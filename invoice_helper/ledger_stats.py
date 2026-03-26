from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from statistics import mean
from typing import Any

from openpyxl import Workbook

from .ledger import list_ledger_entries


def get_stats_payload(
    db_path: Path,
    *,
    date_from: str = "",
    date_to: str = "",
    invoice_types: list[str] | None = None,
    expense_types: list[str] | None = None,
    invoice_categories: list[str] | None = None,
    seller_names: list[str] | None = None,
    payer_names: list[str] | None = None,
) -> dict[str, Any]:
    entries = list_ledger_entries(
        db_path,
        invoice_types=invoice_types or None,
        expense_types=expense_types or None,
        invoice_categories=invoice_categories or None,
        seller_names=seller_names or None,
        payer_names=payer_names or None,
        date_from=date_from or None,
        date_to=date_to or None,
    )
    return build_stats_payload(entries, date_from=date_from, date_to=date_to)


def build_stats_payload(entries: list[dict[str, Any]], *, date_from: str = "", date_to: str = "") -> dict[str, Any]:
    dedup_groups = _build_duplicate_groups(entries)
    duplicate_ids = {item_id for group_ids in dedup_groups.values() if len(group_ids) > 1 for item_id in group_ids[1:]}
    duplicate_group_labels = {item_id: f"重复组{index}" for index, group_ids in enumerate((ids for ids in dedup_groups.values() if len(ids) > 1), start=1) for item_id in group_ids}

    amounts = [_safe_float(entry.get("amount")) for entry in entries]
    total_amount = sum(amounts)
    unique_entries = [entry for entry in entries if entry["id"] not in duplicate_ids]
    unique_count = len(unique_entries)
    duplicate_count = len(duplicate_ids)
    average_amount = mean(amounts) if amounts else 0.0

    trend_bucket = _resolve_trend_bucket(entries, date_from, date_to)
    charts = {
        "amountTrend": _build_trend_chart(entries, trend_bucket, value_key="amount"),
        "countTrend": _build_trend_chart(entries, trend_bucket, value_key=None),
        "expenseType": _build_counter_chart(entries, key="expense_type"),
        "invoiceType": _build_counter_chart(entries, key="invoice_type_filter"),
        "invoiceCategory": _build_counter_chart(entries, key="invoice_category"),
        "invoiceCategoryAmount": _build_category_amount_chart(entries),
    }

    duplicate_rows = []
    for entry in entries:
        duplicate_status = "重复发票" if entry["id"] in duplicate_ids else "正常"
        if duplicate_status == "正常":
            continue
        duplicate_rows.append(
            {
                "id": entry["id"],
                "invoiceCategory": _category_label(entry["invoice_category"]),
                "originalName": entry["original_name"],
                "invoiceNumber": entry["fields"].get("invoice_number", ""),
                "issueDate": entry["issue_date"],
                "amount": entry["amount"],
                "sellerName": entry["seller_name"],
                "payerName": entry["payer_name"],
                "duplicateStatus": duplicate_status,
                "duplicateGroup": duplicate_group_labels.get(entry["id"], ""),
            }
        )

    filter_options = {
        "sellerNames": sorted({entry["seller_name"] for entry in entries if entry["seller_name"]}),
        "payerNames": sorted({entry["payer_name"] for entry in entries if entry["payer_name"]}),
    }

    return {
        "summary": {
            "invoiceCount": len(entries),
            "uniqueInvoiceCount": unique_count,
            "totalAmount": f"{total_amount:.2f}",
            "averageAmount": f"{average_amount:.2f}",
            "duplicateCount": duplicate_count,
            "trendBucket": trend_bucket,
        },
        "charts": charts,
        "table": duplicate_rows,
        "filterOptions": filter_options,
    }


def export_stats_workbook(payload: dict[str, Any], *, filter_summary: dict[str, str]) -> BytesIO:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "汇总概览"
    summary_sheet.append(["统计项", "值"])
    for key, label in (
        ("invoiceCount", "发票总数"),
        ("uniqueInvoiceCount", "去重后发票数"),
        ("totalAmount", "总金额"),
        ("averageAmount", "平均票面金额"),
        ("duplicateCount", "重复发票数"),
    ):
        summary_sheet.append([label, payload["summary"][key]])
    summary_sheet.append([])
    summary_sheet.append(["筛选项", "值"])
    for label, value in filter_summary.items():
        summary_sheet.append([label, value or "全部"])

    detail_sheet = workbook.create_sheet("明细数据")
    detail_sheet.append(["票种", "文件名", "发票号码", "开票日期", "金额", "销售方", "付款方", "重复状态", "重复组"])
    for row in payload["table"]:
        detail_sheet.append(
            [
                row["invoiceCategory"],
                row["originalName"],
                row["invoiceNumber"],
                row["issueDate"],
                row["amount"],
                row["sellerName"],
                row["payerName"],
                row["duplicateStatus"],
                row["duplicateGroup"],
            ]
        )

    for worksheet in workbook.worksheets:
        for column_cells in worksheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column_cells)
            worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 32)

    memory_file = BytesIO()
    workbook.save(memory_file)
    memory_file.seek(0)
    return memory_file


def _build_duplicate_groups(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        dedup_key = _build_dedup_key(entry)
        if not dedup_key:
            continue
        groups[dedup_key].append(entry["id"])
    return groups


def _build_dedup_key(entry: dict[str, Any]) -> str:
    category = entry["invoice_category"]
    fields = entry["fields"] or {}
    invoice_number = str(fields.get("invoice_number", "") or "").strip()
    if invoice_number:
        return f"{category}:invoice:{invoice_number}"
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


def _resolve_trend_bucket(entries: list[dict[str, Any]], date_from: str, date_to: str) -> str:
    parsed_dates = [_parse_date(entry["issue_date"]) for entry in entries if entry.get("issue_date")]
    if date_from and date_to:
        start = _parse_date(date_from)
        end = _parse_date(date_to)
        if start and end and (end - start).days <= 31:
            return "day"
    if parsed_dates:
        start = min(parsed_dates)
        end = max(parsed_dates)
        if (end - start).days <= 31:
            return "day"
    return "month"


def _build_trend_chart(entries: list[dict[str, Any]], bucket: str, *, value_key: str | None) -> dict[str, Any]:
    grouped: dict[str, float] = defaultdict(float)
    for entry in entries:
        parsed = _parse_date(entry.get("issue_date", ""))
        if not parsed:
            continue
        label = parsed.strftime("%Y-%m-%d") if bucket == "day" else parsed.strftime("%Y-%m")
        grouped[label] += 1 if value_key is None else _safe_float(entry.get(value_key))
    labels = sorted(grouped.keys())
    return {"labels": labels, "series": [round(grouped[label], 2) for label in labels]}


def _build_counter_chart(entries: list[dict[str, Any]], *, key: str) -> dict[str, Any]:
    counter = Counter()
    for entry in entries:
        value = entry.get(key) or "未分类"
        counter[_category_label(value) if key == "invoice_category" else value] += 1
    labels = list(counter.keys())
    return {"labels": labels, "series": [counter[label] for label in labels]}


def _build_category_amount_chart(entries: list[dict[str, Any]]) -> dict[str, Any]:
    category_order = ["general", "railway", "airline"]
    grouped: dict[str, float] = defaultdict(float)
    for entry in entries:
        grouped[entry.get("invoice_category") or "unknown"] += _safe_float(entry.get("amount"))

    labels: list[str] = []
    series: list[float] = []
    for category in category_order:
        labels.append(_category_label(category))
        series.append(round(grouped.get(category, 0.0), 2))
    return {"labels": labels, "series": series}


def _category_label(value: str) -> str:
    return {
        "railway": "铁路电子客票",
        "airline": "航空电子客票",
        "general": "常规数电发票",
    }.get(value, value)


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
