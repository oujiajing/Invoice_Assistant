from __future__ import annotations

import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

from .ocr_service import recognize_image_bytes, recognize_pdf_bytes


@dataclass(slots=True)
class DocumentText:
    text: str
    source: str


def extract_native_pdf_text(file_bytes: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_native_ofd_text(file_bytes: bytes) -> str:
    texts: list[str] = []
    with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
        xml_names = sorted(name for name in archive.namelist() if name.lower().endswith(".xml"))
        for name in xml_names:
            try:
                root = ElementTree.fromstring(archive.read(name))
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


def native_text_is_usable(text: str) -> bool:
    return len("".join((text or "").split())) >= 20


def extract_document_text(file_name: str, file_bytes: bytes, validator=None) -> DocumentText:
    extension = Path(file_name).suffix.lower()
    if extension in {".jpg", ".jpeg", ".png"}:
        return DocumentText(recognize_image_bytes(file_bytes, extension), "ocr")
    if extension == ".pdf":
        try:
            native_text = extract_native_pdf_text(file_bytes)
        except Exception:
            native_text = ""
        if native_text_is_usable(native_text):
            # A valid native text layer is authoritative. A parser mismatch is
            # an unsupported/invalid invoice, not a reason to OCR an electronic PDF.
            return DocumentText(native_text, "native")
        return DocumentText(recognize_pdf_bytes(file_bytes), "ocr")
    if extension == ".ofd":
        native_text = extract_native_ofd_text(file_bytes)
        if not native_text_is_usable(native_text):
            raise ValueError("OFD 原生文本为空或过少，暂不对 OFD 执行 OCR。")
        if validator is not None:
            validator(native_text)
        return DocumentText(native_text, "native")
    raise ValueError("仅支持 PDF、OFD、JPG、JPEG 或 PNG 格式。")
