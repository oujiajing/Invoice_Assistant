const invoiceTypeConfigs = {
  general: {
    key: "general",
    apiBase: "/api/general-invoice",
    label: "常规数电发票",
    heroTitle: "免费在线 PDF / OFD 格式常规数电发票文件重命名",
    heroDescription: "批量上传常规数电发票文件，按票面字段自动识别并预览新文件名，支持自定义规则后导出重命名结果压缩包。",
    uploadTitle: "点击或拖拽上传 PDF / OFD 格式常规数电发票文件",
    uploadDescription: "支持多选批量上传，上传后先进入解析结果列表，再手动开始重命名。",
    emptyMessage: "上传 PDF / OFD 常规数电发票文件后，这里会显示解析结果和重命名预览。",
    defaultTemplate: "{开票日期}_{销售方名称}_{价税合计}",
    templateHint:
      "可用变量：{发票类型} {发票代码} {发票号码} {开票日期} {购买方名称} {购买方税号} {销售方名称} {销售方税号} {发票金额} {发票税额} {价税合计} {价税合计大写} {备注} {收款人} {复核人} {开票人} {自定义内容}",
    fieldDefinitions: [
      { key: "invoice_type", label: "发票类型" },
      { key: "invoice_code", label: "发票代码" },
      { key: "invoice_number", label: "发票号码" },
      { key: "issue_date", label: "开票日期" },
      { key: "buyer_name", label: "购买方名称" },
      { key: "buyer_tax_number", label: "购买方税号" },
      { key: "seller_name", label: "销售方名称" },
      { key: "seller_tax_number", label: "销售方税号" },
      { key: "amount", label: "发票金额" },
      { key: "tax_amount", label: "发票税额" },
      { key: "total_amount", label: "价税合计" },
      { key: "total_amount_upper", label: "价税合计大写" },
      { key: "remarks", label: "备注" },
      { key: "payee", label: "收款人" },
      { key: "reviewer", label: "复核人" },
      { key: "issuer", label: "开票人" },
      { key: "custom_content", label: "自定义内容" },
    ],
    defaultTokens: [
      { type: "field", value: "issue_date" },
      { type: "field", value: "seller_name" },
      { type: "field", value: "total_amount" },
    ],
    resultColumns: [
      { key: "status", label: "状态" },
      { key: "originalName", label: "原文件名" },
      { key: "invoice_type", label: "发票类型" },
      { key: "invoice_number", label: "发票号码" },
      { key: "issue_date", label: "开票日期" },
      { key: "buyer_name", label: "购买方名称" },
      { key: "seller_name", label: "销售方名称" },
      { key: "total_amount", label: "价税合计" },
      { key: "previewName", label: "新文件名预览" },
      { key: "actions", label: "操作" },
    ],
  },
  railway: {
    key: "railway",
    apiBase: "/api/railway",
    label: "铁路电子客票",
    heroTitle: "免费在线 PDF / OFD 格式铁路电子客票文件重命名",
    heroDescription: "批量上传铁路电子客票文件，按票面字段自动识别并预览新文件名，支持自定义规则后导出重命名结果压缩包。",
    uploadTitle: "点击或拖拽上传 PDF / OFD 格式铁路电子客票文件",
    uploadDescription: "支持多选批量上传，上传后先进入解析结果列表，再手动开始重命名。",
    emptyMessage: "上传 PDF / OFD 铁路电子客票文件后，这里会显示解析结果和重命名预览。",
    defaultTemplate: "{开票日期}_{出发站}_{到达站}_{票价}",
    templateHint:
      "可用变量：{发票号码} {开票日期} {出发站} {到达站} {发车时间} {车次} {座位号} {票价} {乘车人姓名} {乘车人身份证号} {自定义内容}",
    fieldDefinitions: [
      { key: "invoice_number", label: "发票号码" },
      { key: "issue_date", label: "开票日期" },
      { key: "departure_station", label: "出发站" },
      { key: "arrival_station", label: "到达站" },
      { key: "departure_datetime", label: "发车时间" },
      { key: "train_number", label: "车次" },
      { key: "seat_number", label: "座位号" },
      { key: "amount", label: "票价" },
      { key: "passenger_name", label: "乘车人姓名" },
      { key: "passenger_id", label: "乘车人身份证号" },
      { key: "custom_content", label: "自定义内容" },
    ],
    defaultTokens: [
      { type: "field", value: "issue_date" },
      { type: "field", value: "departure_station" },
      { type: "field", value: "arrival_station" },
      { type: "field", value: "amount" },
    ],
    resultColumns: [
      { key: "status", label: "状态" },
      { key: "originalName", label: "原文件名" },
      { key: "invoice_number", label: "发票号码" },
      { key: "issue_date", label: "开票日期" },
      { key: "departure_station", label: "出发站" },
      { key: "arrival_station", label: "到达站" },
      { key: "departure_datetime", label: "发车时间" },
      { key: "amount", label: "票价" },
      { key: "previewName", label: "新文件名预览" },
      { key: "actions", label: "操作" },
    ],
  },
  airline: {
    key: "airline",
    apiBase: "/api/airline",
    label: "航空电子客票",
    heroTitle: "免费在线 PDF / OFD 格式航空电子客票文件重命名",
    heroDescription: "批量上传航空电子客票发票文件，按票面字段自动识别并预览新文件名，支持自定义规则后导出重命名结果压缩包。",
    uploadTitle: "点击或拖拽上传 PDF / OFD 格式航空电子客票文件",
    uploadDescription: "支持两种航空机票发票版式，上传后先进入解析结果列表，再手动开始重命名。",
    emptyMessage: "上传 PDF / OFD 航空电子客票文件后，这里会显示解析结果和重命名预览。",
    defaultTemplate: "{开票日期}_{起飞机场}_{着陆机场}_{航班号}_{价税合计}",
    templateHint:
      "可用变量：{发票号码} {开票日期} {起飞机场} {着陆机场} {航班号} {座位等级} {起飞时间} {票价} {价税合计} {乘机人姓名} {乘机人身份证号} {自定义内容}",
    fieldDefinitions: [
      { key: "invoice_number", label: "发票号码" },
      { key: "issue_date", label: "开票日期" },
      { key: "departure_airport", label: "起飞机场" },
      { key: "arrival_airport", label: "着陆机场" },
      { key: "flight_number", label: "航班号" },
      { key: "cabin_class", label: "座位等级" },
      { key: "departure_time", label: "起飞时间" },
      { key: "amount", label: "票价" },
      { key: "total_amount", label: "价税合计" },
      { key: "passenger_name", label: "乘机人姓名" },
      { key: "passenger_id", label: "乘机人身份证号" },
      { key: "custom_content", label: "自定义内容" },
    ],
    defaultTokens: [
      { type: "field", value: "issue_date" },
      { type: "field", value: "departure_airport" },
      { type: "field", value: "arrival_airport" },
      { type: "field", value: "flight_number" },
    ],
    resultColumns: [
      { key: "status", label: "状态" },
      { key: "originalName", label: "原文件名" },
      { key: "invoice_number", label: "发票号码" },
      { key: "issue_date", label: "开票日期" },
      { key: "departure_airport", label: "起飞机场" },
      { key: "arrival_airport", label: "着陆机场" },
      { key: "flight_number", label: "航班号" },
      { key: "departure_time", label: "起飞时间" },
      { key: "total_amount", label: "价税合计" },
      { key: "previewName", label: "新文件名预览" },
      { key: "actions", label: "操作" },
    ],
  },
};

const state = {
  activeInvoiceType: "general",
  documentsByType: {
    general: [],
    railway: [],
    airline: [],
  },
  ruleConfigByType: {
    general: createDefaultRuleConfig(invoiceTypeConfigs.general),
    railway: createDefaultRuleConfig(invoiceTypeConfigs.railway),
    airline: createDefaultRuleConfig(invoiceTypeConfigs.airline),
  },
  excelColumnsByType: {
    general: invoiceTypeConfigs.general.fieldDefinitions.map(item => item.key),
    railway: invoiceTypeConfigs.railway.fieldDefinitions.map(item => item.key),
    airline: invoiceTypeConfigs.airline.fieldDefinitions.map(item => item.key),
  },
};

const fileInput = document.getElementById("fileInput");
const dropzone = document.getElementById("dropzone");
const pickFilesBtn = document.getElementById("pickFilesBtn");
const configureRuleBtn = document.getElementById("configureRuleBtn");
const previewBtn = document.getElementById("previewBtn");
const clearBtn = document.getElementById("clearBtn");
const exportExcelBtn = document.getElementById("exportExcelBtn");
const downloadBtn = document.getElementById("downloadBtn");
const resultsHeaderRow = document.getElementById("resultsHeaderRow");
const resultsBody = document.getElementById("resultsBody");
const resultBadge = document.getElementById("resultBadge");
const summaryText = document.getElementById("summaryText");
const statusText = document.getElementById("statusText");
const heroChip = document.getElementById("heroChip");
const heroTitle = document.getElementById("heroTitle");
const heroDescription = document.getElementById("heroDescription");
const uploadTitle = document.getElementById("uploadTitle");
const uploadDescription = document.getElementById("uploadDescription");
const invoiceTypeButtons = [...document.querySelectorAll("[data-invoice-type]")];

const ruleModal = document.getElementById("ruleModal");
const closeRuleBtn = document.getElementById("closeRuleBtn");
const cancelRuleBtn = document.getElementById("cancelRuleBtn");
const saveRuleBtn = document.getElementById("saveRuleBtn");
const fieldPool = document.getElementById("fieldPool");
const tokenList = document.getElementById("tokenList");
const customTextInput = document.getElementById("customTextInput");
const addCustomTextBtn = document.getElementById("addCustomTextBtn");
const separatorInput = document.getElementById("separatorInput");
const dateFormatSelect = document.getElementById("dateFormatSelect");
const amountFormatSelect = document.getElementById("amountFormatSelect");
const templateInput = document.getElementById("templateInput");
const templateHint = document.getElementById("templateHint");
const modalPreview = document.getElementById("modalPreview");
const modeButtons = [...document.querySelectorAll(".mode-btn")];
const tokensPanel = document.getElementById("tokensPanel");
const templatePanel = document.getElementById("templatePanel");
const excelModal = document.getElementById("excelModal");
const closeExcelBtn = document.getElementById("closeExcelBtn");
const cancelExcelBtn = document.getElementById("cancelExcelBtn");
const confirmExcelBtn = document.getElementById("confirmExcelBtn");
const selectAllExcelBtn = document.getElementById("selectAllExcelBtn");
const invertExcelBtn = document.getElementById("invertExcelBtn");
const excelColumnList = document.getElementById("excelColumnList");
const excelSelectionSummary = document.getElementById("excelSelectionSummary");

let draggedTokenIndex = null;
let dragOverTokenIndex = null;
let dragInsertPosition = null;

pickFilesBtn.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", event => uploadFiles(event.target.files));
configureRuleBtn.addEventListener("click", openRuleModal);
previewBtn.addEventListener("click", previewNames);
clearBtn.addEventListener("click", clearDocuments);
exportExcelBtn.addEventListener("click", openExcelModal);
downloadBtn.addEventListener("click", downloadZip);
closeRuleBtn.addEventListener("click", closeRuleModal);
cancelRuleBtn.addEventListener("click", closeRuleModal);
closeExcelBtn.addEventListener("click", closeExcelModal);
cancelExcelBtn.addEventListener("click", closeExcelModal);
confirmExcelBtn.addEventListener("click", exportExcel);
selectAllExcelBtn.addEventListener("click", selectAllExcelColumns);
invertExcelBtn.addEventListener("click", invertExcelColumns);
saveRuleBtn.addEventListener("click", async () => {
  syncRuleConfigFromModal();
  closeRuleModal();
  await previewNames();
});
addCustomTextBtn.addEventListener("click", () => {
  const value = customTextInput.value.trim();
  if (!value) return;
  currentRuleConfig().tokens.push({ type: "text", value });
  customTextInput.value = "";
  renderTokenList();
  updateModalPreview();
});
separatorInput.addEventListener("input", updateModalPreview);
dateFormatSelect.addEventListener("change", updateModalPreview);
amountFormatSelect.addEventListener("change", updateModalPreview);
templateInput.addEventListener("input", updateModalPreview);
modeButtons.forEach(button => button.addEventListener("click", () => switchRuleMode(button.dataset.mode)));
invoiceTypeButtons.forEach(button => {
  button.addEventListener("click", () => switchInvoiceType(button.dataset.invoiceType));
});

["dragenter", "dragover"].forEach(eventName => {
  dropzone.addEventListener(eventName, event => {
    event.preventDefault();
    dropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach(eventName => {
  dropzone.addEventListener(eventName, event => {
    event.preventDefault();
    dropzone.classList.remove("dragover");
  });
});
dropzone.addEventListener("drop", event => {
  uploadFiles(event.dataTransfer.files);
});

function createDefaultRuleConfig(config) {
  return {
    mode: "tokens",
    tokens: config.defaultTokens.map(item => ({ ...item })),
    template: config.defaultTemplate,
    separator: "_",
    dateFormat: "YYYY年MM月DD日",
    amountFormat: "0.00",
    sanitize: true,
    duplicateStrategy: "suffix",
  };
}

function currentConfig() {
  return invoiceTypeConfigs[state.activeInvoiceType];
}

function currentDocuments() {
  return state.documentsByType[state.activeInvoiceType];
}

function currentRuleConfig() {
  return state.ruleConfigByType[state.activeInvoiceType];
}

function currentExcelColumns() {
  return state.excelColumnsByType[state.activeInvoiceType];
}

function switchInvoiceType(invoiceType) {
  if (!invoiceTypeConfigs[invoiceType]) return;
  state.activeInvoiceType = invoiceType;
  invoiceTypeButtons.forEach(button => {
    button.classList.toggle("nav-sub-item-active", button.dataset.invoiceType === invoiceType);
  });
  applyInvoiceTypeConfig();
  renderFieldPool();
  renderTokenList();
  renderResults();
}

function applyInvoiceTypeConfig() {
  const config = currentConfig();
  heroChip.textContent = config.label;
  heroTitle.textContent = config.heroTitle;
  heroDescription.textContent = config.heroDescription;
  uploadTitle.textContent = config.uploadTitle;
  uploadDescription.textContent = config.uploadDescription;
  templateInput.value = currentRuleConfig().template;
  templateHint.textContent = config.templateHint;
  resultsHeaderRow.innerHTML = config.resultColumns.map(column => `<th>${escapeHtml(column.label)}</th>`).join("");
}

function renderFieldPool() {
  const config = currentConfig();
  fieldPool.innerHTML = "";
  config.fieldDefinitions.forEach(field => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "field-btn";
    button.textContent = field.label;
    button.addEventListener("click", () => {
      currentRuleConfig().tokens.push({ type: "field", value: field.key });
      renderTokenList();
      updateModalPreview();
    });
    fieldPool.appendChild(button);
  });
}

function renderTokenList() {
  const tokens = currentRuleConfig().tokens;
  if (!tokens.length) {
    tokenList.className = "token-list empty";
    tokenList.innerHTML = '<div class="empty-builder">勾选左侧字段或添加固定文字</div>';
    return;
  }

  tokenList.className = "token-list";
  tokenList.innerHTML = "";
  tokens.forEach((token, index) => {
    const item = document.createElement("div");
    item.className = "token-item";
    item.draggable = true;
    item.dataset.index = String(index);
    item.innerHTML = `
      <div class="token-label">
        <strong>${escapeHtml(token.type === "field" ? getFieldLabel(token.value) : "固定文字")}</strong>
        <span>${escapeHtml(token.value)}</span>
      </div>
      <div class="token-actions">
        <span class="drag-handle" title="拖动排序">⋮⋮</span>
        <button type="button" class="mini-btn" data-action="remove" data-index="${index}">×</button>
      </div>
    `;
    item.addEventListener("dragstart", () => {
      draggedTokenIndex = index;
      item.classList.add("dragging");
    });
    item.addEventListener("dragend", () => {
      draggedTokenIndex = null;
      dragOverTokenIndex = null;
      dragInsertPosition = null;
      clearDragIndicators();
    });
    item.addEventListener("dragover", event => {
      event.preventDefault();
      const rect = item.getBoundingClientRect();
      dragOverTokenIndex = index;
      dragInsertPosition = event.clientY < rect.top + rect.height / 2 ? "before" : "after";
      updateDragIndicators();
    });
    item.addEventListener("dragleave", () => {
      item.classList.remove("drag-over-top", "drag-over-bottom");
    });
    item.addEventListener("drop", event => {
      event.preventDefault();
      moveToken(index, dragInsertPosition);
    });
    tokenList.appendChild(item);
  });

  tokenList.querySelectorAll(".mini-btn").forEach(button => {
    button.addEventListener("click", event => {
      const index = Number(event.currentTarget.dataset.index);
      currentRuleConfig().tokens.splice(index, 1);
      renderTokenList();
      updateModalPreview();
    });
  });
}

function moveToken(targetIndex, insertPosition = "before") {
  if (draggedTokenIndex === null || targetIndex === null) return;
  let insertIndex = insertPosition === "after" ? targetIndex + 1 : targetIndex;
  if (draggedTokenIndex < insertIndex) insertIndex -= 1;
  if (insertIndex === draggedTokenIndex) {
    dragOverTokenIndex = null;
    dragInsertPosition = null;
    clearDragIndicators();
    return;
  }

  const tokens = currentRuleConfig().tokens;
  const [movedItem] = tokens.splice(draggedTokenIndex, 1);
  tokens.splice(insertIndex, 0, movedItem);
  dragOverTokenIndex = null;
  dragInsertPosition = null;
  renderTokenList();
  updateModalPreview();
}

function clearDragIndicators() {
  tokenList.querySelectorAll(".token-item").forEach(tokenNode => {
    tokenNode.classList.remove("dragging", "drag-over-top", "drag-over-bottom");
  });
}

function updateDragIndicators() {
  clearDragIndicators();
  tokenList.querySelectorAll(".token-item").forEach(tokenNode => {
    const index = Number(tokenNode.dataset.index);
    if (index === draggedTokenIndex) tokenNode.classList.add("dragging");
    if (index === dragOverTokenIndex) {
      tokenNode.classList.add(dragInsertPosition === "before" ? "drag-over-top" : "drag-over-bottom");
    }
  });
}

async function uploadFiles(fileList) {
  const files = [...fileList].filter(file => /\.(pdf|ofd)$/i.test(file.name));
  if (!files.length) {
    window.alert("请选择 PDF 或 OFD 格式的发票文件。");
    return;
  }

  const formData = new FormData();
  files.forEach(file => formData.append("files", file));

  setBusyState("正在上传并解析票据...");
  const response = await fetch(`${currentConfig().apiBase}/upload-and-parse`, { method: "POST", body: formData });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "上传失败，请稍后重试。" }));
    clearBusyState(error.message);
    return;
  }

  state.documentsByType[state.activeInvoiceType] = (await response.json()).map(item => ({ ...item, previewName: "" }));
  clearBusyState("票据已上传并完成解析，请点击开始重命名生成预览。");
  renderResults();
}

async function previewNames() {
  if (!currentDocuments().length) return;
  syncRuleConfigFromModal();
  const response = await fetch(`${currentConfig().apiBase}/preview-rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      documentIds: currentDocuments().map(item => item.id),
      ruleConfig: currentRuleConfig(),
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "预览生成失败。" }));
    clearBusyState(error.message);
    return;
  }

  const previewMap = new Map((await response.json()).map(item => [item.id, item]));
  state.documentsByType[state.activeInvoiceType] = currentDocuments().map(item => ({
    ...item,
    previewName: previewMap.get(item.id)?.conflictResolvedName || "",
  }));
  clearBusyState("预览已更新，可继续调整规则或下载结果。");
  renderResults();
}

async function downloadZip() {
  const response = await fetch(`${currentConfig().apiBase}/export`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      documentIds: currentDocuments().map(item => item.id),
      ruleConfig: currentRuleConfig(),
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "导出失败，请稍后重试。" }));
    window.alert(error.message || "导出失败");
    return;
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${currentConfig().label}重命名结果.zip`;
  link.click();
  window.URL.revokeObjectURL(url);
}

function openExcelModal() {
  renderExcelColumns();
  excelModal.classList.remove("hidden");
}

function closeExcelModal() {
  excelModal.classList.add("hidden");
}

function renderExcelColumns() {
  const selected = new Set(currentExcelColumns());
  excelColumnList.innerHTML = currentConfig().fieldDefinitions
    .map(
      field => `
        <label class="excel-column-item">
          <input type="checkbox" data-column-key="${escapeHtml(field.key)}" ${selected.has(field.key) ? "checked" : ""} />
          <span>${escapeHtml(field.label)}</span>
        </label>
      `,
    )
    .join("");

  excelColumnList.querySelectorAll("[data-column-key]").forEach(input => {
    input.addEventListener("change", event => {
      const { columnKey } = event.currentTarget.dataset;
      const next = new Set(currentExcelColumns());
      if (event.currentTarget.checked) {
        next.add(columnKey);
      } else {
        next.delete(columnKey);
      }
      state.excelColumnsByType[state.activeInvoiceType] = currentConfig().fieldDefinitions
        .map(item => item.key)
        .filter(key => next.has(key));
      updateExcelSelectionSummary();
    });
  });

  updateExcelSelectionSummary();
}

function updateExcelSelectionSummary() {
  excelSelectionSummary.textContent = `已选择 ${currentExcelColumns().length} 列`;
}

function selectAllExcelColumns() {
  state.excelColumnsByType[state.activeInvoiceType] = currentConfig().fieldDefinitions.map(item => item.key);
  renderExcelColumns();
}

function invertExcelColumns() {
  const selected = new Set(currentExcelColumns());
  state.excelColumnsByType[state.activeInvoiceType] = currentConfig().fieldDefinitions
    .map(item => item.key)
    .filter(key => !selected.has(key));
  renderExcelColumns();
}

async function exportExcel() {
  const response = await fetch(`${currentConfig().apiBase}/export-excel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      documentIds: currentDocuments().map(item => item.id),
      ruleConfig: currentRuleConfig(),
      excelColumns: currentExcelColumns(),
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "导出 Excel 失败，请稍后重试。" }));
    window.alert(error.message || "导出 Excel 失败");
    return;
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${currentConfig().label}信息台账.xlsx`;
  link.click();
  window.URL.revokeObjectURL(url);
  closeExcelModal();
}

async function deleteDocument(documentId) {
  const response = await fetch(`${currentConfig().apiBase}/documents/${documentId}`, { method: "DELETE" });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "删除失败，请稍后重试。" }));
    window.alert(error.message || "删除失败");
    return;
  }

  state.documentsByType[state.activeInvoiceType] = currentDocuments().filter(item => item.id !== documentId);
  clearBusyState(currentDocuments().length ? "票据已删除。" : "列表已清空。");
  renderResults();
}

async function clearDocuments() {
  if (!currentDocuments().length) return;
  const response = await fetch(`${currentConfig().apiBase}/documents`, { method: "DELETE" });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "清空失败，请稍后重试。" }));
    window.alert(error.message || "清空失败");
    return;
  }

  state.documentsByType[state.activeInvoiceType] = [];
  clearBusyState("列表已清空。");
  renderResults();
}

function renderResults() {
  const documents = currentDocuments();
  const emptyMessage = currentConfig().emptyMessage;
  if (!documents.length) {
    resultsBody.innerHTML = `<tr class="empty-row"><td colspan="${currentConfig().resultColumns.length}">${escapeHtml(emptyMessage)}</td></tr>`;
    summaryText.textContent = "暂未上传文件";
    statusText.textContent = "上传后先进入解析结果列表，点击开始重命名后再生成新文件名预览。";
    resultBadge.textContent = "等待上传";
    configureRuleBtn.disabled = true;
    previewBtn.disabled = true;
    clearBtn.disabled = true;
    exportExcelBtn.disabled = true;
    downloadBtn.disabled = true;
    return;
  }

  const successCount = documents.filter(item => item.parseStatus === "success").length;
  const failedCount = documents.length - successCount;
  const readyToDownload = documents.some(item => item.previewName);
  resultBadge.textContent = `成功 ${successCount} / 失败 ${failedCount}`;
  summaryText.textContent = `共 ${documents.length} 张票据，成功解析 ${successCount} 张`;
  statusText.textContent = failedCount ? `有 ${failedCount} 张票据解析失败，可检查文件内容或格式。` : "所有票据已完成解析，可以继续调整重命名规则。";
  configureRuleBtn.disabled = false;
  previewBtn.disabled = false;
  clearBtn.disabled = false;
  exportExcelBtn.disabled = false;
  downloadBtn.disabled = !readyToDownload;

  resultsBody.innerHTML = documents
    .map(item => {
      if (item.parseStatus !== "success") {
        return `
          <tr>
            <td><span class="status-failed">解析失败</span></td>
            <td>${escapeHtml(item.originalName)}</td>
            <td colspan="${currentConfig().resultColumns.length - 3}">${escapeHtml(item.error || "未能识别为目标发票类型。")}</td>
            <td><div class="row-actions"><button type="button" class="danger-btn" data-delete-id="${item.id}">删除</button></div></td>
          </tr>
        `;
      }
      const cells = currentConfig().resultColumns
        .map(column => renderCell(item, column.key))
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  resultsBody.querySelectorAll("[data-delete-id]").forEach(button => {
    button.addEventListener("click", () => deleteDocument(button.dataset.deleteId));
  });
}

function renderCell(item, key) {
  if (key === "status") {
    return `<td><span class="status-success">解析成功</span></td>`;
  }
  if (key === "originalName") {
    return `<td>${escapeHtml(item.originalName)}</td>`;
  }
  if (key === "previewName") {
    return `<td class="filename-preview">${escapeHtml(item.previewName || "-")}</td>`;
  }
  if (key === "actions") {
    return `<td><div class="row-actions"><button type="button" class="danger-btn" data-delete-id="${item.id}">删除</button></div></td>`;
  }
  return `<td>${escapeHtml(item.fields[key] || "-")}</td>`;
}

function openRuleModal() {
  const rule = currentRuleConfig();
  separatorInput.value = rule.separator;
  dateFormatSelect.value = rule.dateFormat;
  amountFormatSelect.value = rule.amountFormat;
  templateInput.value = rule.template;
  templateHint.textContent = currentConfig().templateHint;
  switchRuleMode(rule.mode);
  renderTokenList();
  updateModalPreview();
  ruleModal.classList.remove("hidden");
}

function closeRuleModal() {
  ruleModal.classList.add("hidden");
}

function switchRuleMode(mode) {
  currentRuleConfig().mode = mode;
  modeButtons.forEach(button => button.classList.toggle("mode-btn-active", button.dataset.mode === mode));
  tokensPanel.classList.toggle("hidden", mode !== "tokens");
  templatePanel.classList.toggle("hidden", mode !== "template");
  updateModalPreview();
}

function syncRuleConfigFromModal() {
  const rule = currentRuleConfig();
  rule.separator = separatorInput.value || "_";
  rule.dateFormat = dateFormatSelect.value;
  rule.amountFormat = amountFormatSelect.value;
  rule.template = templateInput.value.trim() || currentConfig().defaultTemplate;
}

function updateModalPreview() {
  syncRuleConfigFromModal();
  const sample = currentDocuments().find(item => item.parseStatus === "success");
  if (!sample) {
    modalPreview.textContent = "请先上传至少一张可识别票据";
    return;
  }
  const values = { ...sample.fields };
  if (values.issue_date) values.issue_date = formatDate(values.issue_date, currentRuleConfig().dateFormat);
  if (values.departure_datetime) values.departure_datetime = formatDateTime(values.departure_datetime, currentRuleConfig().dateFormat);
  if (values.departure_time) values.departure_time = formatDateTime(values.departure_time, currentRuleConfig().dateFormat);
  if (currentRuleConfig().mode === "template") {
    modalPreview.textContent = renderTemplate(currentRuleConfig().template, values) || "暂无示例";
    return;
  }
  const parts = currentRuleConfig().tokens.map(token => (token.type === "text" ? token.value : values[token.value] || ""));
  modalPreview.textContent = parts.filter(Boolean).join(currentRuleConfig().separator) || "暂无示例";
}

function renderTemplate(template, values) {
  const alias = Object.fromEntries(currentConfig().fieldDefinitions.map(item => [item.label, item.key]));
  return template.replace(/\{([^{}]+)\}/g, (_, key) => values[alias[key] || key] || "");
}

function formatDate(value, format) {
  if (!value) return "";
  if (format === "YYYY-MM-DD") return value;
  const [year, month, day] = value.split("-");
  return `${year}年${month}月${day}日`;
}

function formatDateTime(value, format) {
  if (!value) return "";
  if (/^\d{2}:\d{2}$/.test(value)) return value;
  if (!value.includes(" ")) return formatDate(value, format);
  const [datePart, timePart] = value.split(" ");
  return `${formatDate(datePart, format)} ${timePart}`;
}

function setBusyState(message) {
  statusText.textContent = message;
  previewBtn.disabled = true;
  clearBtn.disabled = true;
  exportExcelBtn.disabled = true;
  downloadBtn.disabled = true;
}

function clearBusyState(message) {
  statusText.textContent = message;
  previewBtn.disabled = !currentDocuments().length;
  clearBtn.disabled = !currentDocuments().length;
  exportExcelBtn.disabled = !currentDocuments().length;
  downloadBtn.disabled = !currentDocuments().some(item => item.previewName);
}

function getFieldLabel(key) {
  return currentConfig().fieldDefinitions.find(item => item.key === key)?.label || key;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

applyInvoiceTypeConfig();
renderFieldPool();
renderTokenList();
renderResults();
