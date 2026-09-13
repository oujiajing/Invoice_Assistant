from __future__ import annotations

import json
import os
import threading
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class OCRResult:
    text: str
    source: str = "ocr"
    confidence: float | None = None


class OCRProvider(Protocol):
    def recognize_image(self, image_bytes: bytes, file_name: str) -> OCRResult:
        ...


class PaddleOCRProvider:
    """Lazy PP-OCRv5 mobile provider; optional imports stay inside this module."""

    def __init__(self):
        self._pipeline = _get_ocr_pipeline()

    def recognize_image(self, image_bytes: bytes, file_name: str) -> OCRResult:
        if not image_bytes:
            raise ValueError("OCR_FAILED: 图片内容为空。")
        suffix = Path(file_name).suffix or ".png"
        with tempfile.TemporaryDirectory(prefix="invoice-ocr-") as temp_dir:
            image_path = Path(temp_dir) / f"input{suffix}"
            image_path.write_bytes(image_bytes)
            try:
                results = self._pipeline.predict(str(image_path))
                text = "\n".join(
                    page_text for page_text in (_result_to_text(result) for result in results) if page_text
                )
            except Exception as exc:
                raise RuntimeError(f"OCR_FAILED: 图片 OCR 识别失败：{exc}") from exc
        if not text.strip():
            raise ValueError("OCR_FAILED: OCR 未识别到文字。")
        return OCRResult(text=text.strip())


_OCR_PIPELINE = None
_OCR_PROVIDER: OCRProvider | None = None
_OCR_LOCK = threading.RLock()


def _get_ocr_pipeline():
    global _OCR_PIPELINE
    if _OCR_PIPELINE is None:
        with _OCR_LOCK:
            if _OCR_PIPELINE is None:
                try:
                    # PaddlePaddle 3.3 + Windows/Python 3.13 can fail in the
                    # oneDNN executor for PP-OCRv5 mobile models. The plain
                    # CPU executor is slower but avoids that runtime failure.
                    os.environ.setdefault("FLAGS_use_mkldnn", "0")
                    from paddleocr import PaddleOCR
                except ImportError as exc:
                    raise RuntimeError(
                        "OCR_NOT_INSTALLED: OCR 功能未安装，请先执行 pip install -r requirements-ocr.txt。"
                    ) from exc
                try:
                    _OCR_PIPELINE = PaddleOCR(
                        text_detection_model_name="PP-OCRv5_mobile_det",
                        text_recognition_model_name="PP-OCRv5_mobile_rec",
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False,
                        enable_mkldnn=False,
                        device="cpu",
                    )
                except Exception as exc:
                    raise RuntimeError(f"OCR_INIT_FAILED: OCR 模型初始化失败：{exc}") from exc
    return _OCR_PIPELINE


def get_ocr_provider() -> OCRProvider:
    global _OCR_PROVIDER
    if _OCR_PROVIDER is None:
        with _OCR_LOCK:
            if _OCR_PROVIDER is None:
                _OCR_PROVIDER = PaddleOCRProvider()
    return _OCR_PROVIDER


def _result_to_text(result) -> str:
    payload = getattr(result, "json", None)
    if callable(payload):
        payload = payload()
    if payload is None and isinstance(result, dict):
        payload = result
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = None
    if isinstance(payload, dict):
        if isinstance(payload.get("res"), dict):
            payload = payload["res"]
        texts = payload.get("rec_texts") or payload.get("texts")
        if isinstance(texts, list):
            return "\n".join(str(text).strip() for text in texts if str(text).strip())

    # Compatibility with the older list-style PaddleOCR result format.
    lines: list[str] = []
    if isinstance(result, list):
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                value = item[1]
                if isinstance(value, (list, tuple)):
                    value = value[0] if value else ""
                if value:
                    lines.append(str(value).strip())
    return "\n".join(line for line in lines if line)


def recognize_image_bytes(image_bytes: bytes, suffix: str = ".png") -> str:
    return get_ocr_provider().recognize_image(image_bytes, suffix).text


def recognize_pdf_bytes(pdf_bytes: bytes) -> str:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("OCR_NOT_INSTALLED: 扫描 PDF OCR 需要安装 requirements-ocr.txt。") from exc
    if not pdf_bytes:
        raise ValueError("PDF 内容为空。")

    page_texts: list[str] = []
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise RuntimeError(f"PDF_RENDER_FAILED: PDF 打开失败，无法进行 OCR：{exc}") from exc
    try:
        if document.page_count > 50:
            raise ValueError("PDF 页数超过 OCR 单文件限制（50 页）。")
        for index in range(document.page_count):
            page = document.load_page(index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_texts.append(recognize_image_bytes(pixmap.tobytes("png")))
    except Exception as exc:
        if isinstance(exc, (ValueError, RuntimeError)):
            raise
        raise RuntimeError(f"PDF_RENDER_FAILED: PDF 页面转换失败：{exc}") from exc
    finally:
        document.close()
    text = "\n".join(page_texts).strip()
    if not text:
        raise ValueError("OCR 未识别到 PDF 文字。")
    return text
