from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


@dataclass(slots=True)
class StatsDedupItem:
    item_id: str
    original_name: str
    stored_path: str
    file_type: str
    parse_status: str = "pending"
    invoice_category: str = ""
    invoice_number: str = ""
    issue_date: str = ""
    amount: str = ""
    tax_amount: str = ""
    total_amount: str = ""
    dedup_status: str = "待统计"
    duplicate_group_key: str = ""
    error: str = ""
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.item_id,
            "originalName": self.original_name,
            "fileType": self.file_type,
            "parseStatus": self.parse_status,
            "invoiceCategory": self.invoice_category,
            "invoiceNumber": self.invoice_number,
            "issueDate": self.issue_date,
            "amount": self.amount,
            "taxAmount": self.tax_amount,
            "totalAmount": self.total_amount,
            "dedupStatus": self.dedup_status,
            "duplicateGroupKey": self.duplicate_group_key,
            "error": self.error,
            "fields": self.fields,
        }


@dataclass(slots=True)
class StatsDedupTask:
    task_id: str
    items: list[StatsDedupItem] = field(default_factory=list)
    latest_export_id: str = ""
    latest_export_path: str = ""
    latest_export_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "taskId": self.task_id,
            "items": [item.to_dict() for item in self.items],
        }


def add_files_to_stats_task(
    *,
    task_store: dict[str, StatsDedupTask],
    task_id: str | None,
    files: list[FileStorage],
    upload_dir: Path,
) -> StatsDedupTask:
    task = task_store.get(task_id) if task_id else None
    if task is None:
        task = StatsDedupTask(task_id=task_id or str(uuid.uuid4()))
        task_store[task.task_id] = task

    for file_storage in files:
        original_name = file_storage.filename or "未命名文件.pdf"
        suffix = Path(original_name).suffix.lower()
        if suffix != ".pdf":
            raise ValueError("当前模块仅支持 PDF 发票。")
        item_id = str(uuid.uuid4())
        stored_name = secure_filename(f"{item_id}{suffix}")
        stored_path = upload_dir / stored_name
        stored_path.write_bytes(file_storage.read())
        task.items.append(
            StatsDedupItem(
                item_id=item_id,
                original_name=original_name,
                stored_path=str(stored_path),
                file_type="pdf",
            )
        )
    return task


def delete_stats_item(task_store: dict[str, StatsDedupTask], task_id: str, item_id: str) -> StatsDedupTask:
    task = task_store.get(task_id)
    if task is None:
        raise ValueError("未找到统计任务。")
    remaining: list[StatsDedupItem] = []
    deleted = False
    for item in task.items:
        if item.item_id == item_id:
            deleted = True
            path = Path(item.stored_path)
            if path.exists():
                path.unlink()
            continue
        remaining.append(item)
    if not deleted:
        raise ValueError("未找到要删除的文件。")
    task.items = remaining
    return task


def clear_stats_task(task_store: dict[str, StatsDedupTask], task_id: str) -> None:
    task = task_store.pop(task_id, None)
    if task is None:
        return
    for item in task.items:
        path = Path(item.stored_path)
        if path.exists():
            path.unlink()
    if task.latest_export_path:
        export_path = Path(task.latest_export_path)
        if export_path.exists():
            export_path.unlink()


def build_stats_workbook(task: StatsDedupTask) -> Workbook:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "发票统计报表"
    worksheet.append(
        [
            "序号",
            "文件名称",
            "票种",
            "发票号码",
            "开票日期",
            "金额",
            "税额",
            "价税合计",
            "是否重复",
            "重复组",
            "统计状态",
            "错误信息",
        ]
    )
    for index, item in enumerate(task.items, start=1):
        worksheet.append(
            [
                index,
                item.original_name,
                item.invoice_category,
                item.invoice_number,
                item.issue_date,
                item.amount,
                item.tax_amount,
                item.total_amount,
                "是" if item.dedup_status == "重复发票" else "否",
                item.duplicate_group_key,
                item.dedup_status,
                item.error,
            ]
        )

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 34)
    return workbook


def workbook_to_bytes(workbook: Workbook) -> io.BytesIO:
    memory_file = io.BytesIO()
    workbook.save(memory_file)
    memory_file.seek(0)
    return memory_file
