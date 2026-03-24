from io import BytesIO
from pathlib import Path
import shutil

import pytest

import app as app_module
from invoice_helper.models import AirlineInvoiceFields, GeneralInvoiceFields, RailwayTicketFields


@pytest.fixture()
def client(monkeypatch):
    app_module.app.config["TESTING"] = True
    temp_root = Path.cwd() / ".pytest_tmp"
    temp_root.mkdir(exist_ok=True)
    upload_dir = temp_root / "uploads"
    upload_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(app_module, "UPLOAD_DIR", upload_dir)
    app_module.RAILWAY_DOCUMENT_STORE.clear()
    app_module.GENERAL_DOCUMENT_STORE.clear()
    app_module.AIRLINE_DOCUMENT_STORE.clear()
    yield app_module.app.test_client()
    shutil.rmtree(temp_root, ignore_errors=True)


def test_upload_preview_and_export_flow(client, monkeypatch):
    def fake_parse(file_name, file_bytes):
        return RailwayTicketFields(
            invoice_number="25429165800000526150",
            issue_date="2025-04-01",
            departure_station="武汉站",
            arrival_station="北京西站",
            departure_datetime="2025-03-31 08:36",
            train_number="G70",
            seat_number="08车05B号",
            amount="623.00",
            passenger_name="李志",
            passenger_id="4307231982****0037",
        )

    monkeypatch.setattr(app_module, "parse_railway_ticket_from_bytes", fake_parse)

    upload_response = client.post(
        "/api/railway/upload-and-parse",
        data={"files": (BytesIO(b"%PDF-1.4 fake"), "ticket.pdf")},
        content_type="multipart/form-data",
    )

    assert upload_response.status_code == 200
    documents = upload_response.get_json()
    assert len(documents) == 1
    assert documents[0]["fields"]["departure_station"] == "武汉站"

    preview_response = client.post(
        "/api/railway/preview-rename",
        json={
            "documentIds": [documents[0]["id"]],
            "ruleConfig": {
                "mode": "template",
                "template": "{开票日期}_{出发站}_{到达站}_{票价}",
                "dateFormat": "YYYY-MM-DD",
            },
        },
    )

    assert preview_response.status_code == 200
    preview_payload = preview_response.get_json()
    assert preview_payload[0]["conflictResolvedName"] == "2025-04-01_武汉站_北京西站_623.00"

    export_response = client.post(
        "/api/railway/export",
        json={
            "documentIds": [documents[0]["id"]],
            "ruleConfig": {
                "mode": "template",
                "template": "{开票日期}_{出发站}_{到达站}_{票价}",
                "dateFormat": "YYYY-MM-DD",
            },
        },
    )

    assert export_response.status_code == 200
    assert export_response.mimetype == "application/zip"


def test_delete_and_clear_documents(client, monkeypatch):
    def fake_parse(file_name, file_bytes):
        return RailwayTicketFields(
            invoice_number="25429165800000526150",
            issue_date="2025-04-01",
            departure_station="武汉站",
            arrival_station="北京西站",
            departure_datetime="2025-03-31 08:36",
            amount="623.00",
        )

    monkeypatch.setattr(app_module, "parse_railway_ticket_from_bytes", fake_parse)

    first = client.post(
        "/api/railway/upload-and-parse",
        data={"files": (BytesIO(b"%PDF-1.4 first"), "first.pdf")},
        content_type="multipart/form-data",
    ).get_json()[0]
    second = client.post(
        "/api/railway/upload-and-parse",
        data={"files": (BytesIO(b"%PDF-1.4 second"), "second.pdf")},
        content_type="multipart/form-data",
    ).get_json()[0]

    delete_response = client.delete(f"/api/railway/documents/{first['id']}")
    assert delete_response.status_code == 200
    assert first["id"] not in app_module.RAILWAY_DOCUMENT_STORE
    assert second["id"] in app_module.RAILWAY_DOCUMENT_STORE

    clear_response = client.delete("/api/railway/documents")
    assert clear_response.status_code == 200
    assert app_module.RAILWAY_DOCUMENT_STORE == {}


def test_general_invoice_flow(client, monkeypatch):
    def fake_parse(file_name, file_bytes):
        return GeneralInvoiceFields(
            invoice_type="电子发票（普通发票）",
            invoice_number="25312000000002446025",
            issue_date="2025-01-03",
            buyer_name="广东工业大学",
            seller_name="上海淳大酒店投资管理有限公司",
            total_amount="813.64",
        )

    monkeypatch.setattr(app_module, "parse_general_invoice_from_bytes", fake_parse)

    upload_response = client.post(
        "/api/general-invoice/upload-and-parse",
        data={"files": (BytesIO(b"%PDF-1.4 fake"), "hotel.pdf")},
        content_type="multipart/form-data",
    )

    assert upload_response.status_code == 200
    document = upload_response.get_json()[0]
    assert document["fields"]["seller_name"] == "上海淳大酒店投资管理有限公司"

    preview_response = client.post(
        "/api/general-invoice/preview-rename",
        json={
            "documentIds": [document["id"]],
            "ruleConfig": {
                "mode": "template",
                "template": "{开票日期}_{销售方名称}_{价税合计}",
                "dateFormat": "YYYY-MM-DD",
            },
        },
    )
    assert preview_response.status_code == 200
    assert preview_response.get_json()[0]["conflictResolvedName"] == "2025-01-03_上海淳大酒店投资管理有限公司_813.64"


def test_airline_invoice_flow(client, monkeypatch):
    def fake_parse(file_name, file_bytes):
        return AirlineInvoiceFields(
            invoice_number="26112000001054174981",
            issue_date="2026-03-18",
            departure_airport="北京大兴",
            arrival_airport="广州",
            flight_number="JD5921",
            cabin_class="经济舱 Q舱",
            departure_time="2025-09-15",
            amount="807.34",
            total_amount="930.00",
            passenger_name="李志",
            passenger_id="430723******120037",
        )

    monkeypatch.setattr(app_module, "parse_airline_invoice_from_bytes", fake_parse)

    upload_response = client.post(
        "/api/airline/upload-and-parse",
        data={"files": (BytesIO(b"%PDF-1.4 fake"), "airline.pdf")},
        content_type="multipart/form-data",
    )
    assert upload_response.status_code == 200
    document = upload_response.get_json()[0]
    assert document["fields"]["flight_number"] == "JD5921"

    preview_response = client.post(
        "/api/airline/preview-rename",
        json={
            "documentIds": [document["id"]],
            "ruleConfig": {
                "mode": "template",
                "template": "{开票日期}_{起飞机场}_{着陆机场}_{航班号}_{价税合计}",
                "dateFormat": "YYYY-MM-DD",
            },
        },
    )
    assert preview_response.status_code == 200
    assert preview_response.get_json()[0]["conflictResolvedName"] == "2026-03-18_北京大兴_广州_JD5921_930.00"
