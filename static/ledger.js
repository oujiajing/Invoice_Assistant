const ledgerState = {
  entries: [],
  selectedIds: new Set(),
  activeEntryId: "",
  filters: {
    invoiceTypes: [],
    expenseTypes: [],
  },
};

const ledgerFileInput = document.getElementById("ledgerFileInput");
const ledgerPickFilesBtn = document.getElementById("ledgerPickFilesBtn");
const ledgerDownloadBtn = document.getElementById("ledgerDownloadBtn");
const ledgerDeleteBtn = document.getElementById("ledgerDeleteBtn");
const ledgerCountText = document.getElementById("ledgerCountText");
const ledgerStatusText = document.getElementById("ledgerStatusText");
const ledgerGroups = document.getElementById("ledgerGroups");
const selectAllCheckbox = document.getElementById("selectAllCheckbox");
const ledgerFilters = [...document.querySelectorAll(".ledger-filter")];
const ledgerFilterPanel = document.getElementById("ledgerFilterPanel");
const toggleFilterBtn = document.getElementById("toggleFilterBtn");
const ledgerDetailSection = document.getElementById("ledgerDetailSection");
const collapseLedgerDetailBtn = document.getElementById("collapseLedgerDetailBtn");
const ledgerPreviewContainer = document.getElementById("ledgerPreviewContainer");
const ledgerInfoList = document.getElementById("ledgerInfoList");
const ledgerExtendedList = document.getElementById("ledgerExtendedList");
const ledgerDetailDownloadLink = document.getElementById("ledgerDetailDownloadLink");

ledgerPickFilesBtn.addEventListener("click", () => ledgerFileInput.click());
ledgerFileInput.addEventListener("change", event => uploadLedgerFiles(event.target.files));
ledgerDownloadBtn.addEventListener("click", downloadSelectedLedgerEntries);
ledgerDeleteBtn.addEventListener("click", deleteSelectedLedgerEntries);
selectAllCheckbox.addEventListener("change", toggleSelectAllLedgerEntries);
toggleFilterBtn.addEventListener("click", toggleFilterPanel);
collapseLedgerDetailBtn.addEventListener("click", closeLedgerDetail);
ledgerFilters.forEach(input => input.addEventListener("change", updateLedgerFilters));

async function loadLedgerEntries() {
  const search = new URLSearchParams();
  if (ledgerState.filters.invoiceTypes.length) {
    search.set("invoice_types", ledgerState.filters.invoiceTypes.join(","));
  }
  if (ledgerState.filters.expenseTypes.length) {
    search.set("expense_types", ledgerState.filters.expenseTypes.join(","));
  }

  const response = await fetch(`/api/ledger/list?${search.toString()}`);
  if (!response.ok) {
    ledgerStatusText.textContent = "台账加载失败，请稍后重试。";
    return;
  }

  ledgerState.entries = await response.json();
  const validIds = new Set(ledgerState.entries.map(item => item.id));
  ledgerState.selectedIds = new Set([...ledgerState.selectedIds].filter(id => validIds.has(id)));
  if (ledgerState.activeEntryId && !validIds.has(ledgerState.activeEntryId)) {
    ledgerState.activeEntryId = "";
    closeLedgerDetail();
  }
  renderLedgerGroups();
  renderLedgerToolbar();
}

async function uploadLedgerFiles(fileList) {
  const files = [...fileList].filter(file => /\.(pdf|ofd)$/i.test(file.name));
  if (!files.length) {
    window.alert("请选择 PDF 或 OFD 格式的发票文件。");
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
  const failedText = payload.failed.length
    ? `，其中 ${payload.failed.length} 张未识别成功`
    : "";
  ledgerStatusText.textContent = `已新增 ${payload.created.length} 张发票${failedText}。`;
  if (payload.failed.length) {
    window.alert(`以下文件未识别成功：\n${payload.failed.map(item => `${item.originalName}：${item.error}`).join("\n")}`);
  }
  ledgerFileInput.value = "";
  await loadLedgerEntries();
}

function updateLedgerFilters() {
  ledgerState.filters.invoiceTypes = ledgerFilters
    .filter(input => input.dataset.filterGroup === "invoiceType" && input.checked)
    .map(input => input.value);
  ledgerState.filters.expenseTypes = ledgerFilters
    .filter(input => input.dataset.filterGroup === "expenseType" && input.checked)
    .map(input => input.value);
  loadLedgerEntries();
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
  ledgerCountText.textContent = `发票 · ${ledgerState.entries.length}`;
  ledgerDownloadBtn.disabled = ledgerState.selectedIds.size === 0;
  ledgerDeleteBtn.disabled = ledgerState.selectedIds.size === 0;
  selectAllCheckbox.checked = ledgerState.entries.length > 0 && ledgerState.selectedIds.size === ledgerState.entries.length;
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
  const response = await fetch(`/api/ledger/${entryId}`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "加载详情失败。" }));
    window.alert(error.message || "加载详情失败");
    return;
  }

  const detail = await response.json();
  ledgerState.activeEntryId = entryId;
  ledgerDetailDownloadLink.href = detail.downloadUrl;
  ledgerPreviewContainer.innerHTML =
    detail.fileType.toLowerCase() === "pdf"
      ? `<iframe class="ledger-preview-frame" src="${detail.previewUrl}" title="发票预览"></iframe>`
      : `
          <div class="ledger-preview-placeholder">
            <p>当前文件为 OFD，浏览器可能无法直接内嵌显示。</p>
            <a class="primary-btn" href="${detail.downloadUrl}">下载查看</a>
          </div>
        `;
  ledgerInfoList.innerHTML = detail.infoItems.map(renderInfoItem).join("");
  ledgerExtendedList.innerHTML = detail.extendedItems.map(renderInfoItem).join("");
  ledgerDetailSection.classList.remove("hidden");
  renderLedgerGroups();
  renderLedgerToolbar();
  ledgerDetailSection.scrollIntoView({ behavior: "smooth", block: "start" });
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
  ledgerDetailSection.classList.add("hidden");
  renderLedgerGroups();
  renderLedgerToolbar();
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
  ledgerState.selectedIds.clear();
  await loadLedgerEntries();
}

function toggleFilterPanel() {
  ledgerFilterPanel.classList.toggle("collapsed");
  toggleFilterBtn.textContent = ledgerFilterPanel.classList.contains("collapsed") ? "展开" : "收起";
}

function formatChineseDate(value) {
  if (!value) return "-";
  const [year, month, day] = value.split("-");
  return `${Number(year)}年${Number(month)}月${Number(day)}日`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

loadLedgerEntries();
