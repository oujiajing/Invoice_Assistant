from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class RailwayTicketFields:
    invoice_number: str = ""
    issue_date: str = ""
    departure_station: str = ""
    arrival_station: str = ""
    departure_datetime: str = ""
    train_number: str = ""
    seat_number: str = ""
    amount: str = ""
    passenger_name: str = ""
    passenger_id: str = ""
    custom_content: str = ""
    ticket_label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RailwayDocument:
    document_id: str
    original_name: str
    stored_name: str
    stored_path: str
    file_type: str
    parse_status: str
    fields: RailwayTicketFields = field(default_factory=RailwayTicketFields)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = payload.pop("document_id")
        payload["originalName"] = payload.pop("original_name")
        payload["storedName"] = payload.pop("stored_name")
        payload["storedPath"] = payload.pop("stored_path")
        payload["fileType"] = payload.pop("file_type")
        payload["parseStatus"] = payload.pop("parse_status")
        return payload


@dataclass(slots=True)
class GeneralInvoiceFields:
    invoice_type: str = ""
    invoice_code: str = ""
    invoice_number: str = ""
    issue_date: str = ""
    buyer_name: str = ""
    buyer_tax_number: str = ""
    seller_name: str = ""
    seller_tax_number: str = ""
    amount: str = ""
    tax_amount: str = ""
    total_amount: str = ""
    total_amount_upper: str = ""
    remarks: str = ""
    payee: str = ""
    reviewer: str = ""
    issuer: str = ""
    custom_content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GeneralInvoiceDocument:
    document_id: str
    original_name: str
    stored_name: str
    stored_path: str
    file_type: str
    parse_status: str
    fields: GeneralInvoiceFields = field(default_factory=GeneralInvoiceFields)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = payload.pop("document_id")
        payload["originalName"] = payload.pop("original_name")
        payload["storedName"] = payload.pop("stored_name")
        payload["storedPath"] = payload.pop("stored_path")
        payload["fileType"] = payload.pop("file_type")
        payload["parseStatus"] = payload.pop("parse_status")
        return payload


@dataclass(slots=True)
class AirlineInvoiceFields:
    invoice_number: str = ""
    issue_date: str = ""
    departure_airport: str = ""
    arrival_airport: str = ""
    flight_number: str = ""
    cabin_class: str = ""
    departure_time: str = ""
    amount: str = ""
    total_amount: str = ""
    passenger_name: str = ""
    passenger_id: str = ""
    custom_content: str = ""
    invoice_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AirlineInvoiceDocument:
    document_id: str
    original_name: str
    stored_name: str
    stored_path: str
    file_type: str
    parse_status: str
    fields: AirlineInvoiceFields = field(default_factory=AirlineInvoiceFields)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = payload.pop("document_id")
        payload["originalName"] = payload.pop("original_name")
        payload["storedName"] = payload.pop("stored_name")
        payload["storedPath"] = payload.pop("stored_path")
        payload["fileType"] = payload.pop("file_type")
        payload["parseStatus"] = payload.pop("parse_status")
        return payload


@dataclass(slots=True)
class RenameRuleToken:
    type: str
    value: str


@dataclass(slots=True)
class RenameRuleConfig:
    mode: str = "tokens"
    tokens: list[RenameRuleToken] = field(default_factory=list)
    template: str = "{开票日期}_{出发站}_{到达站}_{票价}"
    separator: str = "_"
    date_format: str = "YYYY年MM月DD日"
    amount_format: str = "0.00"
    sanitize: bool = True
    duplicate_strategy: str = "suffix"

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "RenameRuleConfig":
        payload = payload or {}
        tokens = [
            RenameRuleToken(type=item.get("type", "field"), value=item.get("value", ""))
            for item in payload.get("tokens", [])
        ]
        return cls(
            mode=payload.get("mode", "tokens"),
            tokens=tokens,
            template=payload.get("template", "{开票日期}_{出发站}_{到达站}_{票价}"),
            separator=payload.get("separator", "_"),
            date_format=payload.get("dateFormat", "YYYY年MM月DD日"),
            amount_format=payload.get("amountFormat", "0.00"),
            sanitize=payload.get("sanitize", True),
            duplicate_strategy=payload.get("duplicateStrategy", "suffix"),
        )


def normalize_amount(value: str) -> str:
    if not value:
        return ""
    try:
        return f"{Decimal(value):.2f}"
    except Exception:
        return value
