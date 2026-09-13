# Progress log

## 2026-09-13

- Read the complete task specification from the pasted attachment.
- Initialized file-based planning for the multi-file implementation.
- Audited the existing working-tree OCR attempt and found base requirements incorrectly included OCR dependencies and native PDF parser mismatch incorrectly triggered OCR.
- Added `requirements-ocr.txt`, lazy `OCRProvider`/`PaddleOCRProvider`, unified image/native-PDF/scanned-PDF extraction, source metadata, stats/ledger image routing, and explicit OCR/PDF error prefixes.
- Added focused image, fallback, parser-reuse, source, and batch-isolation tests; updated README and upload UI copy.
- Verification: `python -m pytest -q` => 37 passed; Python compileall and `git diff --check` passed; importing `app` does not import PaddleOCR/PaddlePaddle.
- Real-image validation against `C:\Users\ojj\Desktop\发票图片`: installed optional OCR dependencies, disabled incompatible oneDNN CPU execution for the observed Windows/Python 3.13 runtime error, then verified all 15 images: OCR 15/15 and existing invoice Parser 15/15.
