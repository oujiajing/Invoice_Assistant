const ledgerState = {
  entries: [],
  selectedIds: new Set(),
  activeEntryId: "",
  activeDetail: null,
  documentModalEntryId: "",
  detailCache: new Map(),
  filters: {
    invoiceTypes: [],
    expenseTypes: [],
    invoiceCategories: [],
  },
  reportFilters: {
    datePreset: "month",
    dateFrom: "",
    dateTo: "",
    sellerNames: "",
    payerNames: "",
  },
  viewMode: "list",
  reportData: null,
  chartInstances: new Map(),
  chartFilterKey: "",
};

const ledgerFileInput = document.getElementById("ledgerFileInput");
const ledgerPickFilesBtn = document.getElementById("ledgerPickFilesBtn");
const ledgerDownloadBtn = document.getElementById("ledgerDownloadBtn");
const ledgerDeleteBtn = document.getElementById("ledgerDeleteBtn");
const ledgerCountText = document.getElementById("ledgerCountText");
const ledgerStatusText = document.getElementById("ledgerStatusText");
const ledgerGroups = document.getElementById("ledgerGroups");
const ledgerListArea = document.querySelector(".ledger-list-area");
const ledgerListView = document.getElementById("ledgerListView");
const ledgerReportView = document.getElementById("ledgerReportView");
const selectAllCheckbox = document.getElementById("selectAllCheckbox");
const ledgerFilters = [...document.querySelectorAll(".ledger-filter")];
const ledgerFilterPanel = document.getElementById("ledgerFilterPanel");
const toggleFilterBtn = document.getElementById("toggleFilterBtn");
const ledgerDetailSection = document.getElementById("ledgerDetailSection");
const collapseLedgerDetailBtn = document.getElementById("collapseLedgerDetailBtn");
const ledgerDetailResizeHandle = document.getElementById("ledgerDetailResizeHandle");
const ledgerPreviewContainer = document.getElementById("ledgerPreviewContainer");
const ledgerPreviewOpenBtn = document.getElementById("ledgerPreviewOpenBtn");
const ledgerInfoList = document.getElementById("ledgerInfoList");
const ledgerExtendedList = document.getElementById("ledgerExtendedList");
const ledgerDetailDownloadLink = document.getElementById("ledgerDetailDownloadLink");
const ledgerDetailPrintBtn = document.getElementById("ledgerDetailPrintBtn");
const ledgerDocumentModal = document.getElementById("ledgerDocumentModal");
const ledgerDocumentViewer = document.getElementById("ledgerDocumentViewer");
const ledgerDocumentTitle = document.getElementById("ledgerDocumentTitle");
const ledgerDocumentDownloadLink = document.getElementById("ledgerDocumentDownloadLink");
const ledgerDocumentPrintBtn = document.getElementById("ledgerDocumentPrintBtn");
const ledgerDocumentCloseBtn = document.getElementById("ledgerDocumentCloseBtn");
const ledgerListViewBtn = document.getElementById("ledgerListViewBtn");
const ledgerReportViewBtn = document.getElementById("ledgerReportViewBtn");
const ledgerDatePresetButtons = [...document.querySelectorAll(".ledger-date-preset")];
const ledgerDateFromInput = document.getElementById("ledgerDateFromInput");
const ledgerDateToInput = document.getElementById("ledgerDateToInput");
const ledgerSellerFilterInput = document.getElementById("ledgerSellerFilterInput");
const ledgerPayerFilterInput = document.getElementById("ledgerPayerFilterInput");
const ledgerApplyReportFiltersBtn = document.getElementById("ledgerApplyReportFiltersBtn");
const ledgerExportStatsBtn = document.getElementById("ledgerExportStatsBtn");
const ledgerReportSummary = document.getElementById("ledgerReportSummary");
const ledgerReportTableBody = document.getElementById("ledgerReportTableBody");
const ledgerReportTableHint = document.getElementById("ledgerReportTableHint");

const chartNodes = {
  amountTrend: document.getElementById("ledgerAmountTrendChart"),
  countTrend: document.getElementById("ledgerCountTrendChart"),
  expenseType: document.getElementById("ledgerExpenseTypeChart"),
  invoiceType: document.getElementById("ledgerInvoiceTypeChart"),
  invoiceCategory: document.getElementById("ledgerInvoiceCategoryChart"),
  invoiceCategoryAmount: document.getElementById("ledgerInvoiceCategoryAmountChart"),
};

let detailResizeStartY = 0;
let detailResizeStartHeight = 0;

ledgerPickFilesBtn.addEventListener("click", () => ledgerFileInput.click());
ledgerFileInput.addEventListener("change", event => uploadLedgerFiles(event.target.files));
ledgerDownloadBtn.addEventListener("click", downloadSelectedLedgerEntries);
ledgerDeleteBtn.addEventListener("click", deleteSelectedLedgerEntries);
selectAllCheckbox.addEventListener("change", toggleSelectAllLedgerEntries);
toggleFilterBtn.addEventListener("click", toggleFilterPanel);
collapseLedgerDetailBtn.addEventListener("click", closeLedgerDetail);
ledgerPreviewOpenBtn.addEventListener("click", openDocumentModalForActiveEntry);
ledgerDetailPrintBtn.addEventListener("click", printActivePreview);
ledgerDocumentPrintBtn.addEventListener("click", printDocumentModal);
ledgerDocumentCloseBtn.addEventListener("click", closeDocumentModal);
ledgerDetailResizeHandle.addEventListener("mousedown", startDetailResize);
ledgerFilters.forEach(input => input.addEventListener("change", updateLedgerFilters));
ledgerListViewBtn.addEventListener("click", () => switchLedgerView("list"));
ledgerReportViewBtn.addEventListener("click", () => switchLedgerView("report"));
ledgerDatePresetButtons.forEach(button => button.addEventListener("click", () => applyDatePreset(button.dataset.datePreset)));
ledgerApplyReportFiltersBtn.addEventListener("click", applyReportFilters);
window.addEventListener("resize", resizeLedgerCharts);
ledgerDocumentModal.addEventListener("click", event => {
  if (event.target.dataset.ledgerDocumentClose !== undefined) {
    closeDocumentModal();
  }
});

function buildLedgerQuery(includeReportFilters = false) {
  const search = new URLSearchParams();
  if (ledgerState.filters.invoiceTypes.length) {
    search.set("invoice_types", ledgerState.filters.invoiceTypes.join(","));
  }
  if (ledgerState.filters.expenseTypes.length) {
    search.set("expense_types", ledgerState.filters.expenseTypes.join(","));
  }
  if (ledgerState.filters.invoiceCategories.length) {
    search.set("invoice_categories", ledgerState.filters.invoiceCategories.join(","));
  }
  if (includeReportFilters) {
    if (ledgerState.reportFilters.dateFrom) {
      search.set("date_from", ledgerState.reportFilters.dateFrom);
    }
    if (ledgerState.reportFilters.dateTo) {
      search.set("date_to", ledgerState.reportFilters.dateTo);
    }
    const sellerNames = splitTextValues(ledgerState.reportFilters.sellerNames);
    if (sellerNames.length) {
      search.set("seller_names", sellerNames.join(","));
    }
    const payerNames = splitTextValues(ledgerState.reportFilters.payerNames);
    if (payerNames.length) {
      search.set("payer_names", payerNames.join(","));
    }
  }
  return search;
}

async function loadLedgerEntries() {
  const response = await fetch(`/api/ledger/list?${buildLedgerQuery(false).toString()}`);
  if (!response.ok) {
    ledgerStatusText.textContent = "台账加载失败，请稍后重试。";
    return;
  }

  ledgerState.entries = await response.json();
  const validIds = new Set(ledgerState.entries.map(item => item.id));
  ledgerState.selectedIds = new Set([...ledgerState.selectedIds].filter(id => validIds.has(id)));
  if (ledgerState.activeEntryId && !validIds.has(ledgerState.activeEntryId)) {
    closeLedgerDetail();
  }
  if (ledgerState.documentModalEntryId && !validIds.has(ledgerState.documentModalEntryId)) {
    closeDocumentModal();
  }
  renderLedgerGroups();
  renderLedgerToolbar();
}

async function loadLedgerReport() {
  const query = buildLedgerQuery(true).toString();
  const [summaryResponse, chartsResponse, tableResponse] = await Promise.all([
    fetch(`/api/ledger/stats/summary?${query}`),
    fetch(`/api/ledger/stats/charts?${query}`),
    fetch(`/api/ledger/stats/table?${query}`),
  ]);
  if (!summaryResponse.ok || !chartsResponse.ok || !tableResponse.ok) {
    ledgerReportSummary.innerHTML = '<article class="panel ledger-summary-card"><strong>报表加载失败</strong><span>请稍后重试</span></article>';
    return;
  }
  const summary = await summaryResponse.json();
  const chartsPayload = await chartsResponse.json();
  const tablePayload = await tableResponse.json();
  ledgerState.reportData = {
    summary,
    charts: chartsPayload.charts,
    filterOptions: chartsPayload.filterOptions,
    table: tablePayload.table,
  };
  renderLedgerReport();
}

async function uploadLedgerFiles(fileList) {
  const files = [...fileList].filter(file => /\.(pdf|ofd|jpg|jpeg|png)$/i.test(file.name));
  if (!files.length) {
    window.alert("请选择 PDF、OFD 或 JPG/JPEG/PNG 格式的发票文件。");
    return;
  }

  const formData = new FormData();
  files.forEach(file => formData.append("files", file));
  ledgerStatusText.textContent = "正在上传并识别发票，请稍候...";

  const response = await fetch("/api/ledger/upload-and-parse", { method: "POST", body: formData });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "上传失败，请稍后重试。" }));
    ledgerStatusText.textContent = error.message || "上传失败，请稍后重试。";
    return;
  }

  const payload = await response.json();
  const failedText = payload.failed.length ? `，其中 ${payload.failed.length} 张未识别成功` : "";
  ledgerStatusText.textContent = `已新增 ${payload.created.length} 张发票${failedText}。`;
  if (payload.failed.length) {
    window.alert(`以下文件未识别成功：\n${payload.failed.map(item => `${item.originalName}：${item.error}`).join("\n")}`);
  }
  ledgerFileInput.value = "";
  await refreshLedgerData();
}

function updateLedgerFilters() {
  ledgerState.filters.invoiceTypes = ledgerFilters
    .filter(input => input.dataset.filterGroup === "invoiceType" && input.checked)
    .map(input => input.value);
  ledgerState.filters.expenseTypes = ledgerFilters
    .filter(input => input.dataset.filterGroup === "expenseType" && input.checked)
    .map(input => input.value);
  ledgerState.filters.invoiceCategories = ledgerFilters
    .filter(input => input.dataset.filterGroup === "invoiceCategory" && input.checked)
    .map(input => input.value);
  refreshLedgerData();
}

function renderLedgerGroups() {
  if (!ledgerState.entries.length) {
    ledgerGroups.innerHTML = "";
    ledgerStatusText.textContent = "上传高铁票、机票、住宿发票后，这里会显示台账卡片。";
    return;
  }

  ledgerStatusText.textContent = `当前共 ${ledgerState.entries.length} 张发票。`;
  const groups = groupEntriesByMonth(ledgerState.entries);
  ledgerGroups.innerHTML = groups
    .map(
      group => `
        <section class="ledger-group">
          <div class="ledger-group-header">
            <h3>${escapeHtml(group.label)}</h3>
            <span>${group.items.length} 张发票</span>
          </div>
          <div class="ledger-card-grid">
            ${group.items.map(renderLedgerCard).join("")}
          </div>
        </section>
      `,
    )
    .join("");

  ledgerGroups.querySelectorAll("[data-ledger-select]").forEach(input => {
    input.addEventListener("change", event => {
      const entryId = event.currentTarget.dataset.ledgerSelect;
      if (event.currentTarget.checked) {
        ledgerState.selectedIds.add(entryId);
      } else {
        ledgerState.selectedIds.delete(entryId);
      }
      renderLedgerToolbar();
    });
  });

  ledgerGroups.querySelectorAll("[data-ledger-card]").forEach(card => {
    card.addEventListener("click", event => {
      if (event.target.closest('input[type="checkbox"]')) return;
      openLedgerDetail(card.dataset.ledgerCard);
    });
  });
}

function renderLedgerCard(item) {
  return `
    <article class="ledger-card ${ledgerState.activeEntryId === item.id ? "ledger-card-active" : ""}" data-ledger-card="${item.id}">
      <div class="ledger-card-head">
        <label class="ledger-card-check">
          <input type="checkbox" data-ledger-select="${item.id}" ${ledgerState.selectedIds.has(item.id) ? "checked" : ""} />
        </label>
        <div class="ledger-card-title-wrap">
          <h4>${escapeHtml(item.title)}</h4>
        </div>
        <span class="ledger-tag">${escapeHtml(item.expenseType)}</span>
      </div>
      <div class="ledger-amount">¥ ${escapeHtml(item.amount || "0.00")}</div>
      <div class="ledger-meta">
        <div><span>时间</span><strong>${escapeHtml(formatChineseDate(item.issueDate))}</strong></div>
        <div><span>付款方</span><strong>${escapeHtml(item.payerName || "-")}</strong></div>
        <div><span>项目</span><strong title="${escapeHtml(item.itemSummary || "-")}">${escapeHtml(item.itemSummary || "-")}</strong></div>
      </div>
    </article>
  `;
}

function renderLedgerToolbar() {
  const countLabel = ledgerState.viewMode === "report" ? `统计范围 · ${ledgerState.entries.length}` : `发票 · ${ledgerState.entries.length}`;
  ledgerCountText.textContent = countLabel;
  ledgerDownloadBtn.disabled = ledgerState.selectedIds.size === 0 || ledgerState.viewMode !== "list";
  ledgerDeleteBtn.disabled = ledgerState.selectedIds.size === 0 || ledgerState.viewMode !== "list";
  selectAllCheckbox.checked = ledgerState.entries.length > 0 && ledgerState.selectedIds.size === ledgerState.entries.length;
  selectAllCheckbox.disabled = ledgerState.viewMode !== "list";
}

function toggleSelectAllLedgerEntries() {
  if (selectAllCheckbox.checked) {
    ledgerState.selectedIds = new Set(ledgerState.entries.map(item => item.id));
  } else {
    ledgerState.selectedIds.clear();
  }
  renderLedgerGroups();
  renderLedgerToolbar();
}

function groupEntriesByMonth(entries) {
  const groups = new Map();
  const now = new Date();
  const currentKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  entries.forEach(item => {
    const key = item.issueDate ? item.issueDate.slice(0, 7) : "unknown";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  });

  return [...groups.entries()]
    .sort((a, b) => (a[0] < b[0] ? 1 : -1))
    .map(([key, items]) => ({
      label: key === currentKey ? "本月" : key === "unknown" ? "未识别日期" : `${Number(key.slice(0, 4))}年${Number(key.slice(5, 7))}月`,
      items,
    }));
}

async function openLedgerDetail(entryId) {
  if (ledgerState.viewMode !== "list") return;
  const detail = await fetchLedgerDetail(entryId);
  if (!detail) return;
  ledgerState.activeEntryId = entryId;
  ledgerState.activeDetail = detail;
  ledgerDetailDownloadLink.href = detail.downloadUrl;
  ledgerInfoList.innerHTML = detail.infoItems.map(renderInfoItem).join("");
  ledgerExtendedList.innerHTML = detail.extendedItems.map(renderInfoItem).join("");
  renderInlineDetailPreview();
  ledgerDetailSection.classList.remove("hidden");
  ledgerListArea.classList.add("ledger-list-area-detail-open");
  renderLedgerGroups();
  renderLedgerToolbar();
}

function renderInlineDetailPreview() {
  const detail = ledgerState.activeDetail;
  if (!detail) {
    ledgerPreviewContainer.innerHTML = "";
    return;
  }
  ledgerPreviewContainer.innerHTML = renderPreviewEmbed(detail, "detail");
}

function renderInfoItem(item) {
  return `
    <div class="ledger-info-item">
      <span>${escapeHtml(item.label)}</span>
      <strong>${escapeHtml(item.value || "-")}</strong>
    </div>
  `;
}

function closeLedgerDetail() {
  ledgerState.activeEntryId = "";
  ledgerState.activeDetail = null;
  ledgerDetailSection.classList.add("hidden");
  ledgerListArea.classList.remove("ledger-list-area-detail-open");
  renderLedgerGroups();
  renderLedgerToolbar();
}

function openDocumentModalForActiveEntry() {
  if (!ledgerState.activeDetail) return;
  const detail = ledgerState.activeDetail;
  ledgerState.documentModalEntryId = detail.id;
  ledgerDocumentTitle.textContent = detail.originalName || "发票原票预览";
  ledgerDocumentDownloadLink.href = detail.downloadUrl;
  ledgerDocumentViewer.innerHTML = renderPreviewEmbed(detail, "modal");
  ledgerDocumentModal.classList.remove("hidden");
}

function closeDocumentModal() {
  ledgerState.documentModalEntryId = "";
  ledgerDocumentModal.classList.add("hidden");
  ledgerDocumentViewer.innerHTML = "";
}

function printActivePreview() {
  if (!ledgerState.activeDetail) return;
  printDetailFile(ledgerState.activeDetail);
}

function printDocumentModal() {
  if (!ledgerState.documentModalEntryId) return;
  const detail = ledgerState.detailCache.get(ledgerState.documentModalEntryId);
  if (!detail) return;
  printDetailFile(detail);
}

function printDetailFile(detail) {
  if (detail.fileType.toLowerCase() === "pdf") {
    window.open(detail.previewUrl, "_blank", "noopener");
    return;
  }
  window.open(detail.downloadUrl, "_blank", "noopener");
}

function downloadSelectedLedgerEntries() {
  if (!ledgerState.selectedIds.size) return;
  window.location.href = `/api/ledger/download?ids=${[...ledgerState.selectedIds].join(",")}`;
}

async function deleteSelectedLedgerEntries() {
  if (!ledgerState.selectedIds.size) return;
  const deletingIds = [...ledgerState.selectedIds];
  const response = await fetch("/api/ledger", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids: deletingIds }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "删除失败，请稍后重试。" }));
    window.alert(error.message || "删除失败");
    return;
  }
  if (deletingIds.includes(ledgerState.activeEntryId)) {
    closeLedgerDetail();
  }
  if (deletingIds.includes(ledgerState.documentModalEntryId)) {
    closeDocumentModal();
  }
  deletingIds.forEach(id => ledgerState.detailCache.delete(id));
  ledgerState.selectedIds.clear();
  await refreshLedgerData();
}

function toggleFilterPanel() {
  ledgerFilterPanel.classList.toggle("collapsed");
  toggleFilterBtn.textContent = ledgerFilterPanel.classList.contains("collapsed") ? "展开" : "收起";
}

async function fetchLedgerDetail(entryId) {
  if (ledgerState.detailCache.has(entryId)) {
    return ledgerState.detailCache.get(entryId);
  }

  const response = await fetch(`/api/ledger/${entryId}`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "加载详情失败。" }));
    window.alert(error.message || "加载详情失败");
    return null;
  }

  const detail = await response.json();
  ledgerState.detailCache.set(entryId, detail);
  return detail;
}

function renderPreviewEmbed(detail, variant) {
  if (detail.fileType.toLowerCase() === "pdf") {
    const frameClass = variant === "modal" ? "ledger-document-frame" : "ledger-preview-frame";
    return `<iframe class="${frameClass}" src="${buildPdfPreviewUrl(detail.previewUrl, variant)}" title="发票预览"></iframe>`;
  }

  const wrapperClass = variant === "modal" ? "ledger-document-placeholder" : "ledger-preview-placeholder";
  return `
    <div class="${wrapperClass}">
      <p>当前文件为 OFD，浏览器可能无法直接内嵌显示。</p>
      <a class="primary-btn" href="${detail.downloadUrl}">下载查看</a>
    </div>
  `;
}

function buildPdfPreviewUrl(previewUrl, variant) {
  const zoom = "page-fit";
  return `${previewUrl}#zoom=${zoom}&view=Fit`;
}

function startDetailResize(event) {
  if (ledgerDetailSection.classList.contains("hidden")) return;
  event.preventDefault();
  detailResizeStartY = event.clientY;
  detailResizeStartHeight = ledgerDetailSection.getBoundingClientRect().height;
  window.addEventListener("mousemove", resizeDetailPanel);
  window.addEventListener("mouseup", stopDetailResize);
}

function resizeDetailPanel(event) {
  const deltaY = detailResizeStartY - event.clientY;
  const nextHeight = Math.max(320, Math.min(window.innerHeight - 80, detailResizeStartHeight + deltaY));
  document.documentElement.style.setProperty("--ledger-detail-height", `${nextHeight}px`);
}

function stopDetailResize() {
  window.removeEventListener("mousemove", resizeDetailPanel);
  window.removeEventListener("mouseup", stopDetailResize);
}

function switchLedgerView(viewMode) {
  ledgerState.viewMode = viewMode;
  ledgerListView.classList.toggle("hidden", viewMode !== "list");
  ledgerReportView.classList.toggle("hidden", viewMode !== "report");
  ledgerListViewBtn.classList.toggle("ledger-view-tab-active", viewMode === "list");
  ledgerReportViewBtn.classList.toggle("ledger-view-tab-active", viewMode === "report");
  if (viewMode !== "list") {
    closeLedgerDetail();
  }
  renderLedgerToolbar();
  if (viewMode === "report") {
    loadLedgerReport();
  }
}

function applyDatePreset(preset) {
  ledgerState.reportFilters.datePreset = preset;
  ledgerDatePresetButtons.forEach(button => button.classList.toggle("active", button.dataset.datePreset === preset));
  const now = new Date();
  if (preset === "month") {
    ledgerState.reportFilters.dateFrom = formatDateInputValue(new Date(now.getFullYear(), now.getMonth(), 1));
    ledgerState.reportFilters.dateTo = formatDateInputValue(new Date(now.getFullYear(), now.getMonth() + 1, 0));
  } else if (preset === "quarter") {
    ledgerState.reportFilters.dateFrom = formatDateInputValue(new Date(now.getFullYear(), now.getMonth() - 2, 1));
    ledgerState.reportFilters.dateTo = formatDateInputValue(new Date(now.getFullYear(), now.getMonth() + 1, 0));
  } else if (preset === "year") {
    ledgerState.reportFilters.dateFrom = formatDateInputValue(new Date(now.getFullYear(), 0, 1));
    ledgerState.reportFilters.dateTo = formatDateInputValue(new Date(now.getFullYear(), 11, 31));
  }
  syncReportInputs();
  refreshLedgerData();
}

function applyReportFilters() {
  ledgerState.reportFilters.dateFrom = ledgerDateFromInput.value;
  ledgerState.reportFilters.dateTo = ledgerDateToInput.value;
  ledgerState.reportFilters.sellerNames = ledgerSellerFilterInput.value.trim();
  ledgerState.reportFilters.payerNames = ledgerPayerFilterInput.value.trim();
  ledgerState.reportFilters.datePreset = "custom";
  ledgerDatePresetButtons.forEach(button => button.classList.toggle("active", button.dataset.datePreset === "custom"));
  refreshLedgerData();
}

function syncReportInputs() {
  ledgerDateFromInput.value = ledgerState.reportFilters.dateFrom;
  ledgerDateToInput.value = ledgerState.reportFilters.dateTo;
  ledgerSellerFilterInput.value = ledgerState.reportFilters.sellerNames;
  ledgerPayerFilterInput.value = ledgerState.reportFilters.payerNames;
}

async function refreshLedgerData() {
  await loadLedgerEntries();
  if (ledgerState.viewMode === "report") {
    await loadLedgerReport();
  }
  ledgerExportStatsBtn.href = `/api/ledger/stats/export?${buildLedgerQuery(true).toString()}`;
}

function renderLedgerReport() {
  const reportData = ledgerState.reportData;
  if (!reportData) return;
  renderSummaryCards(reportData.summary);
  renderReportTable(reportData.table);
  renderReportCharts(reportData.charts);
}

function renderSummaryCards(summary) {
  ledgerReportSummary.innerHTML = `
    <article class="panel ledger-summary-card"><span>发票总数</span><strong>${summary.invoiceCount}</strong></article>
    <article class="panel ledger-summary-card"><span>去重后发票数</span><strong>${summary.uniqueInvoiceCount}</strong></article>
    <article class="panel ledger-summary-card"><span>总金额</span><strong>¥ ${summary.totalAmount}</strong></article>
    <article class="panel ledger-summary-card"><span>平均票面金额</span><strong>¥ ${summary.averageAmount}</strong></article>
    <article class="panel ledger-summary-card ledger-summary-card-warn"><span>重复发票数</span><strong>${summary.duplicateCount}</strong></article>
  `;
}

function renderReportTable(rows) {
  if (!rows.length) {
    ledgerReportTableHint.textContent = "当前没有重复发票。";
    ledgerReportTableBody.innerHTML = '<tr class="empty-row"><td colspan="9">当前筛选范围内未检测到重复发票。</td></tr>';
    return;
  }
  ledgerReportTableHint.textContent = `当前检测到 ${rows.length} 条重复发票记录。`;
  const filteredRows = ledgerState.chartFilterKey ? rows.filter(row => row.duplicateStatus === ledgerState.chartFilterKey) : rows;
  ledgerReportTableBody.innerHTML = filteredRows
    .map(
      row => `
        <tr class="stats-row-duplicate">
          <td>${escapeHtml(row.invoiceCategory)}</td>
          <td title="${escapeHtml(row.originalName)}">${escapeHtml(row.originalName)}</td>
          <td>${escapeHtml(row.invoiceNumber || "-")}</td>
          <td>${escapeHtml(formatChineseDate(row.issueDate))}</td>
          <td>${escapeHtml(row.amount || "-")}</td>
          <td>${escapeHtml(row.sellerName || "-")}</td>
          <td>${escapeHtml(row.payerName || "-")}</td>
          <td><span class="stats-status stats-status-duplicate">${escapeHtml(row.duplicateStatus)}</span></td>
          <td>${escapeHtml(row.duplicateGroup || "-")}</td>
        </tr>
      `,
    )
    .join("");
}

function renderReportCharts(charts) {
  if (typeof echarts === "undefined") return;
  renderChart("amountTrend", {
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: charts.amountTrend.labels },
    yAxis: { type: "value" },
    series: [{ type: "line", smooth: true, data: charts.amountTrend.series, itemStyle: { color: "#2d6cdf" } }],
  });
  renderChart("countTrend", {
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: charts.countTrend.labels },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: charts.countTrend.series, itemStyle: { color: "#6b9df5" } }],
  });
  renderChart("expenseType", createPieOption(charts.expenseType, "费用类型"));
  renderChart("invoiceType", createPieOption(charts.invoiceType, "发票类型"));
  renderChart("invoiceCategory", {
    tooltip: { trigger: "axis" },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: charts.invoiceCategory.labels },
    series: [{ type: "bar", data: charts.invoiceCategory.series, itemStyle: { color: "#3f8cff" } }],
  });
  renderChart("invoiceCategoryAmount", {
    tooltip: { trigger: "axis" },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: charts.invoiceCategoryAmount.labels },
    series: [{ type: "bar", data: charts.invoiceCategoryAmount.series, itemStyle: { color: "#4a72dd" } }],
  });
}

function createPieOption(chartData, name) {
  return {
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [
      {
        name,
        type: "pie",
        radius: ["45%", "68%"],
        data: chartData.labels.map((label, index) => ({ name: label, value: chartData.series[index] })),
      },
    ],
  };
}

function renderChart(key, option) {
  const node = chartNodes[key];
  if (!node) return;
  let chart = ledgerState.chartInstances.get(key);
  if (!chart) {
    chart = echarts.init(node);
    ledgerState.chartInstances.set(key, chart);
    if (key === "expenseType" || key === "invoiceType") {
      chart.on("click", params => {
        ledgerState.chartFilterKey = "";
        renderReportTable(ledgerState.reportData?.table || []);
      });
    }
  }
  chart.setOption(option, true);
}

function resizeLedgerCharts() {
  ledgerState.chartInstances.forEach(chart => chart.resize());
}

function splitTextValues(value) {
  return String(value || "")
    .split(/[，,]/)
    .map(item => item.trim())
    .filter(Boolean);
}

function formatChineseDate(value) {
  if (!value) return "-";
  if (!value.includes("-")) return value;
  const [year, month, day] = value.split("-");
  return `${Number(year)}年${Number(month)}月${Number(day)}日`;
}

function formatDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

applyDatePreset("month");
syncReportInputs();
refreshLedgerData();
