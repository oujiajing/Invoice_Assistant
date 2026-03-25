const statsState = {
  taskId: "",
  items: [],
  phase: "upload",
  excelDownloadUrl: "",
  summary: {
    analyzedCount: 0,
    successCount: 0,
    duplicateCount: 0,
    failedCount: 0,
    totalAmount: "0.00",
  },
};

const statsFileInput = document.getElementById("statsFileInput");
const statsDropzone = document.getElementById("statsDropzone");
const statsPickFilesBtn = document.getElementById("statsPickFilesBtn");
const statsUploadPanel = document.getElementById("statsUploadPanel");
const statsWorkspace = document.getElementById("statsWorkspace");
const statsDonePanel = document.getElementById("statsDonePanel");
const statsListBody = document.getElementById("statsListBody");
const statsTableFooter = document.getElementById("statsTableFooter");
const statsSummaryText = document.getElementById("statsSummaryText");
const statsTotalAmountText = document.getElementById("statsTotalAmountText");
const statsAnalyzeBtn = document.getElementById("statsAnalyzeBtn");
const statsExportBtn = document.getElementById("statsExportBtn");
const statsAddFilesBtn = document.getElementById("statsAddFilesBtn");
const statsClearBtn = document.getElementById("statsClearBtn");
const statsBackBtn = document.getElementById("statsBackBtn");
const statsDownloadLink = document.getElementById("statsDownloadLink");
const statsDoneDescription = document.getElementById("statsDoneDescription");
const statsDoneFilename = document.getElementById("statsDoneFilename");
const statsStepUpload = document.getElementById("statsStepUpload");
const statsStepAnalyze = document.getElementById("statsStepAnalyze");
const statsStepDone = document.getElementById("statsStepDone");

statsPickFilesBtn.addEventListener("click", () => statsFileInput.click());
statsAddFilesBtn.addEventListener("click", () => statsFileInput.click());
statsFileInput.addEventListener("change", event => uploadStatsFiles(event.target.files));
statsAnalyzeBtn.addEventListener("click", analyzeStatsTask);
statsExportBtn.addEventListener("click", exportStatsWorkbook);
statsClearBtn.addEventListener("click", clearStatsTask);
statsBackBtn.addEventListener("click", () => {
  statsState.phase = "result";
  syncStatsPhase();
});

["dragover", "dragenter"].forEach(eventName => {
  statsDropzone.addEventListener(eventName, event => {
    event.preventDefault();
    statsDropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach(eventName => {
  statsDropzone.addEventListener(eventName, event => {
    event.preventDefault();
    statsDropzone.classList.remove("dragover");
  });
});
statsDropzone.addEventListener("drop", event => uploadStatsFiles(event.dataTransfer.files));

function syncStatsPhase() {
  statsUploadPanel.classList.toggle("hidden", statsState.phase !== "upload");
  statsWorkspace.classList.toggle("hidden", statsState.phase === "done" || (!statsState.items.length && statsState.phase === "upload"));
  statsDonePanel.classList.toggle("hidden", statsState.phase !== "done");

  statsStepUpload.classList.toggle("active", statsState.phase === "upload");
  statsStepAnalyze.classList.toggle("active", statsState.phase === "result");
  statsStepDone.classList.toggle("active", statsState.phase === "done");
}

async function uploadStatsFiles(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  const invalid = files.find(file => !/\.pdf$/i.test(file.name));
  if (invalid) {
    window.alert("当前模块仅支持 PDF 发票。");
    return;
  }
  const formData = new FormData();
  if (statsState.taskId) {
    formData.append("taskId", statsState.taskId);
  }
  files.forEach(file => formData.append("files", file));

  const response = await fetch("/api/stats-dedup/upload", { method: "POST", body: formData });
  const payload = await response.json().catch(() => ({ message: "上传失败，请稍后重试。" }));
  if (!response.ok) {
    window.alert(payload.message || "上传失败，请稍后重试。");
    return;
  }

  statsState.taskId = payload.taskId;
  statsState.items = payload.items;
  statsState.phase = "result";
  statsFileInput.value = "";
  statsState.excelDownloadUrl = "";
  renderStatsList();
  syncStatsPhase();
}

function renderStatsList() {
  statsAnalyzeBtn.disabled = !statsState.items.length;
  statsClearBtn.disabled = !statsState.items.length;
  statsExportBtn.disabled = !statsState.items.some(item => item.parseStatus === "success");
  statsTableFooter.classList.toggle("hidden", !statsState.items.length || !statsState.items.some(item => item.dedupStatus !== "待统计"));

  if (!statsState.items.length) {
    statsListBody.innerHTML = '<tr class="empty-row"><td colspan="9">上传 PDF 发票后，这里会显示待统计文件列表。</td></tr>';
    return;
  }

  statsListBody.innerHTML = statsState.items
    .map((item, index) => {
      const statusClass =
        item.dedupStatus === "重复发票"
          ? "stats-status-duplicate"
          : item.dedupStatus === "解析失败"
            ? "stats-status-failed"
            : item.dedupStatus === "统计完成"
              ? "stats-status-success"
              : "stats-status-pending";
      const rowClass = item.dedupStatus === "重复发票" ? "stats-row-duplicate" : "";
      return `
        <tr class="${rowClass}">
          <td>${index + 1}</td>
          <td title="${escapeHtml(item.originalName)}">${escapeHtml(item.originalName)}</td>
          <td>${escapeHtml(item.invoiceNumber || "-")}</td>
          <td>${escapeHtml(item.issueDate || "-")}</td>
          <td>${escapeHtml(item.amount || "-")}</td>
          <td>${escapeHtml(item.taxAmount || "-")}</td>
          <td>${escapeHtml(item.totalAmount || "-")}</td>
          <td><span class="stats-status ${statusClass}">${escapeHtml(item.dedupStatus || "待统计")}</span></td>
          <td><button class="icon-btn stats-delete-btn" data-stats-delete="${item.id}">×</button></td>
        </tr>
      `;
    })
    .join("");

  statsSummaryText.textContent = `共统计 ${statsState.summary.analyzedCount} 张发票，检测到 ${statsState.summary.duplicateCount} 张重复发票。`;
  statsTotalAmountText.textContent = `去重后合计金额： ${statsState.summary.totalAmount}`;

  statsListBody.querySelectorAll("[data-stats-delete]").forEach(button => {
    button.addEventListener("click", () => deleteStatsItem(button.dataset.statsDelete));
  });
}

async function analyzeStatsTask() {
  if (!statsState.taskId) return;
  const response = await fetch("/api/stats-dedup/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ taskId: statsState.taskId }),
  });
  const payload = await response.json().catch(() => ({ message: "统计失败，请稍后重试。" }));
  if (!response.ok) {
    window.alert(payload.message || "统计失败，请稍后重试。");
    return;
  }
  statsState.items = payload.items;
  statsState.summary = payload.summary;
  statsState.phase = "result";
  renderStatsList();
  syncStatsPhase();
}

async function exportStatsWorkbook() {
  if (!statsState.taskId) return;
  const response = await fetch("/api/stats-dedup/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ taskId: statsState.taskId }),
  });
  const payload = await response.json().catch(() => ({ message: "生成 Excel 失败，请稍后重试。" }));
  if (!response.ok) {
    window.alert(payload.message || "生成 Excel 失败，请稍后重试。");
    return;
  }
  statsState.excelDownloadUrl = payload.downloadUrl;
  statsDownloadLink.href = payload.downloadUrl;
  statsDownloadLink.classList.remove("disabled-link");
  statsDoneDescription.textContent = `本次共统计了 ${statsState.items.length} 张发票文件！`;
  statsDoneFilename.textContent = payload.fileName;
  statsState.phase = "done";
  syncStatsPhase();
}

async function deleteStatsItem(itemId) {
  if (!statsState.taskId) return;
  const response = await fetch(`/api/stats-dedup/items/${statsState.taskId}/${itemId}`, { method: "DELETE" });
  const payload = await response.json().catch(() => ({ message: "删除失败，请稍后重试。" }));
  if (!response.ok) {
    window.alert(payload.message || "删除失败，请稍后重试。");
    return;
  }
  statsState.items = payload.items;
  if (!statsState.items.length) {
    statsState.phase = "upload";
    statsState.taskId = "";
    statsState.summary = { analyzedCount: 0, successCount: 0, duplicateCount: 0, failedCount: 0, totalAmount: "0.00" };
    statsState.excelDownloadUrl = "";
    statsDownloadLink.classList.add("disabled-link");
    statsDownloadLink.removeAttribute("href");
    renderStatsList();
    syncStatsPhase();
    return;
  }
  if (statsState.phase !== "upload") {
    await analyzeStatsTask();
    return;
  }
  renderStatsList();
  syncStatsPhase();
}

async function clearStatsTask() {
  if (!statsState.taskId) return;
  await fetch(`/api/stats-dedup/task/${statsState.taskId}`, { method: "DELETE" });
  statsState.taskId = "";
  statsState.items = [];
  statsState.phase = "upload";
  statsState.summary = { analyzedCount: 0, successCount: 0, duplicateCount: 0, failedCount: 0, totalAmount: "0.00" };
  statsState.excelDownloadUrl = "";
  statsDownloadLink.classList.add("disabled-link");
  statsDownloadLink.removeAttribute("href");
  renderStatsList();
  syncStatsPhase();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

syncStatsPhase();
renderStatsList();
