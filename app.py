from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path
from typing import Callable

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from invoice_helper.airline_invoice import build_airline_invoice_preview_name, parse_airline_invoice_from_bytes
from invoice_helper.general_invoice import apply_duplicate_strategy, build_general_invoice_preview_name, parse_general_invoice_from_bytes
from invoice_helper.models import AirlineInvoiceDocument, AirlineInvoiceFields, GeneralInvoiceDocument, GeneralInvoiceFields, RailwayDocument, RailwayTicketFields, RenameRuleConfig
from invoice_helper.railway import build_preview_name, parse_railway_ticket_from_bytes

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "runtime"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
RAILWAY_DOCUMENT_STORE: dict[str, RailwayDocument] = {}
GENERAL_DOCUMENT_STORE: dict[str, GeneralInvoiceDocument] = {}
AIRLINE_DOCUMENT_STORE: dict[str, AirlineInvoiceDocument] = {}


@app.errorhandler(ValueError)
def handle_value_error(error):
    return jsonify({"message": str(error)}), 400


@app.get("/")
def index():
    return render_template("index.html")


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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
