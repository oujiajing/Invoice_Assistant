from invoice_helper.airline_invoice import build_airline_invoice_preview_name, parse_airline_invoice_text
from invoice_helper.models import AirlineInvoiceFields, RenameRuleConfig, RenameRuleToken


NEW_STYLE_TEXT = """
电子发票（普通发票） 发票号码：
开票日期：
旅客运输服务
900000000000000003
2026年03月18日
测试乘客 示例航空公司
900000000000000008
¥ 857.34 ¥ 72.66
玖佰叁拾圆整 ¥ 930.00
闫飞
*运输服务*国内机票款 807.34 1 807.34 9% 72.66
*代收民航发展基金*民航发展基金 50.00 1 50.00 不征税
测试乘客 000000******000001 2025-09-15 北京 广州 经济舱 飞机
测试乘客 20250915 JD5921 经济舱 Q舱 北京大兴-广州 9000000000001
"""

OLD_STYLE_TEXT = """
海南增值税电子普通发票
900000000011
05124873
2026      03     18
贰佰捌拾玖圆整 ¥ 289.00
¥269.27
测试乘客 20251228 HU7801 经济舱 B舱 北京首都-广州 9000000000002
¥19.73
*运输服务*国内机票款 219.279% 19.73
*代收民航发展基金*民航发展基金 50.00不征税 ***
测试乘客
示例航空公司
"""


def test_parse_new_style_airline_invoice():
    fields = parse_airline_invoice_text(NEW_STYLE_TEXT)

    assert fields.invoice_number == "900000000000000003"
    assert fields.issue_date == "2026-03-18"
    assert fields.departure_airport == "北京大兴"
    assert fields.arrival_airport == "广州"
    assert fields.flight_number == "JD5921"
    assert fields.cabin_class == "经济舱 Q舱"
    assert fields.amount == "807.34"
    assert fields.total_amount == "930.00"
    assert fields.passenger_name == "测试乘客"
    assert fields.passenger_id == "000000******000001"


def test_parse_old_style_airline_invoice():
    fields = parse_airline_invoice_text(OLD_STYLE_TEXT)

    assert fields.invoice_number == "05124873"
    assert fields.issue_date == "2026-03-18"
    assert fields.departure_airport == "北京首都"
    assert fields.arrival_airport == "广州"
    assert fields.flight_number == "HU7801"
    assert fields.cabin_class == "经济舱 B舱"
    assert fields.amount == "219.27"
    assert fields.total_amount == "289.00"
    assert fields.passenger_name == "测试乘客"


def test_build_airline_preview_name():
    fields = AirlineInvoiceFields(
        invoice_number="05124873",
        issue_date="2026-03-18",
        departure_airport="北京首都",
        arrival_airport="广州",
        flight_number="HU7801",
        total_amount="289.00",
    )
    rule = RenameRuleConfig(
        mode="tokens",
        tokens=[
            RenameRuleToken(type="field", value="issue_date"),
            RenameRuleToken(type="field", value="departure_airport"),
            RenameRuleToken(type="field", value="arrival_airport"),
            RenameRuleToken(type="field", value="flight_number"),
        ],
        date_format="YYYY-MM-DD",
    )

    assert build_airline_invoice_preview_name(fields, rule) == "2026-03-18_北京首都_广州_HU7801"
