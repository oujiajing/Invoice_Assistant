from __future__ import annotations

import io
import re
import uuid
import zipfile
from pathlib import Path
from typing import Callable
from urllib.parse import unquote

from flask import Flask, jsonify, render_template, request, send_file
from openpyxl import Workbook
from werkzeug.utils import secure_filename

from invoice_helper.airline_invoice import build_airline_invoice_preview_name, parse_airline_invoice_from_bytes
from invoice_helper.general_invoice import apply_duplicate_strategy, build_general_invoice_preview_name, parse_general_invoice_from_bytes
from invoice_helper.ledger import build_ledger_entry, delete_ledger_entries, detect_invoice_for_ledger, get_ledger_entry, init_ledger_db, insert_ledger_entry, list_ledger_entries
from invoice_helper.ledger_stats import export_stats_workbook, get_stats_payload
from invoice_helper.merge_print import add_files_to_merge_task, build_merge_list_workbook, build_merge_print_pdf, clear_merge_task, delete_merge_item
from invoice_helper.models import AirlineInvoiceDocument, AirlineInvoiceFields, GeneralInvoiceDocument, GeneralInvoiceFields, RailwayDocument, RailwayTicketFields, RenameRuleConfig
from invoice_helper.railway import build_preview_name, parse_railway_ticket_from_bytes
from invoice_helper.stats_dedup import add_files_to_stats_task, build_stats_workbook, clear_stats_task, delete_stats_item, workbook_to_bytes

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "runtime"
UPLOAD_DIR = DATA_DIR / "uploads"
LEDGER_DB_PATH = DATA_DIR / "ledger.sqlite3"
MERGE_PRINT_DIR = DATA_DIR / "merge_print"
STATS_DEDUP_DIR = DATA_DIR / "stats_dedup"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MERGE_PRINT_DIR.mkdir(parents=True, exist_ok=True)
STATS_DEDUP_DIR.mkdir(parents=True, exist_ok=True)
init_ledger_db(LEDGER_DB_PATH)

app = Flask(__name__, template_folder="templates", static_folder="static")
RAILWAY_DOCUMENT_STORE: dict[str, RailwayDocument] = {}
GENERAL_DOCUMENT_STORE: dict[str, GeneralInvoiceDocument] = {}
AIRLINE_DOCUMENT_STORE: dict[str, AirlineInvoiceDocument] = {}
MERGE_PRINT_TASK_STORE = {}
STATS_DEDUP_TASK_STORE = {}

GENERAL_FIELD_DEFINITIONS = [
    ("invoice_type", "发票类型"),
    ("invoice_code", "发票代码"),
    ("invoice_number", "发票号码"),
    ("issue_date", "开票日期"),
    ("buyer_name", "购买方名称"),
    ("buyer_tax_number", "购买方税号"),
    ("seller_name", "销售方名称"),
    ("seller_tax_number", "销售方税号"),
    ("amount", "发票金额"),
    ("tax_amount", "发票税额"),
    ("total_amount", "价税合计"),
    ("total_amount_upper", "价税合计大写"),
    ("remarks", "备注"),
    ("payee", "收款人"),
    ("reviewer", "复核人"),
    ("issuer", "开票人"),
    ("custom_content", "自定义内容"),
]

RAILWAY_FIELD_DEFINITIONS = [
    ("invoice_number", "发票号码"),
    ("issue_date", "开票日期"),
    ("departure_station", "出发站"),
    ("arrival_station", "到达站"),
    ("departure_datetime", "发车时间"),
    ("train_number", "车次"),
    ("seat_number", "座位号"),
    ("amount", "票价"),
    ("passenger_name", "乘车人姓名"),
    ("passenger_id", "乘车人身份证号"),
    ("custom_content", "自定义内容"),
]

AIRLINE_FIELD_DEFINITIONS = [
    ("invoice_number", "发票号码"),
    ("issue_date", "开票日期"),
    ("departure_airport", "起飞机场"),
    ("arrival_airport", "着陆机场"),
    ("flight_number", "航班号"),
    ("cabin_class", "座位等级"),
    ("departure_time", "起飞时间"),
    ("amount", "票价"),
    ("total_amount", "价税合计"),
    ("passenger_name", "乘机人姓名"),
    ("passenger_id", "乘机人身份证号"),
    ("custom_content", "自定义内容"),
]

INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@app.errorhandler(ValueError)
def handle_value_error(error):
    return jsonify({"message": str(error)}), 400


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/ledger")
def ledger_page():
    return render_template("ledger.html")


@app.get("/merge-print")
def merge_print_page():
    return render_template("merge_print.html")


@app.get("/split-folder")
def split_folder_page():
    return render_template("split_folder.html")


@app.get("/stats-dedup")
def stats_dedup_page():
    return render_template("stats_dedup.html")


@app.post("/api/merge-print/upload")
def merge_print_upload():
    files = request.files.getlist("files")
    if not files:
        raise ValueError("请至少上传一个 PDF 或 OFD 文件。")
    task_id = request.form.get("taskId") or None
    task = add_files_to_merge_task(
        task_store=MERGE_PRINT_TASK_STORE,
        task_id=task_id,
        files=files,
        upload_dir=UPLOAD_DIR,
    )
    return jsonify(task.to_dict())


@app.post("/api/merge-print/build")
def merge_print_build():
    payload = request.get_json(silent=True) or {}
    build = build_merge_print_pdf(
        task_store=MERGE_PRINT_TASK_STORE,
        task_id=payload.get("taskId", ""),
        ordered_item_ids=payload.get("itemIds", []),
        layout_mode=payload.get("layoutMode", "double"),
        show_divider=payload.get("showDivider", True),
        list_placement=payload.get("listPlacement", "append"),
        output_dir=MERGE_PRINT_DIR,
    )
    task = MERGE_PRINT_TASK_STORE[payload.get("taskId", "")]
    stats = _build_merge_stats(task, payload.get("itemIds", []))
    return jsonify(
        {
            "taskId": build["taskId"],
            "buildId": build["buildId"],
            "pageCount": build["pageCount"],
            "previewUrl": f"/api/merge-print/preview/{build['taskId']}/{build['buildId']}",
            "downloadUrl": f"/api/merge-print/download/{build['taskId']}/{build['buildId']}",
            "stats": stats,
        }
    )


@app.get("/api/merge-print/preview/<task_id>/<build_id>")
def merge_print_preview(task_id: str, build_id: str):
    task = MERGE_PRINT_TASK_STORE.get(task_id)
    if task is None or task.latest_build_id != build_id or not task.latest_build_path:
        raise ValueError("未找到可预览的合并文件。")
    return send_file(task.latest_build_path, mimetype="application/pdf")


@app.get("/api/merge-print/download/<task_id>/<build_id>")
def merge_print_download(task_id: str, build_id: str):
    task = MERGE_PRINT_TASK_STORE.get(task_id)
    if task is None or task.latest_build_id != build_id or not task.latest_build_path:
        raise ValueError("未找到可下载的合并文件。")
    return send_file(task.latest_build_path, as_attachment=True, download_name=f"发票合并打印_{build_id}.pdf")


@app.post("/api/merge-print/export-list")
def merge_print_export_list():
    payload = request.get_json(silent=True) or {}
    workbook = build_merge_list_workbook(
        MERGE_PRINT_TASK_STORE,
        payload.get("taskId", ""),
        payload.get("itemIds", []),
    )
    memory_file = io.BytesIO()
    workbook.save(memory_file)
    memory_file.seek(0)
    return send_file(
        memory_file,
        as_attachment=True,
        download_name="发票合并打印清单.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.delete("/api/merge-print/items/<task_id>/<item_id>")
def merge_print_delete_item(task_id: str, item_id: str):
    task = delete_merge_item(MERGE_PRINT_TASK_STORE, task_id, item_id)
    return jsonify(task.to_dict())


@app.delete("/api/merge-print/task/<task_id>")
def merge_print_clear_task(task_id: str):
    clear_merge_task(MERGE_PRINT_TASK_STORE, task_id)
    return jsonify({"message": "文件列表已清空。"})


@app.post("/api/stats-dedup/upload")
def stats_dedup_upload():
    files = request.files.getlist("files")
    if not files:
        raise ValueError("请至少上传一个 PDF 发票文件。")
    task_id = request.form.get("taskId") or None
    task = add_files_to_stats_task(
        task_store=STATS_DEDUP_TASK_STORE,
        task_id=task_id,
        files=files,
        upload_dir=UPLOAD_DIR,
    )
    return jsonify(task.to_dict())


@app.post("/api/stats-dedup/analyze")
def stats_dedup_analyze():
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("taskId", "")
    task = STATS_DEDUP_TASK_STORE.get(task_id)
    if task is None or not task.items:
        raise ValueError("未找到待统计的发票任务。")

    duplicate_counters: dict[str, int] = {}
    duplicate_groups: dict[str, str] = {}
    group_index = 1
    successful_unique_total = 0.0
    success_count = 0
    duplicate_count = 0
    failed_count = 0

    for item in task.items:
        try:
            category, fields = _detect_invoice_for_stats(item.original_name, Path(item.stored_path).read_bytes())
            normalized = _normalize_stats_fields(category, fields)
            item.invoice_category = _stats_category_label(category)
            item.parse_status = "success"
            item.invoice_number = normalized["invoiceNumber"]
            item.issue_date = normalized["issueDate"]
            item.amount = normalized["amount"]
            item.tax_amount = normalized["taxAmount"]
            item.total_amount = normalized["totalAmount"]
            item.fields = normalized["fields"]
            dedup_key = _build_stats_dedup_key(category, normalized)
            if dedup_key:
                duplicate_counters[dedup_key] = duplicate_counters.get(dedup_key, 0) + 1
                group_key = duplicate_groups.setdefault(dedup_key, f"重复组{group_index}")
                if group_key == f"重复组{group_index}":
                    group_index += 1
                item.duplicate_group_key = group_key
            else:
                item.duplicate_group_key = ""
            item.dedup_status = "统计完成"
            item.error = ""
        except Exception as exc:
            item.parse_status = "failed"
            item.invoice_category = ""
            item.invoice_number = ""
            item.issue_date = ""
            item.amount = ""
            item.tax_amount = ""
            item.total_amount = ""
            item.fields = {}
            item.duplicate_group_key = ""
            item.dedup_status = "解析失败"
            item.error = str(exc)

    seen_dedup_keys: set[str] = set()
    for item in task.items:
        if item.parse_status != "success":
            failed_count += 1
            continue
        dedup_key = _build_stats_dedup_key_from_item(item)
        if dedup_key and duplicate_counters.get(dedup_key, 0) > 1:
            if dedup_key in seen_dedup_keys:
                item.dedup_status = "重复发票"
                duplicate_count += 1
                continue
            seen_dedup_keys.add(dedup_key)
        else:
            item.duplicate_group_key = ""
        success_count += 1
        try:
            successful_unique_total += float(item.total_amount or 0)
        except ValueError:
            continue

    return jsonify(
        {
            "taskId": task.task_id,
            "items": [item.to_dict() for item in task.items],
            "summary": {
                "analyzedCount": success_count + duplicate_count,
                "successCount": success_count,
                "duplicateCount": duplicate_count,
                "failedCount": failed_count,
                "totalAmount": f"{successful_unique_total:.2f}",
            },
        }
    )


@app.post("/api/stats-dedup/export")
def stats_dedup_export():
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("taskId", "")
    task = STATS_DEDUP_TASK_STORE.get(task_id)
    if task is None or not task.items:
        raise ValueError("未找到可导出的统计任务。")
    if not any(item.parse_status == "success" for item in task.items):
        raise ValueError("没有可导出的成功统计记录。")

    workbook = build_stats_workbook(task)
    export_id = str(uuid.uuid4())
    export_name = "发票统计文件.xlsx"
    export_path = STATS_DEDUP_DIR / f"{task_id}_{export_id}.xlsx"
    memory_file = workbook_to_bytes(workbook)
    export_path.write_bytes(memory_file.getvalue())
    task.latest_export_id = export_id
    task.latest_export_path = str(export_path)
    task.latest_export_name = export_name
    return jsonify(
        {
            "taskId": task.task_id,
            "exportId": export_id,
            "fileName": export_name,
            "downloadUrl": f"/api/stats-dedup/download/{task.task_id}/{export_id}",
        }
    )


@app.get("/api/stats-dedup/download/<task_id>/<export_id>")
def stats_dedup_download(task_id: str, export_id: str):
    task = STATS_DEDUP_TASK_STORE.get(task_id)
    if task is None or task.latest_export_id != export_id or not task.latest_export_path:
        raise ValueError("未找到可下载的统计报表。")
    return send_file(
        task.latest_export_path,
        as_attachment=True,
        download_name=task.latest_export_name or "发票统计文件.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.delete("/api/stats-dedup/items/<task_id>/<item_id>")
def stats_dedup_delete_item(task_id: str, item_id: str):
    task = delete_stats_item(STATS_DEDUP_TASK_STORE, task_id, item_id)
    return jsonify(task.to_dict())


@app.delete("/api/stats-dedup/task/<task_id>")
def stats_dedup_clear_task(task_id: str):
    clear_stats_task(STATS_DEDUP_TASK_STORE, task_id)
    return jsonify({"message": "文件列表已清空。"})


@app.post("/api/railway/upload-and-parse")
def railway_upload_and_parse():
    return jsonify(
        _upload_and_parse(
            store=RAILWAY_DOCUMENT_STORE,
            parser=parse_railway_ticket_from_bytes,
            document_factory=RailwayDocument,
            fields_factory=RailwayTicketFields,
        )
    )


@app.post("/api/general-invoice/upload-and-parse")
def general_upload_and_parse():
    return jsonify(
        _upload_and_parse(
            store=GENERAL_DOCUMENT_STORE,
            parser=parse_general_invoice_from_bytes,
            document_factory=GeneralInvoiceDocument,
            fields_factory=GeneralInvoiceFields,
        )
    )


@app.post("/api/airline/upload-and-parse")
def airline_upload_and_parse():
    return jsonify(
        _upload_and_parse(
            store=AIRLINE_DOCUMENT_STORE,
            parser=parse_airline_invoice_from_bytes,
            document_factory=AirlineInvoiceDocument,
            fields_factory=AirlineInvoiceFields,
        )
    )


@app.post("/api/railway/preview-rename")
def railway_preview_rename():
    return jsonify(
        _preview_rename(
            store=RAILWAY_DOCUMENT_STORE,
            preview_builder=build_preview_name,
        )
    )


@app.post("/api/general-invoice/preview-rename")
def general_preview_rename():
    return jsonify(
        _preview_rename(
            store=GENERAL_DOCUMENT_STORE,
            preview_builder=build_general_invoice_preview_name,
        )
    )


@app.post("/api/airline/preview-rename")
def airline_preview_rename():
    return jsonify(
        _preview_rename(
            store=AIRLINE_DOCUMENT_STORE,
            preview_builder=build_airline_invoice_preview_name,
        )
    )


@app.post("/api/railway/preview-split-folder")
def railway_preview_split_folder():
    return jsonify(
        _preview_split_folder(
            store=RAILWAY_DOCUMENT_STORE,
            preview_builder=build_preview_name,
            field_definitions=RAILWAY_FIELD_DEFINITIONS,
        )
    )


@app.post("/api/general-invoice/preview-split-folder")
def general_preview_split_folder():
    return jsonify(
        _preview_split_folder(
            store=GENERAL_DOCUMENT_STORE,
            preview_builder=build_general_invoice_preview_name,
            field_definitions=GENERAL_FIELD_DEFINITIONS,
        )
    )


@app.post("/api/airline/preview-split-folder")
def airline_preview_split_folder():
    return jsonify(
        _preview_split_folder(
            store=AIRLINE_DOCUMENT_STORE,
            preview_builder=build_airline_invoice_preview_name,
            field_definitions=AIRLINE_FIELD_DEFINITIONS,
        )
    )


@app.post("/api/railway/export")
def railway_export():
    return _export_documents(
        store=RAILWAY_DOCUMENT_STORE,
        preview_builder=build_preview_name,
        download_name="铁路电子客票重命名结果.zip",
    )


@app.post("/api/general-invoice/export")
def general_export():
    return _export_documents(
        store=GENERAL_DOCUMENT_STORE,
        preview_builder=build_general_invoice_preview_name,
        download_name="常规数电发票重命名结果.zip",
    )


@app.post("/api/airline/export")
def airline_export():
    return _export_documents(
        store=AIRLINE_DOCUMENT_STORE,
        preview_builder=build_airline_invoice_preview_name,
        download_name="航空电子客票重命名结果.zip",
    )


@app.post("/api/railway/export-split-folder")
def railway_export_split_folder():
    return _export_split_folder(
        store=RAILWAY_DOCUMENT_STORE,
        preview_builder=build_preview_name,
        field_definitions=RAILWAY_FIELD_DEFINITIONS,
        download_name="铁路电子客票划分文件夹结果.zip",
    )


@app.post("/api/general-invoice/export-split-folder")
def general_export_split_folder():
    return _export_split_folder(
        store=GENERAL_DOCUMENT_STORE,
        preview_builder=build_general_invoice_preview_name,
        field_definitions=GENERAL_FIELD_DEFINITIONS,
        download_name="常规数电发票划分文件夹结果.zip",
    )


@app.post("/api/airline/export-split-folder")
def airline_export_split_folder():
    return _export_split_folder(
        store=AIRLINE_DOCUMENT_STORE,
        preview_builder=build_airline_invoice_preview_name,
        field_definitions=AIRLINE_FIELD_DEFINITIONS,
        download_name="航空电子客票划分文件夹结果.zip",
    )


@app.post("/api/railway/export-excel")
def railway_export_excel():
    return _export_excel(
        store=RAILWAY_DOCUMENT_STORE,
        field_definitions=RAILWAY_FIELD_DEFINITIONS,
        download_name="铁路电子客票信息台账.xlsx",
        sheet_name="铁路电子客票",
    )


@app.post("/api/general-invoice/export-excel")
def general_export_excel():
    return _export_excel(
        store=GENERAL_DOCUMENT_STORE,
        field_definitions=GENERAL_FIELD_DEFINITIONS,
        download_name="常规数电发票信息台账.xlsx",
        sheet_name="常规数电发票",
    )


@app.post("/api/airline/export-excel")
def airline_export_excel():
    return _export_excel(
        store=AIRLINE_DOCUMENT_STORE,
        field_definitions=AIRLINE_FIELD_DEFINITIONS,
        download_name="航空电子客票信息台账.xlsx",
        sheet_name="航空电子客票",
    )


@app.delete("/api/railway/documents/<document_id>")
def railway_delete_document(document_id: str):
    return jsonify(_delete_document(document_id, RAILWAY_DOCUMENT_STORE))


@app.delete("/api/general-invoice/documents/<document_id>")
def general_delete_document(document_id: str):
    return jsonify(_delete_document(document_id, GENERAL_DOCUMENT_STORE))


@app.delete("/api/airline/documents/<document_id>")
def airline_delete_document(document_id: str):
    return jsonify(_delete_document(document_id, AIRLINE_DOCUMENT_STORE))


@app.delete("/api/railway/documents")
def railway_clear_documents():
    return jsonify(_clear_documents(RAILWAY_DOCUMENT_STORE))


@app.delete("/api/general-invoice/documents")
def general_clear_documents():
    return jsonify(_clear_documents(GENERAL_DOCUMENT_STORE))


@app.delete("/api/airline/documents")
def airline_clear_documents():
    return jsonify(_clear_documents(AIRLINE_DOCUMENT_STORE))


@app.post("/api/ledger/upload-and-parse")
def ledger_upload_and_parse():
    files = request.files.getlist("files")
    if not files:
        raise ValueError("请至少上传一个 PDF 或 OFD 文件。")

    created_entries: list[dict] = []
    failed_entries: list[dict] = []
    for file_storage in files:
        entry_id = str(uuid.uuid4())
        original_name = file_storage.filename or "未命名文件"
        suffix = Path(original_name).suffix.lower()
        stored_name = f"{entry_id}{suffix}"
        stored_path = UPLOAD_DIR / secure_filename(stored_name)
        file_bytes = file_storage.read()
        stored_path.write_bytes(file_bytes)

        try:
            category, fields, raw_text = detect_invoice_for_ledger(original_name, file_bytes)
            entry = build_ledger_entry(
                entry_id=entry_id,
                category=category,
                fields=fields,
                raw_text=raw_text,
                original_name=original_name,
                stored_path=str(stored_path),
                file_type=suffix.lstrip("."),
            )
            insert_ledger_entry(LEDGER_DB_PATH, entry)
            created_entries.append(_ledger_list_item(get_ledger_entry(LEDGER_DB_PATH, entry_id)))
        except Exception as exc:
            if stored_path.exists():
                stored_path.unlink()
            failed_entries.append({"originalName": original_name, "error": str(exc)})

    return jsonify({"created": created_entries, "failed": failed_entries})


@app.get("/api/ledger/list")
def ledger_list():
    invoice_types = _split_query_values(request.args.get("invoice_types", ""))
    expense_types = _split_query_values(request.args.get("expense_types", ""))
    invoice_categories = _split_query_values(request.args.get("invoice_categories", ""))
    seller_names = _split_query_values(request.args.get("seller_names", ""))
    payer_names = _split_query_values(request.args.get("payer_names", ""))
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    entries = list_ledger_entries(
        LEDGER_DB_PATH,
        invoice_types=invoice_types or None,
        expense_types=expense_types or None,
        invoice_categories=invoice_categories or None,
        seller_names=seller_names or None,
        payer_names=payer_names or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return jsonify([_ledger_list_item(entry) for entry in entries])


@app.get("/api/ledger/stats/summary")
def ledger_stats_summary():
    payload = _build_ledger_stats_payload_from_request()
    return jsonify(payload["summary"])


@app.get("/api/ledger/stats/charts")
def ledger_stats_charts():
    payload = _build_ledger_stats_payload_from_request()
    return jsonify({"charts": payload["charts"], "filterOptions": payload["filterOptions"]})


@app.get("/api/ledger/stats/table")
def ledger_stats_table():
    payload = _build_ledger_stats_payload_from_request()
    return jsonify({"table": payload["table"]})


@app.get("/api/ledger/stats/export")
def ledger_stats_export():
    payload = _build_ledger_stats_payload_from_request()
    filters = _ledger_stats_filter_summary()
    workbook_file = export_stats_workbook(payload, filter_summary=filters)
    return send_file(
        workbook_file,
        as_attachment=True,
        download_name="发票台账统计报表.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/api/ledger/<entry_id>")
def ledger_detail(entry_id: str):
    entry = get_ledger_entry(LEDGER_DB_PATH, entry_id)
    if not entry:
        raise ValueError("未找到对应的台账发票。")
    return jsonify(_ledger_detail_payload(entry))


@app.get("/api/ledger/<entry_id>/preview")
def ledger_preview(entry_id: str):
    entry = get_ledger_entry(LEDGER_DB_PATH, entry_id)
    if not entry:
        raise ValueError("未找到对应的台账发票。")
    file_path = Path(entry["stored_path"])
    if not file_path.exists():
        raise ValueError("发票原文件不存在。")
    return send_file(file_path, as_attachment=False, download_name=entry["original_name"])


@app.get("/api/ledger/download")
def ledger_download():
    ids = _split_query_values(request.args.get("ids", ""))
    entries = [get_ledger_entry(LEDGER_DB_PATH, entry_id) for entry_id in ids]
    entries = [entry for entry in entries if entry]
    if not entries:
        raise ValueError("请选择至少一张发票。")
    if len(entries) == 1:
        entry = entries[0]
        return send_file(Path(entry["stored_path"]), as_attachment=True, download_name=entry["original_name"])

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            file_path = Path(entry["stored_path"])
            if file_path.exists():
                archive.writestr(entry["original_name"], file_path.read_bytes())
    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name="发票台账下载.zip", mimetype="application/zip")


@app.delete("/api/ledger")
def ledger_delete():
    payload = request.get_json(silent=True) or {}
    entry_ids = payload.get("ids", [])
    deleted_entries = delete_ledger_entries(LEDGER_DB_PATH, entry_ids)
    for entry in deleted_entries:
        file_path = Path(entry["stored_path"])
        if file_path.exists():
            try:
                file_path.unlink()
            except PermissionError:
                pass
    return jsonify({"message": "发票已删除。", "deletedCount": len(deleted_entries)})


def _upload_and_parse(
    *,
    store: dict,
    parser: Callable[[str, bytes], object],
    document_factory,
    fields_factory,
) -> list[dict]:
    files = request.files.getlist("files")
    if not files:
        raise ValueError("请至少上传一个 PDF 或 OFD 文件。")

    documents: list[dict] = []
    for file_storage in files:
        document_id = str(uuid.uuid4())
        original_name = file_storage.filename or "未命名文件"
        suffix = Path(original_name).suffix.lower()
        stored_name = f"{document_id}{suffix}"
        stored_path = UPLOAD_DIR / secure_filename(stored_name)
        file_bytes = file_storage.read()
        stored_path.write_bytes(file_bytes)

        document = document_factory(
            document_id=document_id,
            original_name=original_name,
            stored_name=stored_name,
            stored_path=str(stored_path),
            file_type=suffix.lstrip("."),
            parse_status="success",
            fields=fields_factory(),
        )

        try:
            document.fields = parser(original_name, file_bytes)
        except Exception as exc:
            document.parse_status = "failed"
            document.error = str(exc)

        store[document_id] = document
        documents.append(document.to_dict())
    return documents


def _preview_rename(*, store: dict, preview_builder: Callable[[object, RenameRuleConfig], str]) -> list[dict]:
    payload = request.get_json(silent=True) or {}
    document_ids = payload.get("documentIds", [])
    rule = RenameRuleConfig.from_dict(payload.get("ruleConfig"))
    documents = _collect_documents(document_ids, store)

    names = [preview_builder(doc.fields, rule) if doc.parse_status == "success" else "" for doc in documents]
    resolved_names = apply_duplicate_strategy(names)
    response = []
    for doc, resolved_name in zip(documents, resolved_names):
        response.append(
            {
                "id": doc.document_id,
                "newFileName": preview_builder(doc.fields, rule) if doc.parse_status == "success" else "",
                "conflictResolvedName": resolved_name if doc.parse_status == "success" else "",
            }
        )
    return response


def _preview_split_folder(
    *,
    store: dict,
    preview_builder: Callable[[object, RenameRuleConfig], str],
    field_definitions: list[tuple[str, str]],
) -> list[dict]:
    payload = request.get_json(silent=True) or {}
    document_ids = payload.get("documentIds", [])
    rule = RenameRuleConfig.from_dict(payload.get("ruleConfig"))
    documents = _collect_documents(document_ids, store)

    raw_outputs: list[dict[str, str]] = []
    for doc in documents:
        if doc.parse_status != "success":
            raw_outputs.append({"folderPath": "", "newFileName": "", "fullOutputPath": ""})
            continue
        folder_path, new_file_name, full_output_path = _build_split_output_path(
            fields=doc.fields,
            rule=rule,
            preview_builder=preview_builder,
            field_definitions=field_definitions,
            extension=Path(doc.original_name).suffix.lower(),
        )
        raw_outputs.append(
            {
                "folderPath": folder_path,
                "newFileName": new_file_name,
                "fullOutputPath": full_output_path,
            }
        )

    resolved_paths = _apply_split_duplicate_strategy([item["fullOutputPath"] for item in raw_outputs])
    response = []
    for doc, output, resolved_path in zip(documents, raw_outputs, resolved_paths):
        response.append(
            {
                "id": doc.document_id,
                "folderPath": output["folderPath"] if doc.parse_status == "success" else "",
                "newFileName": output["newFileName"] if doc.parse_status == "success" else "",
                "fullOutputPath": resolved_path if doc.parse_status == "success" else "",
                "status": doc.parse_status,
                "error": doc.error,
            }
        )
    return response


def _export_documents(*, store: dict, preview_builder: Callable[[object, RenameRuleConfig], str], download_name: str):
    payload = request.get_json(silent=True) or {}
    document_ids = payload.get("documentIds", [])
    rule = RenameRuleConfig.from_dict(payload.get("ruleConfig"))
    documents = _collect_documents(document_ids, store)
    success_docs = [doc for doc in documents if doc.parse_status == "success"]
    if not success_docs:
        raise ValueError("没有可导出的成功解析文件。")

    preview_names = [preview_builder(doc.fields, rule) for doc in success_docs]
    resolved_names = apply_duplicate_strategy(preview_names)

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for doc, final_name in zip(success_docs, resolved_names):
            original_path = Path(doc.stored_path)
            archive.writestr(f"{final_name}{original_path.suffix.lower()}", original_path.read_bytes())

    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name=download_name, mimetype="application/zip")


def _export_split_folder(
    *,
    store: dict,
    preview_builder: Callable[[object, RenameRuleConfig], str],
    field_definitions: list[tuple[str, str]],
    download_name: str,
):
    payload = request.get_json(silent=True) or {}
    document_ids = payload.get("documentIds", [])
    rule = RenameRuleConfig.from_dict(payload.get("ruleConfig"))
    documents = _collect_documents(document_ids, store)
    success_docs = [doc for doc in documents if doc.parse_status == "success"]
    if not success_docs:
        raise ValueError("没有可导出的成功解析文件。")

    raw_paths: list[str] = []
    for doc in success_docs:
        _folder_path, _new_file_name, full_output_path = _build_split_output_path(
            fields=doc.fields,
            rule=rule,
            preview_builder=preview_builder,
            field_definitions=field_definitions,
            extension=Path(doc.original_name).suffix.lower(),
        )
        raw_paths.append(full_output_path)

    resolved_paths = _apply_split_duplicate_strategy(raw_paths)
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for doc, archive_path in zip(success_docs, resolved_paths):
            original_path = Path(doc.stored_path)
            archive.writestr(archive_path, original_path.read_bytes())

    memory_file.seek(0)
    return send_file(memory_file, as_attachment=True, download_name=download_name, mimetype="application/zip")


def _export_excel(*, store: dict, field_definitions: list[tuple[str, str]], download_name: str, sheet_name: str):
    payload = request.get_json(silent=True) or {}
    document_ids = payload.get("documentIds", [])
    documents = _collect_documents(document_ids, store)
    success_docs = [doc for doc in documents if doc.parse_status == "success"]
    if not success_docs:
        raise ValueError("没有可导出的成功解析票据。")

    selected_columns = payload.get("excelColumns") or []
    selected_columns = _resolve_excel_columns(selected_columns, field_definitions)
    headers = ["原文件名", *[label for key, label in field_definitions if key in selected_columns]]

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name[:31]
    worksheet.append(headers)

    for doc in success_docs:
        fields_dict = doc.fields.to_dict()
        row = [doc.original_name, *[fields_dict.get(column_key, "") for column_key in selected_columns]]
        worksheet.append(row)

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 36)

    memory_file = io.BytesIO()
    workbook.save(memory_file)
    memory_file.seek(0)
    return send_file(
        memory_file,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _delete_document(document_id: str, store: dict) -> dict[str, str]:
    document = store.pop(document_id, None)
    if document is None:
        return {"message": "未找到要删除的票据。"}

    stored_path = Path(document.stored_path)
    if stored_path.exists():
        stored_path.unlink()
    return {"message": "票据已删除。"}


def _clear_documents(store: dict) -> dict[str, str]:
    for document in store.values():
        stored_path = Path(document.stored_path)
        if stored_path.exists():
            stored_path.unlink()
    store.clear()
    return {"message": "列表已清空。"}


def _collect_documents(document_ids: list[str], store: dict) -> list:
    documents = [store[document_id] for document_id in document_ids if document_id in store]
    if not documents:
        raise ValueError("未找到已上传的票据，请重新上传文件。")
    return documents


def _resolve_excel_columns(selected_columns: list[str], field_definitions: list[tuple[str, str]]) -> list[str]:
    allowed_keys = [key for key, _ in field_definitions]
    if not selected_columns:
        return allowed_keys
    return [key for key in allowed_keys if key in selected_columns]


def _build_split_output_path(
    *,
    fields,
    rule: RenameRuleConfig,
    preview_builder: Callable[[object, RenameRuleConfig], str],
    field_definitions: list[tuple[str, str]],
    extension: str,
) -> tuple[str, str, str]:
    label_map = dict(field_definitions)
    value_map = _build_rule_value_map(fields, rule, field_definitions)
    filename_base = _sanitize_path_part(preview_builder(fields, rule)) or "未命名发票"
    extension = extension or ""

    if rule.mode == "template":
        rendered = _render_split_template(rule.template, value_map)
        segments = [_sanitize_path_part(part) for part in rendered.split("/") if _sanitize_path_part(part)]
    else:
        segments = []
        for token in rule.tokens:
            if token.type == "text":
                part = token.value.strip()
            else:
                raw_value = str(value_map.get(token.value, "") or "").strip()
                if rule.show_item_prefix and raw_value:
                    part = f"{label_map.get(token.value, token.value)}_{raw_value}"
                else:
                    part = raw_value
            sanitized = _sanitize_path_part(part)
            if sanitized:
                segments.append(sanitized)

    folder_path = "/".join(segments)
    full_output_path = f"{folder_path}/{filename_base}{extension}" if folder_path else f"{filename_base}{extension}"
    return folder_path, f"{filename_base}{extension}", full_output_path


def _apply_split_duplicate_strategy(paths: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    resolved: list[str] = []
    for path in paths:
        if not path:
            resolved.append("")
            continue
        path_obj = Path(path)
        parent = str(path_obj.parent).replace("\\", "/")
        stem = path_obj.stem
        suffix = path_obj.suffix
        key = f"{parent}/{stem}{suffix}"
        count = seen.get(key, 0)
        seen[key] = count + 1
        if count == 0:
            resolved.append(path.replace("\\", "/"))
            continue
        duplicate_name = f"{stem}({count}){suffix}"
        resolved.append(f"{parent}/{duplicate_name}".lstrip("./").replace("\\", "/") if parent not in {".", ""} else duplicate_name)
    return resolved


def _sanitize_path_part(value: str) -> str:
    cleaned = INVALID_PATH_CHARS_RE.sub("_", str(value or "")).strip().strip(".")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _render_split_template(template: str, value_map: dict[str, str]) -> str:
    return re.sub(r"\{([^}]+)\}", lambda match: value_map.get(match.group(1), ""), template or "")


def _build_rule_value_map(fields, rule: RenameRuleConfig, field_definitions: list[tuple[str, str]]) -> dict[str, str]:
    raw_values = fields.to_dict()
    label_map = dict(field_definitions)
    value_map: dict[str, str] = {}
    for key, label in label_map.items():
        formatted = _format_rule_value(raw_values.get(key, ""), key, rule)
        value_map[key] = formatted
        value_map[label] = formatted
    return value_map


def _format_rule_value(value: str, key: str, rule: RenameRuleConfig) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "date" in key or "datetime" in key or "time" in key:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?", text):
            date_part, _, time_part = text.partition(" ")
            year, month, day = date_part.split("-")
            formatted_date = (
                f"{year}年{month}月{day}日"
                if rule.date_format == "YYYY年MM月DD日"
                else f"{year}-{month}-{day}"
            )
            return f"{formatted_date} {time_part}".strip() if time_part else formatted_date
    if key in {"amount", "tax_amount", "total_amount"}:
        try:
            return f"{float(text):.2f}"
        except ValueError:
            return text
    return text


def _split_query_values(value: str) -> list[str]:
    if not value:
        return []
    return [unquote(item).strip() for item in value.split(",") if item.strip()]


def _build_ledger_stats_payload_from_request() -> dict:
    invoice_types = _split_query_values(request.args.get("invoice_types", ""))
    expense_types = _split_query_values(request.args.get("expense_types", ""))
    invoice_categories = _split_query_values(request.args.get("invoice_categories", ""))
    seller_names = _split_query_values(request.args.get("seller_names", ""))
    payer_names = _split_query_values(request.args.get("payer_names", ""))
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    return get_stats_payload(
        LEDGER_DB_PATH,
        date_from=date_from,
        date_to=date_to,
        invoice_types=invoice_types,
        expense_types=expense_types,
        invoice_categories=invoice_categories,
        seller_names=seller_names,
        payer_names=payer_names,
    )


def _ledger_stats_filter_summary() -> dict[str, str]:
    return {
        "开始日期": request.args.get("date_from", "").strip(),
        "结束日期": request.args.get("date_to", "").strip(),
        "发票类型": "、".join(_split_query_values(request.args.get("invoice_types", ""))),
        "费用类型": "、".join(_split_query_values(request.args.get("expense_types", ""))),
        "票种类别": "、".join(_split_query_values(request.args.get("invoice_categories", ""))),
        "销售方": "、".join(_split_query_values(request.args.get("seller_names", ""))),
        "付款方": "、".join(_split_query_values(request.args.get("payer_names", ""))),
    }


def _ledger_list_item(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "invoiceCategory": entry["invoice_category"],
        "expenseType": entry["expense_type"],
        "invoiceTypeFilter": entry["invoice_type_filter"],
        "title": entry["title"],
        "amount": entry["amount"],
        "issueDate": entry["issue_date"],
        "payerName": entry["payer_name"],
        "sellerName": entry["seller_name"],
        "itemSummary": entry["item_summary"],
        "remarks": entry["remarks"],
        "originalName": entry["original_name"],
        "fileType": entry["file_type"],
        "createdAt": entry["created_at"],
    }


def _ledger_detail_payload(entry: dict) -> dict:
    fields = entry["fields"]
    base_items = [
        {"label": "票据号码", "value": fields.get("invoice_number", "")},
        {"label": "收/付款方", "value": entry["seller_name"] or entry["payer_name"]},
        {"label": "付款方", "value": entry["payer_name"]},
        {"label": "项目名称", "value": entry["item_summary"]},
        {"label": "金额", "value": f"¥ {entry['amount']}" if entry["amount"] else ""},
        {"label": "开票日期", "value": entry["issue_date"]},
        {"label": "发票种类", "value": entry["invoice_type_filter"]},
        {"label": "来自", "value": "本地上传"},
        {"label": "备注", "value": entry["remarks"]},
    ]
    extended_items = []
    if entry["invoice_category"] == "railway":
        extended_items = [
            {"label": "出发站", "value": fields.get("departure_station", "")},
            {"label": "到达站", "value": fields.get("arrival_station", "")},
            {"label": "发车时间", "value": fields.get("departure_datetime", "")},
            {"label": "车次", "value": fields.get("train_number", "")},
            {"label": "座位号", "value": fields.get("seat_number", "")},
        ]
    elif entry["invoice_category"] == "airline":
        extended_items = [
            {"label": "起飞机场", "value": fields.get("departure_airport", "")},
            {"label": "着陆机场", "value": fields.get("arrival_airport", "")},
            {"label": "航班号", "value": fields.get("flight_number", "")},
            {"label": "起飞时间", "value": fields.get("departure_time", "")},
            {"label": "舱位", "value": fields.get("cabin_class", "")},
        ]
    else:
        extended_items = [
            {"label": "购买方名称", "value": fields.get("buyer_name", "")},
            {"label": "购买方税号", "value": fields.get("buyer_tax_number", "")},
            {"label": "销售方名称", "value": fields.get("seller_name", "")},
            {"label": "销售方税号", "value": fields.get("seller_tax_number", "")},
        ]

    return {
        **_ledger_list_item(entry),
        "previewUrl": f"/api/ledger/{entry['id']}/preview",
        "downloadUrl": f"/api/ledger/download?ids={entry['id']}",
        "infoItems": base_items,
        "extendedItems": extended_items,
        "fields": fields,
    }


def _build_merge_stats(task, ordered_item_ids: list[str]) -> dict:
    item_map = {item.item_id: item for item in task.items}
    ordered_items = [item_map[item_id] for item_id in ordered_item_ids if item_id in item_map] or task.items
    total_amount = 0.0
    for item in ordered_items:
        try:
            total_amount += float(item.amount or 0)
        except ValueError:
            continue
    return {
        "fileCount": len(ordered_items),
        "invoiceCount": sum(item.invoice_count for item in ordered_items),
        "totalAmount": f"{total_amount:.2f}",
        "inputType": task.input_type,
    }


def _detect_invoice_for_stats(file_name: str, file_bytes: bytes) -> tuple[str, object]:
    for category, parser in (
        ("railway", parse_railway_ticket_from_bytes),
        ("airline", parse_airline_invoice_from_bytes),
        ("general", parse_general_invoice_from_bytes),
    ):
        try:
            return category, parser(file_name, file_bytes)
        except Exception:
            continue
    raise ValueError("未识别为支持统计的 PDF 发票。")


def _normalize_stats_fields(category: str, fields: object) -> dict[str, object]:
    values = fields.to_dict()
    if category == "railway":
        total_amount = values.get("amount", "")
        return {
            "invoiceNumber": values.get("invoice_number", ""),
            "issueDate": values.get("issue_date", ""),
            "amount": values.get("amount", ""),
            "taxAmount": "",
            "totalAmount": total_amount,
            "fields": values,
        }
    if category == "airline":
        total_amount = values.get("total_amount", "") or values.get("amount", "")
        return {
            "invoiceNumber": values.get("invoice_number", ""),
            "issueDate": values.get("issue_date", ""),
            "amount": values.get("amount", ""),
            "taxAmount": "",
            "totalAmount": total_amount,
            "fields": values,
        }
    return {
        "invoiceNumber": values.get("invoice_number", ""),
        "issueDate": values.get("issue_date", ""),
        "amount": values.get("amount", ""),
        "taxAmount": values.get("tax_amount", ""),
        "totalAmount": values.get("total_amount", ""),
        "fields": values,
    }


def _stats_category_label(category: str) -> str:
    return {
        "railway": "铁路电子客票",
        "airline": "航空电子客票",
        "general": "常规数电发票",
    }.get(category, category)


def _build_stats_dedup_key(category: str, normalized: dict[str, object]) -> str:
    invoice_number = str(normalized.get("invoiceNumber", "") or "").strip()
    if invoice_number:
        return f"{category}:invoice:{invoice_number}"

    fields = normalized.get("fields", {}) or {}
    if category == "railway":
        parts = [
            fields.get("issue_date", ""),
            fields.get("departure_station", ""),
            fields.get("arrival_station", ""),
            fields.get("departure_datetime", ""),
            fields.get("amount", ""),
            fields.get("passenger_name", ""),
        ]
    elif category == "airline":
        parts = [
            fields.get("issue_date", ""),
            fields.get("departure_airport", ""),
            fields.get("arrival_airport", ""),
            fields.get("flight_number", ""),
            fields.get("total_amount", "") or fields.get("amount", ""),
            fields.get("passenger_name", ""),
        ]
    else:
        parts = [
            fields.get("issue_date", ""),
            fields.get("seller_name", ""),
            fields.get("total_amount", ""),
            fields.get("buyer_name", ""),
        ]

    joined = "|".join(str(part or "").strip() for part in parts)
    return f"{category}:fallback:{joined}" if joined.replace("|", "") else ""


def _build_stats_dedup_key_from_item(item) -> str:
    category = ""
    if item.invoice_category == "铁路电子客票":
        category = "railway"
    elif item.invoice_category == "航空电子客票":
        category = "airline"
    elif item.invoice_category == "常规数电发票":
        category = "general"
    if item.invoice_number:
        return f"{category}:invoice:{item.invoice_number}" if category else item.invoice_number
    fields = item.fields or {}
    normalized = {
        "invoiceNumber": item.invoice_number,
        "fields": fields,
    }
    return _build_stats_dedup_key(category, normalized)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
