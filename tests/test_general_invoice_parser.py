from invoice_helper.general_invoice import build_general_invoice_preview_name, parse_general_invoice_text
from invoice_helper.models import GeneralInvoiceFields, RenameRuleConfig, RenameRuleToken


GENERAL_INVOICE_TEXT = """
电子发票（普通发票） 发票号码：
开票日期：
25317000000630235720
2025年04月04日
购
买
方
信
息
名称：广东工业大学
统一社会信用代码/纳税人识别号:12440000455860226X
销
售
方
信
息
名称：阿斯兰航空服务（上海）有限公司
统一社会信用代码/纳税人识别号:913101150529904218
项目名称 规格型号 单 位 数 量 单 价 金 额 税率/征收率 税 额
*经纪代理服务*代订机票费
个 1 399.06 399.06 6% 23.94
*经纪代理服务*代订附加产品
个 1 33.96 33.96 6% 2.04
合计 ¥433.02 ¥25.98
价税合计（大写）
肆佰伍拾玖圆整 （小写）¥459.00
备注
开票人：唐玉玲
"""


def test_parse_general_invoice_text():
    fields = parse_general_invoice_text(GENERAL_INVOICE_TEXT)

    assert fields.invoice_type == "电子发票（普通发票）"
    assert fields.invoice_number == "25317000000630235720"
    assert fields.issue_date == "2025-04-04"
    assert fields.buyer_name == "广东工业大学"
    assert fields.buyer_tax_number == "12440000455860226X"
    assert fields.seller_name == "阿斯兰航空服务（上海）有限公司"
    assert fields.seller_tax_number == "913101150529904218"
    assert fields.amount == "433.02"
    assert fields.tax_amount == "25.98"
    assert fields.total_amount == "459.00"
    assert fields.total_amount_upper == "肆佰伍拾玖圆整"
    assert fields.issuer == "唐玉玲"


def test_build_general_invoice_preview_name():
    fields = GeneralInvoiceFields(
        invoice_type="电子发票（普通发票）",
        invoice_number="25317000000630235720",
        issue_date="2025-04-04",
        seller_name="阿斯兰航空服务（上海）有限公司",
        total_amount="459.00",
        issuer="唐玉玲",
    )
    token_rule = RenameRuleConfig(
        mode="tokens",
        tokens=[
            RenameRuleToken(type="field", value="issue_date"),
            RenameRuleToken(type="field", value="seller_name"),
            RenameRuleToken(type="field", value="total_amount"),
        ],
        date_format="YYYY-MM-DD",
    )

    assert build_general_invoice_preview_name(fields, token_rule) == "2025-04-04_阿斯兰航空服务（上海）有限公司_459.00"
