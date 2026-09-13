# Findings

## Initial

- User requires native PDF/OFD parsing to remain the default, optional lazy-loaded PP-OCRv5 for images and scanned PDFs, and reuse of existing invoice parsers/business flows.
- OCR dependencies must be isolated in `requirements-ocr.txt`; base startup must not import PaddleOCR eagerly.

## Current codebase

- `app.py` has three invoice upload/parse routes plus a ledger route. `SUPPORTED_PARSE_SUFFIXES` was already expanded to PDF/OFD/JPG/JPEG/PNG in the working tree.
- Each existing parser has a `*_from_bytes` entry point and now delegates extraction to `invoice_helper.document_text.extract_document_text`; business parsers still parse text and set `parse_source`/`raw_text`.
- `invoice_helper.ocr_service` already has lazy singleton loading and PDF rendering, but the working-tree implementation currently puts PaddleOCR/PaddlePaddle in `requirements.txt`, violating the optional-dependency requirement.
- `document_text` currently falls back to OCR when native PDF text is too short or fails validation. The user specifically says fallback should not be triggered merely by parser failure for an otherwise valid electronic PDF, so the validator-based fallback needs review.
- `tests/test_ocr_integration.py` exists in the working tree but does not yet cover all required routes, optional dependency behavior, or batch isolation.
