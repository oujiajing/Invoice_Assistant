from invoice_helper.models import RailwayTicketFields, RenameRuleConfig, RenameRuleToken
from invoice_helper.railway import apply_duplicate_strategy, build_preview_name, parse_railway_ticket_text


STANDARD_TEXT = """
国家税务总局
开票日期:2025年04月01日
发票号码:900000000000000001
武汉
站
北京西
站
G70
Wuhan
Beijingxi
2025年03月31日
08:36开
08车05B号
票价:
二等座
0000000000****0001测试乘客
电子客票号:900000000000000010
电子发票（铁路电子客票）
￥
623.00
"""

REVERSE_STATION_TEXT = """
国家税务总局
买票请到12306发货请到95306
发票号码:900000000000000002
Guangzhounan
G810
2025年03月30日
电子发票（铁路电子客票）
16:21开13车13D号
票价:￥314.00
二等座
0000000000****0001测试乘客
电子客票号:900000000000000011
测试乘客统一社会信用代码:
开票日期:2025年03月31日
Changshanan
长沙南站广州南站
始发改签
中国铁路祝您旅途愉快
"""


def test_parse_standard_ticket():
    fields = parse_railway_ticket_text(STANDARD_TEXT)

    assert fields.invoice_number == "900000000000000001"
    assert fields.issue_date == "2025-04-01"
    assert fields.departure_station == "武汉站"
    assert fields.arrival_station == "北京西站"
    assert fields.departure_datetime == "2025-03-31 08:36"
    assert fields.train_number == "G70"
    assert fields.seat_number == "08车05B号"
    assert fields.amount == "623.00"
    assert fields.passenger_name == "测试乘客"
    assert fields.passenger_id == "0000000000****0001"


def test_parse_reverse_station_ticket():
    fields = parse_railway_ticket_text(REVERSE_STATION_TEXT)

    assert fields.departure_station == "广州南站"
    assert fields.arrival_station == "长沙南站"
    assert fields.departure_datetime == "2025-03-30 16:21"
    assert fields.ticket_label == "始发改签"


def test_build_preview_name_for_tokens_and_template():
    fields = RailwayTicketFields(
        invoice_number="900000000000000006",
        issue_date="2025-03-31",
        departure_station="广州南站",
        arrival_station="长沙南站",
        departure_datetime="2025-03-30 16:21",
        amount="314.00",
        passenger_name="测试乘客",
    )
    token_rule = RenameRuleConfig(
        mode="tokens",
        tokens=[
            RenameRuleToken(type="field", value="issue_date"),
            RenameRuleToken(type="field", value="departure_station"),
            RenameRuleToken(type="text", value="差旅"),
            RenameRuleToken(type="field", value="amount"),
        ],
        separator="_",
        date_format="YYYY-MM-DD",
    )
    template_rule = RenameRuleConfig(
        mode="template",
        template="{开票日期}_{出发站}_{到达站}_{票价}",
        date_format="YYYY-MM-DD",
    )

    assert build_preview_name(fields, token_rule) == "2025-03-31_广州南站_差旅_314.00"
    assert build_preview_name(fields, template_rule) == "2025-03-31_广州南站_长沙南站_314.00"


def test_duplicate_strategy_adds_suffix():
    assert apply_duplicate_strategy(["a", "a", "b", "a"]) == ["a", "a(1)", "b", "a(2)"]
