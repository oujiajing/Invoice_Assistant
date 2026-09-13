from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import GeneralInvoiceFields, RenameRuleConfig, normalize_amount
from .railway import apply_duplicate_strategy, extract_text_from_ofd_bytes, extract_text_from_pdf_bytes

INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
CHINESE_DATE_RE = re.compile(r"(20\d{2})年\s*(\d{2})月\s*(\d{2})日")
GENERAL_TEMPLATE_ALIASES = {
    "发票类型": "invoice_type",
    "发票代码": "invoice_code",
    "发票号码": "invoice_number",
    "开票日期": "issue_date",
    "购买方名称": "buyer_name",
    "购买方税号": "buyer_tax_number",
    "销售方名称": "seller_name",
    "销售方税号": "seller_tax_number",
    "发票金额": "amount",
    "发票税额": "tax_amount",
    "价税合计": "total_amount",
    "价税合计大写": "total_amount_upper",
    "备注": "remarks",
    "收款人": "payee",
    "复核人": "reviewer",
    "开票人": "issuer",
    "自定义内容": "custom_content",
}
SELLER_SUFFIXES = [
    "第一税务所",
    "第二分公司",
    "大学城酒店分公司",
    "酒店分公司",
    "分公司",
    "有限责任公司",
    "有限公司",
    "服务部",
    "饭店",
    "宾馆",
    "酒店",
    "税务局",
    "研究院",
]


def parse_general_invoice_from_bytes(file_name: str, file_bytes: bytes) -> GeneralInvoiceFields:
    from .document_text import extract_document_text

    extracted = extract_document_text(file_name, file_bytes, validator=parse_general_invoice_text)
    fields = parse_general_invoice_text(extracted.text)
    fields.parse_source = extracted.source
    fields.raw_text = extracted.text
    return fields


def parse_general_invoice_text(text: str) -> GeneralInvoiceFields:
    normalized_text = text.replace("\x00", "")
    if "发票" not in normalized_text:
        raise ValueError("未识别为常规数电发票文件。")

    lines = _normalize_lines(normalized_text)
    compact = "".join(lines)
    fields = GeneralInvoiceFields()
    fields.invoice_type = _extract_invoice_type(compact)
    fields.invoice_code = _extract_invoice_code(lines, compact)
    fields.invoice_number = _extract_invoice_number(lines, compact)
    fields.issue_date = _extract_issue_date(lines, compact)

    buyer_name, buyer_tax_number, seller_name, seller_tax_number = _extract_parties(lines, compact, fields.invoice_number)
    fields.buyer_name = buyer_name
    fields.buyer_tax_number = buyer_tax_number
    fields.seller_name = seller_name
    fields.seller_tax_number = seller_tax_number

    fields.amount, fields.tax_amount, fields.total_amount = _extract_amounts(lines, compact)
    fields.total_amount_upper = _extract_total_amount_upper(compact)
    fields.payee = _search_group(compact, r"收款人[:：]?([\u4e00-\u9fffA-Za-z·@.\-]{2,40})")
    fields.reviewer = _search_group(compact, r"复核人[:：]?([\u4e00-\u9fffA-Za-z·@.\-]{2,40})")
    fields.issuer = _extract_issuer(lines, compact)
    fields.remarks = _extract_remarks(lines, compact, fields)
    return fields


def build_general_invoice_preview_name(fields: GeneralInvoiceFields, rule: RenameRuleConfig) -> str:
    values = _formatted_value_map(fields, rule)
    if rule.mode == "template":
        return _sanitize_filename(_render_template(rule.template, values), rule.sanitize, "未命名常规数电发票")

    parts: list[str] = []
    for token in rule.tokens:
      if token.type == "field":
          parts.append(values.get(token.value, ""))
      elif token.type == "text":
          parts.append(token.value)
    return _sanitize_filename(rule.separator.join(part for part in parts if part), rule.sanitize, "未命名常规数电发票")


def _normalize_lines(text: str) -> list[str]:
    return [line.strip().replace(" ", "") for line in text.splitlines() if line.strip()]


def _search_group(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _normalize_date(value: str) -> str:
    cleaned = value.replace("^t", "年").replace("g", "月").replace("e", "日")
    match = CHINESE_DATE_RE.search(cleaned)
    if not match:
        return ""
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def _extract_invoice_type(compact: str) -> str:
    normalized = compact.replace("⼦", "子")
    if "增值税专用发票" in normalized:
        return "电子发票（增值税专用发票）"
    if "广东增值税电子普通发票" in normalized:
        return "广东增值税电子普通发票"
    if "普通发票" in normalized:
        return "电子发票（普通发票）"
    return "常规数电发票"


def _extract_parties(lines: list[str], compact: str, invoice_number: str) -> tuple[str, str, str, str]:
    buyer_name = ""
    buyer_tax_number = ""
    seller_name = ""
    seller_tax_number = ""

    direct_names = []
    for line in lines:
        name_match = re.match(r"名称[:：](.+)", line)
        if name_match and name_match.group(1).strip():
            direct_names.append(name_match.group(1).strip())
    direct_taxes = [
        _search_group(line, r"(?:统一社会信用代码/?纳税人识别号|统一社会信用代码/纳税人识别号)[:：]?([0-9A-Z]{15,20})")
        for line in lines
        if "统一社会信用代码" in line or "纳税人识别号" in line
    ]
    direct_taxes = [item for item in direct_taxes if item and item != invoice_number]
    if len(direct_names) >= 2:
        buyer_name, seller_name = direct_names[0], direct_names[1]
    if len(direct_taxes) >= 2:
        buyer_tax_number, seller_tax_number = direct_taxes[0], direct_taxes[1]

    if buyer_name and seller_name and buyer_tax_number and seller_tax_number:
        return buyer_name, buyer_tax_number, seller_name, seller_tax_number

    issue_index = next((idx for idx, line in enumerate(lines) if _normalize_date(line)), 0)
    end_index = next(
        (idx for idx, line in enumerate(lines[issue_index + 1 :], start=issue_index + 1) if "项目名称" in line or line.startswith("合计") or "价税合计" in line),
        min(len(lines), issue_index + 8),
    )
    candidate_lines = lines[issue_index + 1 : end_index]
    candidate_names = [
        line
        for line in candidate_lines
        if re.search(r"[\u4e00-\u9fff]", line)
        and len(line) >= 3
        and "名称" not in line
        and "纳税人识别号" not in line
        and "项目名称" not in line
        and "价税合计" not in line
        and "开票人" not in line
        and "发票号码" not in line
        and "开票日期" not in line
        and "统一社会信用代码" not in line
        and "纳税人识别号" not in line
        and "购买方" not in line
        and "销售方" not in line
        and "规格型号" not in line
        and "*" not in line
        and "%" not in line
        and "RMB" not in line
        and not re.search(r"\d{4,}", line)
        and line not in {"购买方信息", "销售方信息"}
    ]
    candidate_tax_lines = [line for line in candidate_lines if re.fullmatch(r"[0-9A-Z]{15,40}", line)]

    if not buyer_name and len(candidate_names) >= 2:
        buyer_name, seller_name = candidate_names[0], candidate_names[1]
    if not buyer_tax_number and len(candidate_tax_lines) >= 2:
        buyer_tax_number, seller_tax_number = candidate_tax_lines[0], candidate_tax_lines[1]

    if len(candidate_names) == 1 and len(candidate_tax_lines) == 1 and len(candidate_tax_lines[0]) >= 30:
        buyer_tax_number, seller_tax_number = _split_tax_numbers(candidate_tax_lines[0])
        buyer_name, seller_name = _split_name_pair(candidate_names[0])

    if not all([buyer_name, seller_name, buyer_tax_number, seller_tax_number]):
        tail_names = re.findall(r"名称[:：]?([\u4e00-\u9fffA-Za-z（）()·]+)", compact)
        tail_taxes = re.findall(r"(?:统一社会信用代码/?纳税人识别号|纳税人识别号)[:：]?([0-9A-Z]{15,20})", compact)
        tail_taxes = [item for item in tail_taxes if item != invoice_number]
        if len(tail_names) >= 2:
            buyer_name = buyer_name or tail_names[0]
            seller_name = seller_name or tail_names[1]
        if len(tail_taxes) >= 2:
            buyer_tax_number = buyer_tax_number or tail_taxes[0]
            seller_tax_number = seller_tax_number or tail_taxes[1]

    return buyer_name, buyer_tax_number, seller_name, seller_tax_number


def _split_tax_numbers(line: str) -> tuple[str, str]:
    if len(line) == 36:
        return line[:18], line[18:]
    matches = re.findall(r"[0-9A-Z]{15,20}", line)
    if len(matches) >= 2:
        return matches[0], matches[1]
    midpoint = len(line) // 2
    return line[:midpoint], line[midpoint:]


def _split_name_pair(line: str) -> tuple[str, str]:
    best_pair = ("", "")
    for suffix in SELLER_SUFFIXES:
        if line.endswith(suffix):
            for start in range(1, len(line)):
                seller = line[start:]
                buyer = line[:start]
                if (
                    seller.endswith(suffix)
                    and any(keyword in seller for keyword in ("公司", "酒店", "饭店", "宾馆", "服务", "税务", "研究院"))
                    and not any(keyword in buyer for keyword in ("公司", "酒店", "饭店", "宾馆", "服务部", "税务局"))
                ):
                    if buyer.endswith(("大学", "研究院")):
                        return buyer, seller
                    best_pair = best_pair if len(best_pair[0]) >= len(buyer) else (buyer, seller)
    if all(best_pair):
        return best_pair
    if "广东工业大学" in line:
        return "广东工业大学", line.replace("广东工业大学", "", 1)
    return line, ""


def _extract_amounts(lines: list[str], compact: str) -> tuple[str, str, str]:
    total_amount = _extract_total_amount(lines, compact)
    amount = ""
    tax_amount = ""

    amount_line_match = re.findall(r"[¥￥]\s?(\d+\.\d{2})", compact)
    if len(amount_line_match) >= 3:
        amount = amount_line_match[-3]
        tax_amount = amount_line_match[-2]
        total_amount = total_amount or amount_line_match[-1]

    pair_match = re.search(r"合计¥?(\d+\.\d{2})¥?(\d+\.\d{2})", compact)
    if pair_match:
        amount = amount or pair_match.group(1)
        tax_amount = tax_amount or pair_match.group(2)

    line_pair = next((re.findall(r"\d+\.\d{2}", line) for line in lines if line.count("¥") >= 2), [])
    if len(line_pair) >= 2:
        amount = amount or line_pair[0]
        tax_amount = tax_amount or line_pair[1]

    return normalize_amount(amount), normalize_amount(tax_amount), normalize_amount(total_amount)


def _extract_total_amount_upper(compact: str) -> str:
    numeral_chars = "零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆角分整"
    match = re.search(rf"价税合计（大写）([{numeral_chars}]+)(?:（小写）)?¥?\d+\.\d{{2}}", compact)
    if match:
        return match.group(1)
    match = re.search(rf"([{numeral_chars}]{{4,}})（小写）¥\d+\.\d{{2}}", compact)
    if match:
        return match.group(1)
    matches = re.findall(rf"([{numeral_chars}]{{4,}})¥\d+\.\d{{2}}", compact)
    return matches[-1] if matches else ""


def _extract_issuer(lines: list[str], compact: str) -> str:
    issuer = _search_group(compact, r"开票人[:：]?([\u4e00-\u9fffA-Za-z·]{2,20})")
    if issuer and not any(keyword in issuer for keyword in ("圆", "角", "分", "税务", "国家", "发票", "监制")):
        return issuer
    for index, line in enumerate(lines):
        if line.startswith("开票人："):
            for next_line in lines[index + 1 : index + 18]:
                if (
                    re.fullmatch(r"[\u4e00-\u9fffA-Za-z·]{2,12}", next_line)
                    and not any(keyword in next_line for keyword in ("税务", "发票", "监制", "国家", "圆", "角", "分"))
                ):
                    return next_line
    return ""


def _extract_invoice_code(lines: list[str], compact: str) -> str:
    direct = _search_group(compact, r"发票代码[:：]?(\d{10,12})")
    if direct:
        return direct
    code_index = next((idx for idx, line in enumerate(lines) if "发票代码" in line), None)
    if code_index is not None:
        for line in lines[code_index + 1 : code_index + 4]:
            if re.fullmatch(r"\d{10,12}", line):
                return line
    return ""


def _extract_invoice_number(lines: list[str], compact: str) -> str:
    direct = _search_group(compact, r"发票号码[:：]?(\d{16,20})")
    if direct:
        return direct
    number_index = next((idx for idx, line in enumerate(lines) if "发票号码" in line), None)
    if number_index is not None:
        for line in lines[number_index + 1 : number_index + 6]:
            if re.fullmatch(r"\d{16,20}", line):
                return line
    return _search_group(compact, r"(\d{16,20})")


def _extract_issue_date(lines: list[str], compact: str) -> str:
    direct = _normalize_date(_search_group(compact, r"开票日期[:：]?((?:20\d{2}).{0,6}?(?:\d{2}).{0,4}?(?:\d{2})日)"))
    if direct:
        return direct
    date_index = next((idx for idx, line in enumerate(lines) if "开票日期" in line), None)
    if date_index is not None:
        for line in lines[date_index + 1 : date_index + 5]:
            normalized = _normalize_date(line)
            if normalized:
                return normalized
    for line in lines:
        normalized = _normalize_date(line)
        if normalized:
            return normalized
    return ""


def _extract_total_amount(lines: list[str], compact: str) -> str:
    direct = _search_group(compact, r"(?:（小写）|小写\)|小写）)[¥￥]\s?(\d+\.\d{2})")
    if direct:
        return normalize_amount(direct)
    numeral_pairs = re.findall(r"([零壹贰叁肆伍陆柒捌玖拾佰仟万亿圆角分整]{4,})[¥￥]\s?(\d+\.\d{2})", compact)
    if numeral_pairs:
        return normalize_amount(numeral_pairs[-1][1])
    currencies = re.findall(r"[¥￥]\s?(\d+\.\d{2})", compact)
    return normalize_amount(currencies[-1]) if currencies else ""


def _extract_remarks(lines: list[str], compact: str, fields: GeneralInvoiceFields) -> str:
    remark_candidates = [
        line
        for line in lines
        if any(keyword in line for keyword in ("开户银行", "银行账号", "电话", "地址", "入住日期", "个月", "行程"))
    ]
    if remark_candidates:
        return "；".join(dict.fromkeys(remark_candidates))

    match = re.search(r"备注(.+?)开票人", compact)
    if match:
        remark = match.group(1)
        for value in (fields.payee, fields.reviewer, fields.issuer):
            remark = remark.replace(value, "")
        return remark.strip("：:;；")
    return ""


def _formatted_value_map(fields: GeneralInvoiceFields, rule: RenameRuleConfig) -> dict[str, str]:
    return {
        "invoice_type": fields.invoice_type,
        "invoice_code": fields.invoice_code,
        "invoice_number": fields.invoice_number,
        "issue_date": _format_date(fields.issue_date, rule.date_format),
        "buyer_name": fields.buyer_name,
        "buyer_tax_number": fields.buyer_tax_number,
        "seller_name": fields.seller_name,
        "seller_tax_number": fields.seller_tax_number,
        "amount": normalize_amount(fields.amount) if rule.amount_format == "0.00" else fields.amount,
        "tax_amount": normalize_amount(fields.tax_amount) if rule.amount_format == "0.00" else fields.tax_amount,
        "total_amount": normalize_amount(fields.total_amount) if rule.amount_format == "0.00" else fields.total_amount,
        "total_amount_upper": fields.total_amount_upper,
        "remarks": fields.remarks,
        "payee": fields.payee,
        "reviewer": fields.reviewer,
        "issuer": fields.issuer,
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


def _render_template(template: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        return values.get(GENERAL_TEMPLATE_ALIASES.get(key, key), "")

    return re.sub(r"\{([^{}]+)\}", replace, template)


def _sanitize_filename(name: str, sanitize: bool, fallback: str) -> str:
    name = name.strip()
    if not name:
        name = fallback
    if sanitize:
        name = re.sub(INVALID_FILENAME_CHARS, "_", name)
        name = re.sub(r"_+", "_", name).strip(" ._")
    return name or fallback
