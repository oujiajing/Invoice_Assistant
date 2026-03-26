from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .airline_invoice import parse_airline_invoice_from_bytes
from .general_invoice import parse_general_invoice_from_bytes
from .railway import extract_text_from_ofd_bytes, extract_text_from_pdf_bytes, parse_railway_ticket_from_bytes


def init_ledger_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger_entries (
                id TEXT PRIMARY KEY,
                invoice_category TEXT NOT NULL,
                expense_type TEXT NOT NULL,
                invoice_type_filter TEXT NOT NULL,
                title TEXT NOT NULL,
                amount TEXT NOT NULL,
                issue_date TEXT NOT NULL,
                payer_name TEXT NOT NULL,
                seller_name TEXT NOT NULL,
                item_summary TEXT NOT NULL,
                remarks TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                parse_status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                fields_json TEXT NOT NULL
            )
            """
        )


def detect_invoice_for_ledger(file_name: str, file_bytes: bytes) -> tuple[str, dict[str, str], str]:
    for category, parser in (
        ("railway", parse_railway_ticket_from_bytes),
        ("airline", parse_airline_invoice_from_bytes),
        ("general", parse_general_invoice_from_bytes),
    ):
        try:
            fields = parser(file_name, file_bytes)
            return category, fields.to_dict(), _extract_text(file_name, file_bytes)
        except Exception:
            continue
    raise ValueError("未识别为支持的发票类型。")


def build_ledger_entry(
    *,
    entry_id: str,
    category: str,
    fields: dict[str, str],
    raw_text: str,
    original_name: str,
    stored_path: str,
    file_type: str,
) -> dict[str, str]:
    title = _build_title(category, fields, raw_text)
    amount = _build_amount(category, fields)
    issue_date = fields.get("issue_date", "")
    payer_name = _build_payer_name(category, fields)
    seller_name = _build_seller_name(category, fields, raw_text)
    item_summary = _build_item_summary(category, fields, raw_text)
    remarks = _build_remarks(category, fields, raw_text)
    invoice_type_filter = _build_invoice_type_filter(category, fields)
    expense_type = "住宿" if category == "general" else "交通"

    return {
        "id": entry_id,
        "invoice_category": category,
        "expense_type": expense_type,
        "invoice_type_filter": invoice_type_filter,
        "title": title,
        "amount": amount,
        "issue_date": issue_date,
        "payer_name": payer_name,
        "seller_name": seller_name,
        "item_summary": item_summary,
        "remarks": remarks,
        "original_name": original_name,
        "stored_path": stored_path,
        "file_type": file_type,
        "parse_status": "success",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "fields_json": json.dumps(fields, ensure_ascii=False),
    }


def insert_ledger_entry(db_path: Path, entry: dict[str, str]) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO ledger_entries (
                id, invoice_category, expense_type, invoice_type_filter, title, amount,
                issue_date, payer_name, seller_name, item_summary, remarks, original_name,
                stored_path, file_type, parse_status, created_at, fields_json
            ) VALUES (
                :id, :invoice_category, :expense_type, :invoice_type_filter, :title, :amount,
                :issue_date, :payer_name, :seller_name, :item_summary, :remarks, :original_name,
                :stored_path, :file_type, :parse_status, :created_at, :fields_json
            )
            """,
            entry,
        )


def list_ledger_entries(
    db_path: Path,
    *,
    invoice_types: list[str] | None = None,
    expense_types: list[str] | None = None,
    invoice_categories: list[str] | None = None,
    seller_names: list[str] | None = None,
    payer_names: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT id, invoice_category, expense_type, invoice_type_filter, title, amount, issue_date,
               payer_name, seller_name, item_summary, remarks, original_name, stored_path, file_type,
               parse_status, created_at, fields_json
        FROM ledger_entries
    """
    clauses: list[str] = []
    params: list[str] = []
    if invoice_types:
        placeholders = ",".join("?" for _ in invoice_types)
        clauses.append(f"invoice_type_filter IN ({placeholders})")
        params.extend(invoice_types)
    if expense_types:
        placeholders = ",".join("?" for _ in expense_types)
        clauses.append(f"expense_type IN ({placeholders})")
        params.extend(expense_types)
    if invoice_categories:
        placeholders = ",".join("?" for _ in invoice_categories)
        clauses.append(f"invoice_category IN ({placeholders})")
        params.extend(invoice_categories)
    if seller_names:
        placeholders = ",".join("?" for _ in seller_names)
        clauses.append(f"seller_name IN ({placeholders})")
        params.extend(seller_names)
    if payer_names:
        placeholders = ",".join("?" for _ in payer_names)
        clauses.append(f"payer_name IN ({placeholders})")
        params.extend(payer_names)
    if date_from:
        clauses.append("issue_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("issue_date <= ?")
        params.append(date_to)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY issue_date DESC, created_at DESC"

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()
    return [_row_to_entry(row) for row in rows]


def get_ledger_entry(db_path: Path, entry_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, invoice_category, expense_type, invoice_type_filter, title, amount, issue_date,
                   payer_name, seller_name, item_summary, remarks, original_name, stored_path, file_type,
                   parse_status, created_at, fields_json
            FROM ledger_entries
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()
    return _row_to_entry(row) if row else None


def delete_ledger_entries(db_path: Path, entry_ids: list[str]) -> list[dict[str, Any]]:
    if not entry_ids:
        return []
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in entry_ids)
        rows = connection.execute(
            f"""
            SELECT id, invoice_category, expense_type, invoice_type_filter, title, amount, issue_date,
                   payer_name, seller_name, item_summary, remarks, original_name, stored_path, file_type,
                   parse_status, created_at, fields_json
            FROM ledger_entries
            WHERE id IN ({placeholders})
            """,
            entry_ids,
        ).fetchall()
        connection.execute(f"DELETE FROM ledger_entries WHERE id IN ({placeholders})", entry_ids)
    return [_row_to_entry(row) for row in rows]


def _row_to_entry(row: sqlite3.Row) -> dict[str, Any]:
    payload = dict(row)
    payload["fields"] = json.loads(payload.pop("fields_json") or "{}")
    return payload


def _extract_text(file_name: str, file_bytes: bytes) -> str:
    extension = Path(file_name).suffix.lower()
    if extension == ".pdf":
        return extract_text_from_pdf_bytes(file_bytes)
    return extract_text_from_ofd_bytes(file_bytes)


def _build_title(category: str, fields: dict[str, str], raw_text: str) -> str:
    if category == "railway":
        return "电子发票（铁路电子客票）"
    if category == "airline":
        return _build_seller_name(category, fields, raw_text) or "航空电子客票"
    return fields.get("seller_name") or "常规数电发票"


def _build_amount(category: str, fields: dict[str, str]) -> str:
    if category == "general":
        return fields.get("total_amount") or fields.get("amount") or ""
    if category == "airline":
        return fields.get("total_amount") or fields.get("amount") or ""
    return fields.get("amount") or ""


def _build_payer_name(category: str, fields: dict[str, str]) -> str:
    if category == "railway":
        return fields.get("passenger_name", "")
    if category == "airline":
        return fields.get("passenger_name", "")
    return fields.get("buyer_name", "")


def _build_seller_name(category: str, fields: dict[str, str], raw_text: str) -> str:
    if category == "general":
        return fields.get("seller_name", "")
    if category == "airline":
        for line in _normalized_lines(raw_text):
            if any(keyword in line for keyword in ("航空", "航司", "航空公司")) and not any(keyword in line for keyword in ("发票", "机票款", "基金")):
                return line
        return ""
    return "中国铁路网络有限公司"


def _build_item_summary(category: str, fields: dict[str, str], raw_text: str) -> str:
    if category == "railway":
        return "网上购票系统-电子发票通知"
    if category == "airline":
        extracted = _extract_airline_item_summary(raw_text)
        if extracted:
            return extracted
        return "运输服务"
    extracted = _extract_item_line(raw_text)
    if extracted:
        return extracted
    if fields.get("remarks"):
        return fields["remarks"][:80].replace("*", "")
    for line in _normalized_lines(raw_text):
        if "*" in line and "服务" in line:
            return line.replace("*", "")[:80]
    return "住宿服务"


def _build_remarks(category: str, fields: dict[str, str], raw_text: str) -> str:
    if category == "railway":
        parts = [fields.get("departure_station", ""), fields.get("arrival_station", ""), fields.get("train_number", "")]
        return " ".join(part for part in parts if part)
    if category == "airline":
        route = "-".join(part for part in (fields.get("departure_airport", ""), fields.get("arrival_airport", "")) if part)
        parts = [route, fields.get("flight_number", ""), fields.get("cabin_class", "")]
        return " ".join(part for part in parts if part)
    return fields.get("remarks", "")[:200]


def _build_invoice_type_filter(category: str, fields: dict[str, str]) -> str:
    if category in {"railway", "airline"}:
        return "普通发票"
    invoice_type = fields.get("invoice_type", "")
    if "专用发票" in invoice_type or "专票" in invoice_type:
        return "增值税专票"
    return "普通发票"


def _normalized_lines(text: str) -> list[str]:
    return [line.strip().replace(" ", "") for line in text.splitlines() if line.strip()]


def _extract_item_line(raw_text: str) -> str:
    lines = _normalized_lines(raw_text)
    header_keywords = ("项目名称", "货物或应税劳务、服务名称", "货物或应税劳务服务名称")
    for index, line in enumerate(lines):
        if any(keyword in line for keyword in header_keywords):
            for candidate in lines[index + 1 :]:
                cleaned = _sanitize_item_summary(candidate)
                if cleaned:
                    return cleaned[:80]
    for line in lines:
        cleaned = _sanitize_item_summary(line)
        if cleaned:
            return cleaned[:80]
    return ""


def _extract_airline_item_summary(raw_text: str) -> str:
    lines = _normalized_lines(raw_text)
    items: list[str] = []
    for line in lines:
        cleaned = _sanitize_item_summary(line)
        if cleaned and any(keyword in cleaned for keyword in ("机票款", "民航发展基金", "运输服务")):
            if cleaned not in items:
                items.append(cleaned)
    return "".join(items)[:120]


def _sanitize_item_summary(line: str) -> str:
    if not line:
        return ""
    if any(keyword in line for keyword in ("规格型号", "价税合计", "开票人", "复核人", "收款人", "发票号码", "开票日期", "购买方", "销售方", "地址", "电话", "开户行", "账号")):
        return ""
    if line.startswith("合计") or line.startswith("价税合计"):
        return ""
    if "*" not in line and not any(keyword in line for keyword in ("票款", "服务", "住宿", "运输")):
        return ""

    sanitized = line
    sanitized = sanitized.split("税率", 1)[0]
    sanitized = sanitized.split("不征税", 1)[0]
    sanitized = sanitized.split("规格型号", 1)[0]
    sanitized = sanitized.split("数量", 1)[0]
    sanitized = sanitized.split("单价", 1)[0]
    sanitized = sanitized.split("金额", 1)[0]
    sanitized = sanitized.split("项目名称", 1)[0]
    sanitized = sanitized.rstrip(":：")
    sanitized = __strip_trailing_numbers(sanitized)
    return sanitized[:80]


def __strip_trailing_numbers(value: str) -> str:
    trimmed = value
    while True:
        updated = trimmed
        updated = __strip_one_numeric_suffix(updated)
        if updated == trimmed:
            break
        trimmed = updated
    return trimmed.rstrip("-")


def __strip_one_numeric_suffix(value: str) -> str:
    patterns = [
        r"[\d.]+%?[\d.]*$",
        r"\d+(天|晚|次|张|间)$",
        r"[0-9.]+$",
    ]
    for pattern in patterns:
        updated = re.sub(pattern, "", value)
        if updated != value:
            return updated
    return value
