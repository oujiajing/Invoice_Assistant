from __future__ import annotations

import re
import zipfile
from collections import Counter
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

from pypdf import PdfReader

from .models import RailwayTicketFields, RenameRuleConfig, normalize_amount

FIELD_LABELS = {
    "invoice_number": "发票号码",
    "issue_date": "开票日期",
    "departure_station": "出发站",
    "arrival_station": "到达站",
    "departure_datetime": "发车时间",
    "train_number": "车次",
    "seat_number": "座位号",
    "amount": "票价",
    "passenger_name": "乘车人姓名",
    "passenger_id": "乘车人身份证号",
    "custom_content": "自定义内容",
}

TEMPLATE_ALIASES = {
    "发票号码": "invoice_number",
    "开票日期": "issue_date",
    "出发站": "departure_station",
    "到达站": "arrival_station",
    "终点站": "arrival_station",
    "终到站": "arrival_station",
    "发车时间": "departure_datetime",
    "车次": "train_number",
    "座位号": "seat_number",
    "票价": "amount",
    "乘车人姓名": "passenger_name",
    "乘车人身份证号": "passenger_id",
    "自定义内容": "custom_content",
}

INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
CHINESE_DATE_RE = re.compile(r"(20\d{2})年\s*(\d{2})月\s*(\d{2})日")
DATETIME_RE = re.compile(r"(20\d{2})年\s*(\d{2})月\s*(\d{2})日(\d{2}:\d{2})开")


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_text_from_ofd_bytes(file_bytes: bytes) -> str:
    texts: list[str] = []
    with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
        xml_names = sorted(name for name in archive.namelist() if name.lower().endswith(".xml"))
        for name in xml_names:
            raw = archive.read(name)
            try:
                root = ElementTree.fromstring(raw)
            except ElementTree.ParseError:
                continue
            for element in root.iter():
                chunks = []
                if element.text and element.text.strip():
                    chunks.append(element.text.strip())
                for key, value in element.attrib.items():
                    if key.lower().endswith("value") and value.strip():
                        chunks.append(value.strip())
                if chunks:
                    texts.append("".join(chunks))
    return "\n".join(texts)


def parse_railway_ticket_from_bytes(file_name: str, file_bytes: bytes) -> RailwayTicketFields:
    from .document_text import extract_document_text

    extracted = extract_document_text(file_name, file_bytes, validator=parse_railway_ticket_text)
    fields = parse_railway_ticket_text(extracted.text)
    fields.parse_source = extracted.source
    fields.raw_text = extracted.text
    return fields


def parse_railway_ticket_text(text: str) -> RailwayTicketFields:
    if not (
        "铁路电子客票" in text
        or ("铁路" in text and "客票" in text and ("中国铁路" in text or "电子发票" in text))
    ):
        raise ValueError("未识别为铁路电子客票文件。")

    lines = _normalize_lines(text)
    compact = "".join(lines)
    fields = RailwayTicketFields()

    fields.invoice_number = _search_group(compact, r"发票号码[:：]?(\d{16,20})")
    fields.issue_date = _normalize_date(_search_group(compact, r"开票日期[:：]?((?:20\d{2})年(?:\d{2})月(?:\d{2})日)"))
    fields.train_number = _extract_train_number(lines, compact)
    fields.departure_datetime = _extract_departure_datetime(compact, lines)
    fields.seat_number = _extract_seat_number(lines, compact)
    fields.amount = normalize_amount(_extract_amount(compact, lines))
    fields.passenger_id, fields.passenger_name = _extract_passenger(compact, lines)
    fields.ticket_label = _extract_ticket_label(compact)
    departure_station, arrival_station = _extract_stations(lines)
    fields.departure_station = departure_station
    fields.arrival_station = arrival_station
    return fields


def build_preview_name(fields: RailwayTicketFields, rule: RenameRuleConfig) -> str:
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


def apply_duplicate_strategy(names: Iterable[str]) -> list[str]:
    counter: Counter[str] = Counter()
    resolved: list[str] = []
    for name in names:
        base = name or "未命名铁路电子客票"
        counter[base] += 1
        if counter[base] == 1:
            resolved.append(base)
        else:
            resolved.append(f"{base}({counter[base] - 1})")
    return resolved


def _normalize_lines(text: str) -> list[str]:
    return [line.strip().replace(" ", "") for line in text.splitlines() if line.strip()]


def _search_group(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _normalize_date(value: str) -> str:
    match = CHINESE_DATE_RE.search(value or "")
    if not match:
        return ""
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def _extract_departure_datetime(compact: str, lines: list[str]) -> str:
    datetime_match = DATETIME_RE.search(compact)
    if datetime_match:
        return f"{datetime_match.group(1)}-{datetime_match.group(2)}-{datetime_match.group(3)} {datetime_match.group(4)}"

    date_index = _find_first_line(lines, lambda line: bool(CHINESE_DATE_RE.fullmatch(line)))
    time_index = _find_first_line(lines, lambda line: bool(re.search(r"(\d{2}:\d{2})开", line)))
    if date_index is not None and time_index is not None:
        date_value = _normalize_date(lines[date_index])
        time_value = _search_group(lines[time_index], r"(\d{2}:\d{2})开")
        return f"{date_value} {time_value}"
    return ""


def _extract_seat_number(lines: list[str], compact: str) -> str:
    inline_match = next((re.search(r"开(\d{2}车[0-9A-Z]{2,5}号)", line) for line in lines if "开" in line), None)
    if inline_match:
        return inline_match.group(1)
    line_match = next(
        (line for line in lines if re.fullmatch(r"\d{2}车[0-9A-Z]{2,5}号", line) or line == "无座"),
        "",
    )
    if line_match:
        return line_match
    return _search_group(compact, r"(\d{2}车[0-9A-Z]{2,5}号|无座)")


def _extract_amount(compact: str, lines: list[str]) -> str:
    match = re.search(r"(票价|改签费|退票费|补票)[:：]?￥?(\d+\.\d{2})", compact)
    if match:
        return match.group(2)

    for index, line in enumerate(lines):
        if line in {"￥", "票价:", "票价:￥"} and index + 1 < len(lines):
            next_line = lines[index + 1]
            if re.fullmatch(r"\d+\.\d{2}", next_line):
                return next_line
    return _search_group(compact, r"￥(\d+\.\d{2})")


def _extract_passenger(compact: str, lines: list[str]) -> tuple[str, str]:
    for index, line in enumerate(lines[:-1]):
        if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", line):
            id_match = re.fullmatch(r"\d{10}\*+\w{2,6}", lines[index + 1])
            if id_match:
                return id_match.group(0), line
    for line in lines:
        line_match = re.search(r"(\d{6}\d{4}\*+\w{0,4})([\u4e00-\u9fff]{2,4})$", line)
        if line_match:
            return line_match.group(1), line_match.group(2)
    match = re.search(r"(\d{6}\d{4}\*+\w{0,4})([\u4e00-\u9fff]{2,4})(?:电子客票号|统一社会信用代码|购买方名称)", compact)
    if match:
        return match.group(1), match.group(2)
    return "", ""


def _extract_ticket_label(compact: str) -> str:
    for label in ("退票费", "改签费", "补票", "始发改签"):
        if label in compact:
            return label
    return "票价"


def _extract_stations(lines: list[str]) -> tuple[str, str]:
    travel_date_index = _find_first_line(lines, lambda line: bool(CHINESE_DATE_RE.fullmatch(line)))
    if travel_date_index is not None:
        nearby = _collect_nearby_station_names(lines[max(0, travel_date_index - 8):travel_date_index])
        if len(nearby) >= 2:
            return nearby[0], nearby[1]
        station_candidates = [
            line
            for line in lines[max(0, travel_date_index - 8):travel_date_index]
            if re.fullmatch(r"[\u4e00-\u9fff]{2,8}", line)
            and line != "站"
            and not line.endswith("税务局")
            and "发票" not in line
            and "铁路" not in line
            and "客票" not in line
        ]
        if len(station_candidates) >= 2:
            return f"{station_candidates[0]}站", f"{station_candidates[1]}站"

    issue_date_index = _find_first_line(lines, lambda line: line.startswith("开票日期:"))
    if issue_date_index is not None:
        trailing_lines = lines[issue_date_index + 1 : issue_date_index + 6]
        trailing_stations = _collect_station_names(trailing_lines)
        if len(trailing_stations) >= 2:
            return trailing_stations[-1], trailing_stations[0]

    all_stations = _collect_station_names(lines)
    if len(all_stations) >= 2:
        return all_stations[0], all_stations[1]
    return "", ""


def _collect_station_names(lines: list[str]) -> list[str]:
    normalized: list[str] = []
    merged = []
    for line in lines:
        if "站" in line and re.search(r"[\u4e00-\u9fff]", line):
            merged.extend(re.findall(r"[\u4e00-\u9fff]{1,8}?站", line))

    for station in merged:
        station = station.replace("购买方名称", "").replace("中国铁路祝您旅途愉快", "")
        if station and station not in normalized:
            normalized.append(station)
    return normalized


def _collect_nearby_station_names(lines: list[str]) -> list[str]:
    stations: list[str] = []
    index = 0
    while index < len(lines):
        current = lines[index]
        if current == "站" and stations:
            stations[-1] = f"{stations[-1]}站"
            index += 1
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]{1,8}", current):
            if index + 1 < len(lines) and lines[index + 1] == "站":
                stations.append(f"{current}站")
                index += 2
                continue
            if current.endswith("站"):
                stations.append(current)
        index += 1
    return stations


def _extract_train_number(lines: list[str], compact: str) -> str:
    for line in lines:
        if re.fullmatch(r"[GDCZTKLYS]\d{1,4}", line):
            return line
    return _search_group(compact, r"([GDCZTKLYS]\d{1,4})")


def _find_first_line(lines: list[str], predicate) -> int | None:
    for index, line in enumerate(lines):
        if predicate(line):
            return index
    return None


def _formatted_value_map(fields: RailwayTicketFields, rule: RenameRuleConfig) -> dict[str, str]:
    departure_datetime = _format_datetime(fields.departure_datetime, rule.date_format)
    issue_date = _format_date(fields.issue_date, rule.date_format)
    amount = normalize_amount(fields.amount) if rule.amount_format == "0.00" else fields.amount
    return {
        "invoice_number": fields.invoice_number,
        "issue_date": issue_date,
        "departure_station": fields.departure_station,
        "arrival_station": fields.arrival_station,
        "departure_datetime": departure_datetime,
        "train_number": fields.train_number,
        "seat_number": fields.seat_number,
        "amount": amount,
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


def _format_datetime(value: str, output_format: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return value
    if output_format == "YYYY-MM-DD":
        return parsed.strftime("%Y-%m-%d %H:%M")
    return parsed.strftime("%Y年%m月%d日 %H:%M")


def _render_template(template: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        internal_key = TEMPLATE_ALIASES.get(key, key)
        return values.get(internal_key, "")

    return re.sub(r"\{([^{}]+)\}", replace, template)


def _sanitize_filename(name: str, sanitize: bool) -> str:
    name = name.strip()
    if not name:
        name = "未命名铁路电子客票"
    if sanitize:
        name = re.sub(INVALID_FILENAME_CHARS, "_", name)
        name = re.sub(r"_+", "_", name).strip(" ._")
    return name or "未命名铁路电子客票"
