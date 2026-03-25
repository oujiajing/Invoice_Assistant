from __future__ import annotations

import io
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
from invoice_helper.merge_print import add_files_to_merge_task, build_merge_list_workbook, build_merge_print_pdf, clear_merge_task, delete_merge_item
from invoice_helper.models import AirlineInvoiceDocument, AirlineInvoiceFields, GeneralInvoiceDocument, GeneralInvoiceFields, RailwayDocument, RailwayTicketFields, RenameRuleConfig
from invoice_helper.railway import build_preview_name, parse_railway_ticket_from_bytes

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "runtime"
UPLOAD_DIR = DATA_DIR / "uploads"
LEDGER_DB_PATH = DATA_DIR / "ledger.sqlite3"
MERGE_PRINT_DIR = DATA_DIR / "merge_print"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MERGE_PRINT_DIR.mkdir(parents=True, exist_ok=True)
init_ledger_db(LEDGER_DB_PATH)

app = Flask(__name__, template_folder="templates", static_folder="static")
RAILWAY_DOCUMENT_STORE: dict[str, RailwayDocument] = {}
GENERAL_DOCUMENT_STORE: dict[str, GeneralInvoiceDocument] = {}
AIRLINE_DOCUMENT_STORE: dict[str, AirlineInvoiceDocument] = {}
MERGE_PRINT_TASK_STORE = {}

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
    entries = list_ledger_entries(LEDGER_DB_PATH, invoice_types=invoice_types or None, expense_types=expense_types or None)
    return jsonify([_ledger_list_item(entry) for entry in entries])


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


def _split_query_values(value: str) -> list[str]:
    if not value:
        return []
    return [unquote(item).strip() for item in value.split(",") if item.strip()]


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
