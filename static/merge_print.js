const mergeState = {
  taskId: "",
  inputType: "",
  items: [],
  layoutMode: "double",
  showDivider: true,
  listPlacement: "append",
  zoomMode: "page-fit",
  buildId: "",
  previewUrl: "",
  downloadUrl: "",
};

const mergeIntro = document.getElementById("mergeIntro");
const mergeWorkspace = document.getElementById("mergeWorkspace");
const mergeFileInput = document.getElementById("mergeFileInput");
const mergePickFilesBtn = document.getElementById("mergePickFilesBtn");
const mergePickMoreBtn = document.getElementById("mergePickMoreBtn");
const mergeDropzone = document.getElementById("mergeDropzone");
const mergeSideDropzone = document.getElementById("mergeSideDropzone");
const mergeList = document.getElementById("mergeList");
const mergeClearBtn = document.getElementById("mergeClearBtn");
const mergePageCountText = document.getElementById("mergePageCountText");
const mergeFileCountBadge = document.getElementById("mergeFileCountBadge");
const mergeInvoiceCountText = document.getElementById("mergeInvoiceCountText");
const mergeAmountText = document.getElementById("mergeAmountText");
const mergePreviewFrame = document.getElementById("mergePreviewFrame");
const mergeDownloadBtn = document.getElementById("mergeDownloadBtn");
const mergePrintBtn = document.getElementById("mergePrintBtn");
const mergeFitBtn = document.getElementById("mergeFitBtn");
const mergeZoomOutBtn = document.getElementById("mergeZoomOutBtn");
const mergeZoomInBtn = document.getElementById("mergeZoomInBtn");
const mergeZoomLabelBtn = document.getElementById("mergeZoomLabelBtn");
const mergeExportListBtn = document.getElementById("mergeExportListBtn");
const layoutInputs = [...document.querySelectorAll(".merge-layout-mode")];
const listPlacementInputs = [...document.querySelectorAll(".merge-list-placement")];
const mergeDividerCheckbox = document.getElementById("mergeDividerCheckbox");

mergePickFilesBtn.addEventListener("click", () => mergeFileInput.click());
mergePickMoreBtn.addEventListener("click", () => mergeFileInput.click());
mergeFileInput.addEventListener("change", event => uploadMergeFiles(event.target.files));
mergeClearBtn.addEventListener("click", clearMergeTask);
mergePrintBtn.addEventListener("click", printMergedPdf);
mergeFitBtn.addEventListener("click", () => {
  mergeState.zoomMode = "page-fit";
  refreshPreviewSrc();
});
mergeZoomOutBtn.addEventListener("click", () => shiftZoom(-10));
mergeZoomInBtn.addEventListener("click", () => shiftZoom(10));
mergeExportListBtn.addEventListener("click", exportMergeList);
layoutInputs.forEach(input => input.addEventListener("change", handleLayoutChange));
listPlacementInputs.forEach(input => input.addEventListener("change", handleListPlacementChange));
mergeDividerCheckbox.addEventListener("change", async () => {
  mergeState.showDivider = mergeDividerCheckbox.checked;
  await rebuildMergePreview();
});

setupDropzone(mergeDropzone);
setupDropzone(mergeSideDropzone);

function setupDropzone(element) {
  element.addEventListener("dragover", event => {
    event.preventDefault();
    element.classList.add("dragover");
  });
  element.addEventListener("dragleave", () => element.classList.remove("dragover"));
  element.addEventListener("drop", event => {
    event.preventDefault();
    element.classList.remove("dragover");
    uploadMergeFiles(event.dataTransfer.files);
  });
}

async function uploadMergeFiles(fileList) {
  const files = [...fileList].filter(file => /\.(pdf|ofd)$/i.test(file.name));
  if (!files.length) {
    window.alert("当前仅支持 PDF 或 OFD 文件。");
    return;
  }

  const formData = new FormData();
  if (mergeState.taskId) {
    formData.append("taskId", mergeState.taskId);
  }
  files.forEach(file => formData.append("files", file));

  const response = await fetch("/api/merge-print/upload", { method: "POST", body: formData });
  const payload = await response.json().catch(() => ({ message: "上传失败，请稍后重试。" }));
  if (!response.ok) {
    window.alert(payload.message || "上传失败，请稍后重试。");
    return;
  }

  mergeState.taskId = payload.taskId;
  mergeState.inputType = payload.inputType;
  mergeState.items = payload.items;
  mergeFileInput.value = "";
  syncWorkspaceVisibility();
  renderMergeList();
  await rebuildMergePreview();
}

function syncWorkspaceVisibility() {
  const hasItems = mergeState.items.length > 0;
  mergeIntro.classList.toggle("hidden", hasItems);
  mergeWorkspace.classList.toggle("hidden", !hasItems);
}

function renderMergeList() {
  mergeFileCountBadge.textContent = String(mergeState.items.length);
  if (!mergeState.items.length) {
    mergeList.innerHTML = '<div class="empty-builder">上传 PDF / OFD 文件后，这里会显示清单。</div>';
    return;
  }

  mergeList.innerHTML = mergeState.items
    .map(
      item => `
        <article class="merge-file-item" draggable="true" data-merge-item="${item.id}">
          <div class="merge-file-handle">⋮⋮</div>
          <div class="merge-file-meta">
            <strong title="${escapeHtml(item.originalName)}">${escapeHtml(item.originalName)}</strong>
            <span>发票数: ${item.invoiceCount} | 金额: ¥${escapeHtml(item.amount || "0.00")}</span>
          </div>
          <span class="merge-file-status">${escapeHtml(item.status)}</span>
          <button class="icon-btn merge-file-delete" data-merge-delete="${item.id}">×</button>
        </article>
      `,
    )
    .join("");

  let draggingId = "";
  mergeList.querySelectorAll("[data-merge-item]").forEach(itemNode => {
    itemNode.addEventListener("dragstart", () => {
      draggingId = itemNode.dataset.mergeItem;
      itemNode.classList.add("dragging");
    });
    itemNode.addEventListener("dragend", () => itemNode.classList.remove("dragging"));
    itemNode.addEventListener("dragover", event => event.preventDefault());
    itemNode.addEventListener("drop", async event => {
      event.preventDefault();
      const targetId = itemNode.dataset.mergeItem;
      if (!draggingId || draggingId === targetId) return;
      reorderItems(draggingId, targetId);
      renderMergeList();
      await rebuildMergePreview();
    });
  });

  mergeList.querySelectorAll("[data-merge-delete]").forEach(button => {
    button.addEventListener("click", async event => {
      event.stopPropagation();
      await deleteMergeItem(button.dataset.mergeDelete);
    });
  });
}

function reorderItems(draggingId, targetId) {
  const sourceIndex = mergeState.items.findIndex(item => item.id === draggingId);
  const targetIndex = mergeState.items.findIndex(item => item.id === targetId);
  if (sourceIndex < 0 || targetIndex < 0) return;
  const [moved] = mergeState.items.splice(sourceIndex, 1);
  mergeState.items.splice(targetIndex, 0, moved);
}

async function deleteMergeItem(itemId) {
  const response = await fetch(`/api/merge-print/items/${mergeState.taskId}/${itemId}`, { method: "DELETE" });
  const payload = await response.json().catch(() => ({ message: "删除失败。" }));
  if (!response.ok) {
    window.alert(payload.message || "删除失败。");
    return;
  }
  mergeState.items = payload.items;
  mergeState.inputType = payload.inputType;
  if (!mergeState.items.length) {
    mergeState.taskId = "";
    mergeState.previewUrl = "";
    mergeState.downloadUrl = "";
    mergeState.buildId = "";
    syncWorkspaceVisibility();
    renderMergeList();
    resetPreview();
    return;
  }
  renderMergeList();
  await rebuildMergePreview();
}

async function clearMergeTask() {
  if (!mergeState.taskId) return;
  await fetch(`/api/merge-print/task/${mergeState.taskId}`, { method: "DELETE" });
  mergeState.taskId = "";
  mergeState.inputType = "";
  mergeState.items = [];
  mergeState.previewUrl = "";
  mergeState.downloadUrl = "";
  mergeState.buildId = "";
  syncWorkspaceVisibility();
  renderMergeList();
  resetPreview();
}

function resetPreview() {
  mergePageCountText.textContent = "共 0 页";
  mergePreviewFrame.src = "about:blank";
  mergeDownloadBtn.classList.add("disabled-link");
  mergeDownloadBtn.removeAttribute("href");
  mergeInvoiceCountText.textContent = "0 张";
  mergeAmountText.textContent = "¥0.00";
  mergeZoomLabelBtn.textContent = "适应";
}

function handleLayoutChange(event) {
  mergeState.layoutMode = event.target.value;
  rebuildMergePreview();
}

function handleListPlacementChange(event) {
  mergeState.listPlacement = event.target.value;
  rebuildMergePreview();
}

async function rebuildMergePreview() {
  if (!mergeState.taskId || !mergeState.items.length) return;
  const response = await fetch("/api/merge-print/build", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      taskId: mergeState.taskId,
      itemIds: mergeState.items.map(item => item.id),
      layoutMode: mergeState.layoutMode,
      showDivider: mergeState.showDivider,
      listPlacement: mergeState.listPlacement,
    }),
  });
  const payload = await response.json().catch(() => ({ message: "生成预览失败。" }));
  if (!response.ok) {
    window.alert(payload.message || "生成预览失败。");
    return;
  }

  mergeState.previewUrl = payload.previewUrl;
  mergeState.downloadUrl = payload.downloadUrl;
  mergeState.buildId = payload.buildId;
  mergePageCountText.textContent = `共 ${payload.pageCount} 页`;
  mergeInvoiceCountText.textContent = `${payload.stats.invoiceCount} 张`;
  mergeAmountText.textContent = `¥${payload.stats.totalAmount}`;
  mergeDownloadBtn.href = payload.downloadUrl;
  mergeDownloadBtn.classList.remove("disabled-link");
  refreshPreviewSrc();
}

function refreshPreviewSrc() {
  if (!mergeState.previewUrl) return;
  mergePreviewFrame.src = `${mergeState.previewUrl}#zoom=${mergeState.zoomMode}&pagemode=none`;
  mergeZoomLabelBtn.textContent = mergeState.zoomMode === "page-fit" ? "适应" : `${mergeState.zoomMode}%`;
}

function shiftZoom(delta) {
  const current = mergeState.zoomMode === "page-fit" ? 100 : Number(mergeState.zoomMode);
  const next = Math.max(50, Math.min(160, current + delta));
  mergeState.zoomMode = String(next);
  refreshPreviewSrc();
}

function printMergedPdf() {
  if (!mergeState.previewUrl) return;
  window.open(mergeState.previewUrl, "_blank", "noopener");
}

async function exportMergeList() {
  if (!mergeState.taskId) return;
  const response = await fetch("/api/merge-print/export-list", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      taskId: mergeState.taskId,
      itemIds: mergeState.items.map(item => item.id),
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ message: "下载清单失败。" }));
    window.alert(payload.message || "下载清单失败。");
    return;
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "发票合并打印清单.xlsx";
  anchor.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

syncWorkspaceVisibility();
renderMergeList();
