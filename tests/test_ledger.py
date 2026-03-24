from invoice_helper.ledger import build_ledger_entry


def test_build_ledger_entry_uses_fixed_railway_item_summary():
    entry = build_ledger_entry(
        entry_id="rail-1",
        category="railway",
        fields={
            "invoice_number": "123",
            "issue_date": "2025-03-31",
            "departure_station": "广州南站",
            "arrival_station": "长沙南站",
            "train_number": "G810",
            "amount": "314.00",
            "passenger_name": "李志",
        },
        raw_text="铁路电子客票",
        original_name="rail.pdf",
        stored_path="C:/tmp/rail.pdf",
        file_type="pdf",
    )

    assert entry["item_summary"] == "网上购票系统-电子发票通知"


def test_build_ledger_entry_extracts_general_item_summary_from_item_lines():
    raw_text = """
    电子发票（普通发票）
    项目名称 规格型号 单位 数量 单价 金额
    *住宿服务*住宿1天99.01
    合计
    """

    entry = build_ledger_entry(
        entry_id="hotel-1",
        category="general",
        fields={
            "invoice_type": "电子发票（普通发票）",
            "invoice_number": "25312000000002446025",
            "issue_date": "2025-01-08",
            "buyer_name": "广东工业大学",
            "seller_name": "北京大小酒店有限公司雅乐轩饭店",
            "total_amount": "629.64",
            "remarks": "备注里的住宿内容",
        },
        raw_text=raw_text,
        original_name="hotel.pdf",
        stored_path="C:/tmp/hotel.pdf",
        file_type="pdf",
    )

    assert entry["item_summary"] == "*住宿服务*住宿"


def test_build_ledger_entry_extracts_airline_item_summary_from_service_name():
    raw_text = """
    电子发票（普通发票）
    货物或应税劳务、服务名称
    *运输服务*国内机票款200.929%18.08
    *代收民航发展基金*民航发展基金50.00不征税
    """

    entry = build_ledger_entry(
        entry_id="air-1",
        category="airline",
        fields={
            "invoice_number": "26112000001054174981",
            "issue_date": "2026-03-18",
            "departure_airport": "北京大兴",
            "arrival_airport": "广州",
            "flight_number": "JD5921",
            "passenger_name": "李志",
            "total_amount": "269.00",
        },
        raw_text=raw_text,
        original_name="air.pdf",
        stored_path="C:/tmp/air.pdf",
        file_type="pdf",
    )

    assert entry["item_summary"] == "*运输服务*国内机票款*代收民航发展基金*民航发展基金"
