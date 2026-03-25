from __future__ import annotations

import base64
import io
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont
from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from werkzeug.utils import secure_filename

from .ledger import detect_invoice_for_ledger

A4_WIDTH = 595.28
A4_HEIGHT = 841.89
PAGE_MARGIN = 18
DOUBLE_GAP = 16
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyh.ttf",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


@dataclass(slots=True)
class MergePrintItem:
    item_id: str
    original_name: str
    stored_name: str
    stored_path: str
    file_type: str
    invoice_count: int
    page_count: int
    amount: str
    status: str
    invoice_label: str
    rendered_pdf_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = payload.pop("item_id")
        payload["originalName"] = payload.pop("original_name")
        payload["storedName"] = payload.pop("stored_name")
        payload["storedPath"] = payload.pop("stored_path")
        payload["renderedPdfPath"] = payload.pop("rendered_pdf_path")
        payload["fileType"] = payload.pop("file_type")
        payload["invoiceCount"] = payload.pop("invoice_count")
        payload["pageCount"] = payload.pop("page_count")
        payload["invoiceLabel"] = payload.pop("invoice_label")
        return payload


@dataclass(slots=True)
class MergePrintTask:
    task_id: str
    input_type: str = ""
    items: list[MergePrintItem] = field(default_factory=list)
    latest_build_id: str = ""
    latest_build_path: str = ""
    latest_page_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "inputType": self.input_type,
            "items": [item.to_dict() for item in self.items],
            "latestBuildId": self.latest_build_id,
            "latestPageCount": self.latest_page_count,
        }


def ensure_merge_print_task(task_store: dict[str, MergePrintTask], task_id: str | None = None) -> MergePrintTask:
    if task_id and task_id in task_store:
        return task_store[task_id]
    task = MergePrintTask(task_id=str(uuid.uuid4()))
    task_store[task.task_id] = task
    return task


def add_files_to_merge_task(
    *,
    task_store: dict[str, MergePrintTask],
    task_id: str | None,
    files,
    upload_dir: Path,
) -> MergePrintTask:
    task = ensure_merge_print_task(task_store, task_id)
    for file_storage in files:
        original_name = file_storage.filename or "未命名文件"
        file_type = _normalize_input_type(Path(original_name).suffix.lower())
        if task.input_type and task.input_type != file_type:
            raise ValueError("同一次合并任务不能同时上传 PDF 和 OFD 文件。")

        task.input_type = task.input_type or file_type
        item_id = str(uuid.uuid4())
        stored_name = secure_filename(f"{item_id}{Path(original_name).suffix.lower()}")
        stored_path = upload_dir / stored_name
        file_bytes = file_storage.read()
        stored_path.write_bytes(file_bytes)
        rendered_pdf_path = ""
        rendered_pdf_bytes: bytes | None = None
        if file_type == "ofd":
            rendered_pdf_bytes = convert_ofd_to_pdf_bytes(file_bytes)
            rendered_pdf_path = str(upload_dir / f"{item_id}.rendered.pdf")
            Path(rendered_pdf_path).write_bytes(rendered_pdf_bytes)
        summary = summarize_merge_item(original_name, file_type, file_bytes, rendered_pdf_bytes)
        task.items.append(
            MergePrintItem(
                item_id=item_id,
                original_name=original_name,
                stored_name=stored_name,
                stored_path=str(stored_path),
                rendered_pdf_path=rendered_pdf_path,
                file_type=file_type,
                invoice_count=summary["invoice_count"],
                page_count=summary["page_count"],
                amount=summary["amount"],
                status=summary["status"],
                invoice_label=summary["invoice_label"],
            )
        )
    return task


def summarize_merge_item(
    file_name: str,
    file_type: str,
    file_bytes: bytes,
    rendered_pdf_bytes: bytes | None = None,
) -> dict[str, Any]:
    amount = ""
    invoice_label = "可合并"
    status = "可合并"
    try:
        category, fields, _raw_text = detect_invoice_for_ledger(file_name, file_bytes)
        invoice_label = {
            "railway": "铁路电子客票",
            "airline": "航空电子客票",
            "general": fields.get("invoice_type") or "常规数电发票",
        }.get(category, "可合并")
        amount = fields.get("total_amount") or fields.get("amount") or ""
    except Exception:
        status = "未识别金额"

    page_count = _count_pdf_pages(rendered_pdf_bytes) if rendered_pdf_bytes else _count_pdf_pages(file_bytes)
    return {
        "invoice_count": 1,
        "page_count": page_count,
        "amount": amount,
        "status": status,
        "invoice_label": invoice_label,
    }


def delete_merge_item(task_store: dict[str, MergePrintTask], task_id: str, item_id: str) -> MergePrintTask:
    task = _get_task(task_store, task_id)
    remaining: list[MergePrintItem] = []
    removed: MergePrintItem | None = None
    for item in task.items:
        if item.item_id == item_id:
            removed = item
            continue
        remaining.append(item)
    if removed is None:
        raise ValueError("未找到要删除的文件。")
    _safe_unlink(Path(removed.stored_path))
    if removed.rendered_pdf_path:
        _safe_unlink(Path(removed.rendered_pdf_path))
    task.items = remaining
    if not task.items:
        task.input_type = ""
    return task


def clear_merge_task(task_store: dict[str, MergePrintTask], task_id: str) -> None:
    task = _get_task(task_store, task_id)
    for item in task.items:
        _safe_unlink(Path(item.stored_path))
        if item.rendered_pdf_path:
            _safe_unlink(Path(item.rendered_pdf_path))
    if task.latest_build_path:
        _safe_unlink(Path(task.latest_build_path))
    del task_store[task_id]


def build_merge_print_pdf(
    *,
    task_store: dict[str, MergePrintTask],
    task_id: str,
    ordered_item_ids: list[str],
    layout_mode: str,
    show_divider: bool,
    list_placement: str,
    output_dir: Path,
) -> dict[str, Any]:
    task = _get_task(task_store, task_id)
    items = _ordered_items(task, ordered_item_ids)
    if not items:
      raise ValueError("请先上传要合并的发票文件。")

    page_sources = []
    for item in items:
        file_path = Path(item.stored_path)
        file_bytes = file_path.read_bytes()
        if item.file_type == "pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
        else:
            rendered_path = Path(item.rendered_pdf_path) if item.rendered_pdf_path else None
            rendered_bytes = rendered_path.read_bytes() if rendered_path and rendered_path.exists() else convert_ofd_to_pdf_bytes(file_bytes)
            reader = PdfReader(io.BytesIO(rendered_bytes))
        for page in reader.pages:
            page_sources.append((page, item.original_name))

    writer = PdfWriter()
    if layout_mode == "single":
        for source_page, _source_name in page_sources:
            writer.add_page(source_page)
    else:
        for index in range(0, len(page_sources), 2):
            first_page = page_sources[index][0]
            second_page = page_sources[index + 1][0] if index + 1 < len(page_sources) else None
            if second_page is None:
                writer.add_page(first_page)
            else:
                writer.add_page(_compose_double_page(first_page, second_page, show_divider))

    if list_placement in {"prepend", "append"}:
        list_pdf = PdfReader(io.BytesIO(build_summary_list_pdf(items)))
        list_pages = list(list_pdf.pages)
        if list_placement == "prepend":
            combined = PdfWriter()
            for page in list_pages:
                combined.add_page(page)
            for page in writer.pages:
                combined.add_page(page)
            writer = combined
        else:
            for page in list_pages:
                writer.add_page(page)

    output_dir.mkdir(parents=True, exist_ok=True)
    build_id = str(uuid.uuid4())
    build_path = output_dir / f"{build_id}.pdf"
    with build_path.open("wb") as fp:
        writer.write(fp)

    if task.latest_build_path:
        _safe_unlink(Path(task.latest_build_path))
    task.latest_build_id = build_id
    task.latest_build_path = str(build_path)
    task.latest_page_count = len(writer.pages)
    return {
        "taskId": task.task_id,
        "buildId": build_id,
        "pageCount": len(writer.pages),
        "previewPath": build_path,
    }


def build_merge_list_workbook(task_store: dict[str, MergePrintTask], task_id: str, ordered_item_ids: list[str]) -> Workbook:
    task = _get_task(task_store, task_id)
    items = _ordered_items(task, ordered_item_ids)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "发票清单"
    worksheet.append(["序号", "文件名", "格式", "发票数量", "页数", "金额", "状态", "发票类型"])
    for index, item in enumerate(items, start=1):
        worksheet.append(
            [
                index,
                item.original_name,
                item.file_type.upper(),
                item.invoice_count,
                item.page_count,
                item.amount,
                item.status,
                item.invoice_label,
            ]
        )
    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 36)
    return workbook


def build_summary_list_pdf(items: list[MergePrintItem]) -> bytes:
    image = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(image)
    title_font = _load_font(32)
    body_font = _load_font(22)
    draw.text((80, 80), "发票合并打印清单", fill="#15335c", font=title_font)

    y = 150
    for index, item in enumerate(items, start=1):
        line = f"{index}. {item.original_name}  |  页数 {item.page_count}  |  金额 {item.amount or '-'}  |  {item.status}"
        for wrapped in _wrap_text(line, body_font, 1080):
            draw.text((80, y), wrapped, fill="#23354d", font=body_font)
            y += 34
            if y > 1660:
                break
        if y > 1660:
            break

    pdf_buffer = io.BytesIO()
    image.save(pdf_buffer, format="PDF", resolution=150.0)
    return pdf_buffer.getvalue()


def _compose_double_page(first_page, second_page, show_divider: bool) -> PageObject:
    first_width = float(first_page.mediabox.width)
    first_height = float(first_page.mediabox.height)
    second_width = float(second_page.mediabox.width) if second_page is not None else 0.0
    second_height = float(second_page.mediabox.height) if second_page is not None else 0.0
    target_width = max(first_width, second_width)
    target_height = first_height + second_height + (DOUBLE_GAP if second_page is not None else 0.0)
    target = PageObject.create_blank_page(width=target_width, height=target_height)

    _place_page(target, first_page, (target_width - first_width) / 2, second_height + (DOUBLE_GAP if second_page is not None else 0.0))
    if second_page is not None:
        _place_page(target, second_page, (target_width - second_width) / 2, 0)
    return target


def _place_page(target_page: PageObject, source_page, x: float, y: float) -> None:
    source_left = float(source_page.mediabox.left)
    source_bottom = float(source_page.mediabox.bottom)
    scale = 1.0
    offset_x = x - source_left * scale
    offset_y = y - source_bottom * scale
    target_page.merge_transformed_page(
        source_page,
        Transformation().scale(scale).translate(offset_x, offset_y),
    )


def _ordered_items(task: MergePrintTask, ordered_item_ids: list[str]) -> list[MergePrintItem]:
    item_map = {item.item_id: item for item in task.items}
    ordered = [item_map[item_id] for item_id in ordered_item_ids if item_id in item_map]
    if len(ordered) != len(task.items):
        remaining = [item for item in task.items if item.item_id not in ordered_item_ids]
        ordered.extend(remaining)
    return ordered


def _count_pdf_pages(file_bytes: bytes) -> int:
    try:
        return len(PdfReader(io.BytesIO(file_bytes)).pages)
    except Exception:
        return 1


def _normalize_input_type(extension: str) -> str:
    if extension == ".pdf":
        return "pdf"
    if extension == ".ofd":
        return "ofd"
    raise ValueError("当前仅支持 PDF 或 OFD 格式。")


def _get_task(task_store: dict[str, MergePrintTask], task_id: str) -> MergePrintTask:
    task = task_store.get(task_id)
    if task is None:
        raise ValueError("未找到对应的合并任务，请重新上传文件。")
    return task


def _safe_unlink(path: Path) -> None:
    if path.exists():
        path.unlink()


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    image = Image.new("RGB", (10, 10), "white")
    draw = ImageDraw.Draw(image)
    lines: list[str] = []
    current = ""
    for char in text.replace("\r", ""):
        if char == "\n":
            if current:
                lines.append(current)
                current = ""
            continue
        trial = current + char
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def convert_ofd_to_pdf_bytes(file_bytes: bytes) -> bytes:
    try:
        from ofdparser import OfdParser
    except ModuleNotFoundError as exc:
        raise ValueError(
            "当前环境缺少 OFD 转换依赖，请先安装 merge-print 所需依赖：pip install ofdparser reportlab xmltodict fonttools"
        ) from exc

    parser = OfdParser(base64.b64encode(file_bytes).decode("ascii"))
    return parser.ofd2pdf()
