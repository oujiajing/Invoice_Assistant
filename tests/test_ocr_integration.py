from invoice_helper import document_text
from invoice_helper.airline_invoice import parse_airline_invoice_from_bytes
from invoice_helper.airline_invoice import parse_airline_invoice_text
from invoice_helper.general_invoice import parse_general_invoice_text
from invoice_helper.railway import parse_railway_ticket_from_bytes


RAILWAY_OCR_TEXT = """
国家税务总局
开票日期:2025年04月01日
发票号码:900000000000000001
武汉站 北京西站 G70 2025年03月31日 08:36开 08车05B号
票价:￥623.00
0000000000****0001测试乘客
电子发票（铁路电子客票）
"""


def test_image_ocr_text_is_reused_by_existing_parser(monkeypatch):
    monkeypatch.setattr(document_text, "recognize_image_bytes", lambda *_args: RAILWAY_OCR_TEXT)

    fields = parse_railway_ticket_from_bytes("ticket.png", b"fake-image")

    assert fields.invoice_number == "900000000000000001"
    assert fields.amount == "623.00"
    assert fields.parse_source == "ocr"
    assert fields.raw_text == RAILWAY_OCR_TEXT


def test_scanned_pdf_falls_back_to_ocr_after_native_parser_failure(monkeypatch):
    monkeypatch.setattr(document_text, "extract_native_pdf_text", lambda _bytes: "too short")
    monkeypatch.setattr(document_text, "recognize_pdf_bytes", lambda _bytes: RAILWAY_OCR_TEXT)

    fields = parse_railway_ticket_from_bytes("ticket.pdf", b"fake-pdf")

    assert fields.invoice_number == "900000000000000001"
    assert fields.parse_source == "ocr"


def test_native_pdf_does_not_call_ocr_when_parser_succeeds(monkeypatch):
    monkeypatch.setattr(document_text, "extract_native_pdf_text", lambda _bytes: RAILWAY_OCR_TEXT)
    monkeypatch.setattr(
        document_text,
        "recognize_pdf_bytes",
        lambda _bytes: (_ for _ in ()).throw(AssertionError("native PDF should not call OCR")),
    )

    fields = parse_railway_ticket_from_bytes("ticket.pdf", b"fake-pdf")

    assert fields.parse_source == "native"


def test_native_pdf_parser_mismatch_does_not_trigger_ocr(monkeypatch):
    monkeypatch.setattr(document_text, "extract_native_pdf_text", lambda _bytes: "valid native text " * 5)
    monkeypatch.setattr(
        document_text,
        "recognize_pdf_bytes",
        lambda _bytes: (_ for _ in ()).throw(AssertionError("parser mismatch must not trigger OCR")),
    )

    try:
        parse_railway_ticket_from_bytes("ordinary.pdf", b"fake-pdf")
    except ValueError as exc:
        assert "铁路电子客票" in str(exc)
    else:
        raise AssertionError("expected native parser mismatch")


def test_image_ocr_failure_is_reported_by_parser(monkeypatch):
    monkeypatch.setattr(
        document_text,
        "recognize_image_bytes",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("模型不可用")),
    )

    try:
        parse_airline_invoice_from_bytes("airline.jpg", b"fake-image")
    except RuntimeError as exc:
        assert "模型不可用" in str(exc)
    else:
        raise AssertionError("expected OCR failure")


def test_ocr_text_handles_split_railway_label_and_passenger_lines():
    text = """
    铁路日
    电子发票
    子客票
    开票日期:2026年01月12日
    北京
    哈尔滨
    Z15
    站
    站
    2025年09月27日
    21:16开
    08车001号
    退票费：￥43.00
    李志
    4307231982****0037
    中国铁路祝您旅途愉快
    发票号码:26119210001000004077
    """
    from invoice_helper.railway import parse_railway_ticket_text

    fields = parse_railway_ticket_text(text)

    assert fields.departure_station == "北京站"
    assert fields.arrival_station == "哈尔滨站"
    assert fields.passenger_name == "李志"
    assert fields.passenger_id == "4307231982****0037"


def test_ocr_text_handles_full_width_currency_and_ascii_name_colon():
    text = """
    电子发票普通发票
    发票号码：25112000000150433895
    开票日期：2025年07月19日
    购买方信息
    名称：上海浙江大学高等研究院
    销售方信息
    名称:北京食尚引领餐饮管理有限公司
    项目名称 *餐饮服务*餐饮服务
    2169.81 130.19
    合计 ￥2169.81 ￥130.19
    价税合计（大写）贰仟叁佰圆整
    （小写）￥2300.00
    """
    fields = parse_general_invoice_text(text)

    assert fields.seller_name == "北京食尚引领餐饮管理有限公司"
    assert fields.amount == "2169.81"
    assert fields.tax_amount == "130.19"
    assert fields.total_amount == "2300.00"


def test_ocr_text_handles_airline_route_without_separate_cabin_class():
    text = """
    海南增值税电子普通发票
    发票号码：04453068
    开票日期:2025年10月24日
    *运输服务*国内机票款 200.92
    （小写）￥269.00
    李志 20251023 HU7131 B舱广州-上海虹桥 8802182899
    """
    fields = parse_airline_invoice_text(text)

    assert fields.invoice_number == "04453068"
    assert fields.flight_number == "HU7131"
    assert fields.departure_airport == "广州"
    assert fields.arrival_airport == "上海虹桥"
    assert fields.total_amount == "269.00"
