from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import AirlineInvoiceFields, RenameRuleConfig, normalize_amount
from .railway import extract_text_from_ofd_bytes, extract_text_from_pdf_bytes

INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
CHINESE_DATE_RE = re.compile(r"(20\d{2})年\s*(\d{2})月\s*(\d{2})日")
AIRLINE_TEMPLATE_ALIASES = {
    "发票号码": "invoice_number",
    "开票日期": "issue_date",
    "起飞机场": "departure_airport",
    "着陆机场": "arrival_airport",
    "航班号": "flight_number",
    "座位等级": "cabin_class",
    "起飞时间": "departure_time",
    "票价": "amount",
    "价税合计": "total_amount",
    "乘机人姓名": "passenger_name",
    "乘机人身份证号": "passenger_id",
    "自定义内容": "custom_content",
}


def parse_airline_invoice_from_bytes(file_name: str, file_bytes: bytes) -> AirlineInvoiceFields:
    from .document_text import extract_document_text

    extracted = extract_document_text(file_name, file_bytes, validator=parse_airline_invoice_text)
    fields = parse_airline_invoice_text(extracted.text)
    fields.parse_source = extracted.source
    fields.raw_text = extracted.text
    return fields


def parse_airline_invoice_text(text: str) -> AirlineInvoiceFields:
    normalized_text = text.replace("\x00", "")
    if "机票" not in normalized_text and "旅客运输服务" not in normalized_text and "海南增值税电子普通发票" not in normalized_text:
        raise ValueError("未识别为航空电子客票文件。")

    lines = _normalize_lines(normalized_text)
    compact = "".join(lines)
    fields = AirlineInvoiceFields()
    fields.invoice_type = _extract_invoice_type(compact)
    fields.invoice_number = _extract_invoice_number(lines, compact)
    fields.issue_date = _extract_issue_date(lines, compact)
    fields.amount = normalize_amount(_extract_amount(lines, compact))
    fields.total_amount = normalize_amount(_extract_total_amount(lines, compact))
    fields.passenger_name, fields.passenger_id = _extract_passenger(lines, compact)
    flight_date, flight_number, cabin_class, route, departure_time = _extract_flight_segments(lines, compact)
    if not fields.passenger_name:
        name_match = re.search(r"([\u4e00-\u9fff]{2,6})\d{8}[A-Z]{2}\d{3,4}", compact)
        if name_match:
            fields.passenger_name = name_match.group(1)
    fields.flight_number = flight_number
    fields.cabin_class = cabin_class
    departure_airport, arrival_airport = _extract_route(route)
    fields.departure_airport = departure_airport
    fields.arrival_airport = arrival_airport
    fields.departure_time = _format_departure_time(flight_date, departure_time)
    return fields


def build_airline_invoice_preview_name(fields: AirlineInvoiceFields, rule: RenameRuleConfig) -> str:
    values = _formatted_value_map(fields, rule)
    if rule.mode == "template":
        return _sanitize_filename(_render_template(rule.template, values), rule.sanitize)

    parts: list[str] = []
    for token in rule.tokens:
        if token.type == "field":
            parts.append(values.get(token.value, ""))
        elif token.type == "text":
            parts.append(token.value)
    return _sanitize_filename(rule.separator.join(part for part in parts if part), rule.sanitize)


def _normalize_lines(text: str) -> list[str]:
    return [line.strip().replace(" ", "") for line in text.splitlines() if line.strip()]


def _search_group(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _normalize_date(value: str) -> str:
    match = CHINESE_DATE_RE.search(value or "")
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    compact_match = re.search(r"(20\d{2})(\d{2})(\d{2})", value or "")
    if compact_match:
        return f"{compact_match.group(1)}-{compact_match.group(2)}-{compact_match.group(3)}"
    return ""


def _extract_invoice_type(compact: str) -> str:
    if "海南增值税电子普通发票" in compact:
        return "海南增值税电子普通发票"
    if "增值税电子普通发票" in compact:
        return "增值税电子普通发票"
    if "电子发票（普通发票）" in compact:
        return "电子发票（普通发票）"
    return "航空电子客票"


def _extract_invoice_number(lines: list[str], compact: str) -> str:
    direct = _search_group(compact, r"发票号码[:：]?(\d{8,20})")
    if direct:
        return direct
    for line in lines:
        if re.fullmatch(r"\d{8}", line):
            # 海南版式的 8 位是发票号码
            return line
    for line in lines:
        if re.fullmatch(r"\d{16,20}", line):
            return line
    return ""


def _extract_issue_date(lines: list[str], compact: str) -> str:
    direct = _normalize_date(_search_group(compact, r"开票日期[:：]?((?:20\d{2})年(?:\d{2})月(?:\d{2})日)"))
    if direct:
        return direct
    date_index = next((idx for idx, line in enumerate(lines) if "开票日期" in line), None)
    if date_index is not None:
        for line in lines[date_index + 1 : date_index + 6]:
            if re.fullmatch(r"20\d{2}年\d{2}月\d{2}日", line) or re.fullmatch(r"20\d{8}", line) or re.fullmatch(r"20\d{2}\d{2}\d{2}", line):
                normalized = _normalize_date(line)
                if normalized:
                    return normalized
    for line in lines:
        if re.fullmatch(r"20\d{2}年\d{2}月\d{2}日", line) or re.fullmatch(r"20\d{8}", line) or re.fullmatch(r"20\d{2}\d{2}\d{2}", line):
            normalized = _normalize_date(line)
            if normalized:
                return normalized
    for line in lines:
        normalized = _normalize_date(line)
        if normalized and len(line) <= 12:
            return normalized
    return ""


def _extract_amount(lines: list[str], compact: str) -> str:
    # "票价" here means the airfare amount excluding the civil aviation development fund.
    match = re.search(r"国内机票款(\d+\.\d{2})", compact)
    if match:
        return match.group(1)
    amounts = re.findall(r"国内机票款[^\d]*(\d+\.\d{2})", compact)
    return amounts[-1] if amounts else ""


def _extract_total_amount(lines: list[str], compact: str) -> str:
    direct = _search_group(compact, r"(?:小写）|小写\)|\(小写\))[¥￥]?\s?(\d+\.\d{2})")
    if direct:
        return direct
    chinese_pairs = re.findall(r"[零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆角分整]+\s*[¥￥]\s?(\d+\.\d{2})", compact)
    if chinese_pairs:
        return chinese_pairs[-1]
    currency_values = re.findall(r"[¥￥]\s?(\d+\.\d{2})", compact)
    return currency_values[0] if currency_values else ""


def _extract_passenger(lines: list[str], compact: str) -> tuple[str, str]:
    passenger_name = ""
    for line in lines:
        flight_line = re.search(r"([\u4e00-\u9fff]{2,6})\s*(20\d{6}|20\d{2}-\d{2}-\d{2})\s*[A-Z]{2}\d{3,4}", line)
        if flight_line:
            passenger_name = flight_line.group(1)
    for line in lines:
        match = re.search(r"([\u4e00-\u9fff]{2,6})\s*(\d{6}\*+\d{0,6}|\d{6}\*+\w+|\d{17}[0-9Xx]|\d{15,18})", line)
        if match and "银行" not in line and "账号" not in line:
            return match.group(1), match.group(2)
    for line in lines:
        match = re.search(r"([\u4e00-\u9fff]{2,6})\s*(\d{6}\*+\d{0,6})", line)
        if match and "银行" not in line and "账号" not in line:
            return match.group(1), match.group(2)
    name = _search_group(compact, r"([\u4e00-\u9fff]{2,6})\d{8}[A-Z]{2}\d{3,4}")
    return passenger_name or name, ""


def _extract_flight_segments(lines: list[str], compact: str) -> tuple[str, str, str, str, str]:
    for line in lines:
        compact_match = re.search(
            r"(?P<name>[\u4e00-\u9fff]{2,6})\s*(?P<date>20\d{2}-?\d{4}|20\d{6})\s*"
            r"(?P<flight>[A-Z]{2}\d{3,4})\s*(?P<class>[A-Z](?:\S)?舱|[A-Z])\s*"
            r"(?P<route>[\u4e00-\u9fff]+-[\u4e00-\u9fff]+)",
            line,
        )
        if compact_match:
            return (
                _normalize_flight_date(compact_match.group("date")),
                compact_match.group("flight"),
                compact_match.group("class"),
                compact_match.group("route"),
                "",
            )
        match = re.search(
            r"(?P<name>[\u4e00-\u9fff]{2,6})\s*(?P<date>20\d{2}-\d{2}-\d{2}|20\d{6})\s*(?P<flight>[A-Z]{2}\d{3,4})\s*(?P<class1>[\u4e00-\u9fff]{2,8})\s*(?P<class2>[A-Z]\S?舱|[A-Z]舱|[A-Z])?\s*(?P<route>[\u4e00-\u9fff]+-[\u4e00-\u9fff]+)\s*(?P<trailing>\d{6,})?",
            line,
        )
        if match:
            cabin_parts = [match.group("class1")]
            if match.group("class2"):
                cabin_parts.append(match.group("class2"))
            return (
                _normalize_flight_date(match.group("date")),
                match.group("flight"),
                " ".join(part for part in cabin_parts if part),
                match.group("route"),
                _search_group(line, r"(\d{2}:\d{2})"),
            )

    for line in lines:
        match = re.search(
            r"(?P<name>[\u4e00-\u9fff]{2,6})\s*(?P<id>\d{6}\*+\d{0,6})?\s*(?P<date>20\d{2}-\d{2}-\d{2})\s*(?P<from>[\u4e00-\u9fff]+)\s*(?P<to>[\u4e00-\u9fff]+)\s*(?P<class>[\u4e00-\u9fff]{2,8})\s*飞机",
            line,
        )
        if match:
            return (
                _normalize_flight_date(match.group("date")),
                "",
                match.group("class"),
                f"{match.group('from')}-{match.group('to')}",
                _search_group(line, r"(\d{2}:\d{2})"),
            )
    return "", "", "", "", ""


def _normalize_flight_date(value: str) -> str:
    if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value):
        return value
    if re.fullmatch(r"20\d{6}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return ""


def _extract_route(route: str) -> tuple[str, str]:
    if "-" not in route:
        return "", ""
    departure, arrival = route.split("-", 1)
    return departure.strip(), arrival.strip()


def _format_departure_time(flight_date: str, departure_time: str) -> str:
    if departure_time and flight_date:
        return f"{flight_date} {departure_time}"
    return departure_time or flight_date


def _formatted_value_map(fields: AirlineInvoiceFields, rule: RenameRuleConfig) -> dict[str, str]:
    issue_date = _format_date(fields.issue_date, rule.date_format)
    departure_time = _format_datetime_or_date(fields.departure_time, rule.date_format)
    return {
        "invoice_number": fields.invoice_number,
        "issue_date": issue_date,
        "departure_airport": fields.departure_airport,
        "arrival_airport": fields.arrival_airport,
        "flight_number": fields.flight_number,
        "cabin_class": fields.cabin_class,
        "departure_time": departure_time,
        "amount": normalize_amount(fields.amount) if rule.amount_format == "0.00" else fields.amount,
        "total_amount": normalize_amount(fields.total_amount) if rule.amount_format == "0.00" else fields.total_amount,
        "passenger_name": fields.passenger_name,
        "passenger_id": fields.passenger_id,
        "custom_content": fields.custom_content,
    }


def _format_date(value: str, output_format: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return value
    if output_format == "YYYY-MM-DD":
        return parsed.strftime("%Y-%m-%d")
    return parsed.strftime("%Y年%m月%d日")


def _format_datetime_or_date(value: str, output_format: str) -> str:
    if not value:
        return ""
    if re.fullmatch(r"\d{2}:\d{2}", value):
        return value
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return value
        return parsed.strftime("%Y-%m-%d") if output_format == "YYYY-MM-DD" else parsed.strftime("%Y年%m月%d日")
    if output_format == "YYYY-MM-DD":
        return parsed.strftime("%Y-%m-%d %H:%M")
    return parsed.strftime("%Y年%m月%d日 %H:%M")


def _render_template(template: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return values.get(AIRLINE_TEMPLATE_ALIASES.get(key, key), "")

    return re.sub(r"\{([^{}]+)\}", replace, template)


def _sanitize_filename(name: str, sanitize: bool) -> str:
    name = name.strip()
    if not name:
        name = "未命名航空电子客票"
    if sanitize:
        name = re.sub(INVALID_FILENAME_CHARS, "_", name)
        name = re.sub(r"_+", "_", name).strip(" ._")
    return name or "未命名航空电子客票"
