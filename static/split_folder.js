const splitTypeConfigs = {
  general: {
    key: "general",
    apiBase: "/api/general-invoice",
    label: "常规数电发票",
    heroTitle: "本地 PDF / OFD 格式常规数电发票划分文件夹",
    heroDescription: "批量上传常规数电发票文件，按票面字段自由组合划分文件夹，并导出带目录结构的压缩包。",
    uploadTitle: "点击或拖拽上传 PDF / OFD 格式常规数电发票文件",
    uploadDescription: "支持多选批量上传，上传后先进入文件列表，再手动开始划分。",
    defaultTemplate: "{开票日期}/{销售方名称}/{价税合计}",
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
  },
  railway: {
    key: "railway",
    apiBase: "/api/railway",
    label: "铁路电子客票",
    heroTitle: "本地 PDF / OFD 格式铁路电子客票划分文件夹",
    heroDescription: "批量上传铁路电子客票文件，按票面字段自由组合划分文件夹，并导出带目录结构的压缩包。",
    uploadTitle: "点击或拖拽上传 PDF / OFD 格式铁路电子客票文件",
    uploadDescription: "支持多选批量上传，上传后先进入文件列表，再手动开始划分。",
    defaultTemplate: "{开票日期}/{出发站}/{到达站}/{票价}",
    templateHint: "可用变量：{发票号码} {开票日期} {出发站} {到达站} {发车时间} {车次} {座位号} {票价} {乘车人姓名} {乘车人身份证号} {自定义内容}",
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
  },
  airline: {
    key: "airline",
    apiBase: "/api/airline",
    label: "航空电子客票",
    heroTitle: "本地 PDF / OFD 格式航空电子客票划分文件夹",
    heroDescription: "批量上传航空电子客票发票文件，按票面字段自由组合划分文件夹，并导出带目录结构的压缩包。",
    uploadTitle: "点击或拖拽上传 PDF / OFD 格式航空电子客票文件",
    uploadDescription: "支持两种航空机票发票版式，上传后先进入文件列表，再手动开始划分。",
    defaultTemplate: "{开票日期}/{起飞机场}/{着陆机场}/{航班号}",
    templateHint: "可用变量：{发票号码} {开票日期} {起飞机场} {着陆机场} {航班号} {座位等级} {起飞时间} {票价} {价税合计} {乘机人姓名} {乘机人身份证号} {自定义内容}",
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
  },
};

const splitState = {
  activeInvoiceType: "general",
  documentsByType: {
    general: [],
    railway: [],
    airline: [],
  },
  ruleConfigByType: {
    general: createDefaultSplitRule(splitTypeConfigs.general),
    railway: createDefaultSplitRule(splitTypeConfigs.railway),
    airline: createDefaultSplitRule(splitTypeConfigs.airline),
  },
};

const splitFileInput = document.getElementById("splitFileInput");
const splitDropzone = document.getElementById("splitDropzone");
const splitPickFilesBtn = document.getElementById("splitPickFilesBtn");
const splitAddFilesBtn = document.getElementById("splitAddFilesBtn");
const splitClearBtn = document.getElementById("splitClearBtn");
const splitConfigureRuleBtn = document.getElementById("splitConfigureRuleBtn");
const splitPreviewBtn = document.getElementById("splitPreviewBtn");
const splitDownloadBtn = document.getElementById("splitDownloadBtn");
const splitListBody = document.getElementById("splitListBody");
const splitListBadge = document.getElementById("splitListBadge");
const splitHeroChip = document.getElementById("splitHeroChip");
const splitHeroTitle = document.getElementById("splitHeroTitle");
const splitHeroDescription = document.getElementById("splitHeroDescription");
const splitUploadTitle = document.getElementById("splitUploadTitle");
const splitUploadDescription = document.getElementById("splitUploadDescription");
const splitTypeButtons = [...document.querySelectorAll("[data-invoice-type]")];

const splitRuleModal = document.getElementById("splitRuleModal");
const splitCloseRuleBtn = document.getElementById("splitCloseRuleBtn");
const splitCancelRuleBtn = document.getElementById("splitCancelRuleBtn");
const splitSaveRuleBtn = document.getElementById("splitSaveRuleBtn");
const splitFieldPool = document.getElementById("splitFieldPool");
const splitTokenList = document.getElementById("splitTokenList");
const splitCustomTextInput = document.getElementById("splitCustomTextInput");
const splitAddCustomTextBtn = document.getElementById("splitAddCustomTextBtn");
const splitSeparatorInput = document.getElementById("splitSeparatorInput");
const splitDateFormatSelect = document.getElementById("splitDateFormatSelect");
const splitAmountFormatSelect = document.getElementById("splitAmountFormatSelect");
const splitTemplateInput = document.getElementById("splitTemplateInput");
const splitTemplateHint = document.getElementById("splitTemplateHint");
const splitModalPreview = document.getElementById("splitModalPreview");
const splitModeButtons = [...document.querySelectorAll("[data-split-mode]")];
const splitTokensPanel = document.getElementById("splitTokensPanel");
const splitTemplatePanel = document.getElementById("splitTemplatePanel");
const splitShowPrefixCheckbox = document.getElementById("splitShowPrefixCheckbox");

let splitDraggedTokenIndex = null;
let splitDragOverTokenIndex = null;
let splitDragInsertPosition = null;

splitPickFilesBtn.addEventListener("click", () => splitFileInput.click());
splitAddFilesBtn.addEventListener("click", () => splitFileInput.click());
splitFileInput.addEventListener("change", event => uploadSplitFiles(event.target.files));
splitConfigureRuleBtn.addEventListener("click", openSplitRuleModal);
splitPreviewBtn.addEventListener("click", previewSplitFolders);
splitClearBtn.addEventListener("click", clearSplitDocuments);
splitDownloadBtn.addEventListener("click", downloadSplitZip);
splitCloseRuleBtn.addEventListener("click", closeSplitRuleModal);
splitCancelRuleBtn.addEventListener("click", closeSplitRuleModal);
splitSaveRuleBtn.addEventListener("click", async () => {
  syncSplitRuleConfigFromModal();
  closeSplitRuleModal();
  await previewSplitFolders();
});
splitAddCustomTextBtn.addEventListener("click", () => {
  const value = splitCustomTextInput.value.trim();
  if (!value) return;
  currentSplitRule().tokens.push({ type: "text", value });
  splitCustomTextInput.value = "";
  renderSplitTokenList();
  updateSplitModalPreview();
});
splitSeparatorInput.addEventListener("input", updateSplitModalPreview);
splitDateFormatSelect.addEventListener("change", updateSplitModalPreview);
splitAmountFormatSelect.addEventListener("change", updateSplitModalPreview);
splitTemplateInput.addEventListener("input", updateSplitModalPreview);
splitShowPrefixCheckbox.addEventListener("change", updateSplitModalPreview);
splitModeButtons.forEach(button => button.addEventListener("click", () => switchSplitMode(button.dataset.splitMode)));
splitTypeButtons.forEach(button => button.addEventListener("click", () => switchSplitInvoiceType(button.dataset.invoiceType)));

["dragenter", "dragover"].forEach(eventName => {
  splitDropzone.addEventListener(eventName, event => {
    event.preventDefault();
    splitDropzone.classList.add("dragover");
  });
});
["dragleave", "drop"].forEach(eventName => {
  splitDropzone.addEventListener(eventName, event => {
    event.preventDefault();
    splitDropzone.classList.remove("dragover");
  });
});
splitDropzone.addEventListener("drop", event => uploadSplitFiles(event.dataTransfer.files));

function createDefaultSplitRule(config) {
  return {
    mode: "tokens",
    tokens: config.defaultTokens.map(token => ({ ...token })),
    template: config.defaultTemplate,
    separator: "/",
    dateFormat: "YYYY年MM月DD日",
    amountFormat: "0.00",
    sanitize: true,
    duplicateStrategy: "suffix",
    showItemPrefix: false,
  };
}

function currentSplitConfig() {
  return splitTypeConfigs[splitState.activeInvoiceType];
}

function currentSplitDocuments() {
  return splitState.documentsByType[splitState.activeInvoiceType];
}

function currentSplitRule() {
  return splitState.ruleConfigByType[splitState.activeInvoiceType];
}

async function uploadSplitFiles(fileList) {
  const files = [...fileList].filter(file => /\.(pdf|ofd)$/i.test(file.name));
  if (!files.length) {
    window.alert("当前仅支持 PDF 或 OFD 文件。");
    return;
  }

  const formData = new FormData();
  files.forEach(file => formData.append("files", file));
  const response = await fetch(`${currentSplitConfig().apiBase}/upload-and-parse`, { method: "POST", body: formData });
  const payload = await response.json().catch(() => ({ message: "上传失败，请稍后重试。" }));
  if (!response.ok) {
    window.alert(payload.message || "上传失败，请稍后重试。");
    return;
  }

  splitState.documentsByType[splitState.activeInvoiceType] = [...currentSplitDocuments(), ...payload];
  splitFileInput.value = "";
  renderSplitDocuments();
}

function renderSplitDocuments() {
  const documents = currentSplitDocuments();
  splitListBadge.textContent = documents.length ? `共 ${documents.length} 张` : "等待上传";
  splitConfigureRuleBtn.disabled = !documents.length;
  splitPreviewBtn.disabled = !documents.length;
  splitClearBtn.disabled = !documents.length;
  splitDownloadBtn.disabled = !documents.some(document => document.parseStatus === "success" && document.fullOutputPath);
  splitConfigureRuleBtn.textContent = documents.length ? "已设置" : "未设置";

  if (!documents.length) {
    splitListBody.innerHTML = '<tr class="empty-row"><td colspan="4">上传 PDF / OFD 文件后，这里会显示待划分文件列表。</td></tr>';
    return;
  }

  splitListBody.innerHTML = documents
    .map(
      (document, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>
            <div class="split-file-cell">
              <strong>${escapeHtml(document.originalName)}</strong>
              ${document.fullOutputPath ? `<span class="split-path-preview">${escapeHtml(document.fullOutputPath)}</span>` : ""}
              ${document.parseStatus === "failed" ? `<span class="split-error-text">${escapeHtml(document.error || "解析失败")}</span>` : ""}
            </div>
          </td>
          <td><span class="split-status ${document.parseStatus === "success" && document.fullOutputPath ? "is-ready" : "is-pending"}">${document.parseStatus === "failed" ? "划分失败" : document.fullOutputPath ? "已划分" : "待划分"}</span></td>
          <td><button class="icon-btn" data-split-delete="${document.id}">×</button></td>
        </tr>
      `,
    )
    .join("");

  splitListBody.querySelectorAll("[data-split-delete]").forEach(button => {
    button.addEventListener("click", () => deleteSplitDocument(button.dataset.splitDelete));
  });
}

async function deleteSplitDocument(documentId) {
  const response = await fetch(`${currentSplitConfig().apiBase}/documents/${documentId}`, { method: "DELETE" });
  if (!response.ok) {
    window.alert("删除失败，请稍后重试。");
    return;
  }
  splitState.documentsByType[splitState.activeInvoiceType] = currentSplitDocuments().filter(document => document.id !== documentId);
  renderSplitDocuments();
}

async function clearSplitDocuments() {
  const response = await fetch(`${currentSplitConfig().apiBase}/documents`, { method: "DELETE" });
  if (!response.ok) {
    window.alert("清空失败，请稍后重试。");
    return;
  }
  splitState.documentsByType[splitState.activeInvoiceType] = [];
  renderSplitDocuments();
}

async function previewSplitFolders() {
  const documents = currentSplitDocuments();
  if (!documents.length) return;
  const response = await fetch(`${currentSplitConfig().apiBase}/preview-split-folder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      documentIds: documents.map(document => document.id),
      ruleConfig: currentSplitRule(),
    }),
  });
  const payload = await response.json().catch(() => ({ message: "生成划分预览失败。" }));
  if (!response.ok) {
    window.alert(payload.message || "生成划分预览失败。");
    return;
  }

  const previewMap = new Map(payload.map(item => [item.id, item]));
  splitState.documentsByType[splitState.activeInvoiceType] = documents.map(document => ({
    ...document,
    folderPath: previewMap.get(document.id)?.folderPath || "",
    newFileName: previewMap.get(document.id)?.newFileName || "",
    fullOutputPath: previewMap.get(document.id)?.fullOutputPath || "",
  }));
  renderSplitDocuments();
}

async function downloadSplitZip() {
  const documents = currentSplitDocuments();
  if (!documents.length) return;
  const response = await fetch(`${currentSplitConfig().apiBase}/export-split-folder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      documentIds: documents.map(document => document.id),
      ruleConfig: currentSplitRule(),
    }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ message: "下载失败，请稍后重试。" }));
    window.alert(payload.message || "下载失败，请稍后重试。");
    return;
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = `${currentSplitConfig().label}划分文件夹结果.zip`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

function switchSplitInvoiceType(invoiceType) {
  splitState.activeInvoiceType = invoiceType;
  splitTypeButtons.forEach(button => {
    const isActive = button.dataset.invoiceType === invoiceType;
    button.classList.toggle("nav-sub-item-active", isActive);
  });
  syncSplitHero();
  renderSplitDocuments();
}

function syncSplitHero() {
  const config = currentSplitConfig();
  splitHeroChip.textContent = config.label;
  splitHeroTitle.textContent = config.heroTitle;
  splitHeroDescription.textContent = config.heroDescription;
  splitUploadTitle.textContent = config.uploadTitle;
  splitUploadDescription.textContent = config.uploadDescription;
}

function openSplitRuleModal() {
  const config = currentSplitConfig();
  const rule = currentSplitRule();
  splitSeparatorInput.value = rule.separator;
  splitDateFormatSelect.value = rule.dateFormat;
  splitAmountFormatSelect.value = rule.amountFormat;
  splitTemplateInput.value = rule.template;
  splitTemplateHint.textContent = config.templateHint;
  splitShowPrefixCheckbox.checked = Boolean(rule.showItemPrefix);
  switchSplitMode(rule.mode);
  renderSplitFieldPool();
  renderSplitTokenList();
  updateSplitModalPreview();
  splitRuleModal.classList.remove("hidden");
}

function closeSplitRuleModal() {
  splitRuleModal.classList.add("hidden");
}

function switchSplitMode(mode) {
  currentSplitRule().mode = mode;
  splitModeButtons.forEach(button => button.classList.toggle("mode-btn-active", button.dataset.splitMode === mode));
  splitTokensPanel.classList.toggle("hidden", mode !== "tokens");
  splitTemplatePanel.classList.toggle("hidden", mode !== "template");
  updateSplitModalPreview();
}

function renderSplitFieldPool() {
  const selectedFields = new Set(currentSplitRule().tokens.filter(token => token.type === "field").map(token => token.value));
  splitFieldPool.innerHTML = currentSplitConfig().fieldDefinitions
    .map(
      item => `
        <label class="field-item">
          <input type="checkbox" value="${item.key}" ${selectedFields.has(item.key) ? "checked" : ""} />
          <span>${item.label}</span>
        </label>
      `,
    )
    .join("");

  splitFieldPool.querySelectorAll("input[type='checkbox']").forEach(input => {
    input.addEventListener("change", () => {
      const rule = currentSplitRule();
      rule.tokens = rule.tokens.filter(token => !(token.type === "field" && token.value === input.value));
      if (input.checked) {
        rule.tokens.push({ type: "field", value: input.value });
      }
      renderSplitTokenList();
      updateSplitModalPreview();
    });
  });
}

function renderSplitTokenList() {
  const rule = currentSplitRule();
  if (!rule.tokens.length) {
    splitTokenList.className = "token-list empty";
    splitTokenList.innerHTML = '<div class="empty-builder">勾选左侧字段或添加固定文字</div>';
    return;
  }

  splitTokenList.className = "token-list";
  splitTokenList.innerHTML = rule.tokens
    .map((token, index) => {
      const label =
        token.type === "field"
          ? currentSplitConfig().fieldDefinitions.find(item => item.key === token.value)?.label || token.value
          : token.value;
      return `
        <div class="token-card ${splitDragOverTokenIndex === index ? `insert-${splitDragInsertPosition || "before"}` : ""}" draggable="true" data-split-token-index="${index}">
          <div class="token-card__content">
            <strong>${escapeHtml(label)}</strong>
            <span>${escapeHtml(token.type === "field" ? token.value : "fixed_text")}</span>
          </div>
          <button class="icon-btn split-token-remove-btn" data-split-remove-token="${index}">×</button>
        </div>
      `;
    })
    .join("");

  splitTokenList.querySelectorAll("[data-split-remove-token]").forEach(button => {
    button.addEventListener("click", () => {
      rule.tokens.splice(Number(button.dataset.splitRemoveToken), 1);
      renderSplitFieldPool();
      renderSplitTokenList();
      updateSplitModalPreview();
    });
  });

  splitTokenList.querySelectorAll("[data-split-token-index]").forEach(card => {
    card.addEventListener("dragstart", () => {
      splitDraggedTokenIndex = Number(card.dataset.splitTokenIndex);
      card.classList.add("dragging");
    });
    card.addEventListener("dragend", () => {
      splitDraggedTokenIndex = null;
      splitDragOverTokenIndex = null;
      splitDragInsertPosition = null;
      card.classList.remove("dragging");
      renderSplitTokenList();
    });
    card.addEventListener("dragover", event => {
      event.preventDefault();
      const bounds = card.getBoundingClientRect();
      splitDragInsertPosition = event.clientY < bounds.top + bounds.height / 2 ? "before" : "after";
      splitDragOverTokenIndex = Number(card.dataset.splitTokenIndex);
      renderSplitTokenList();
    });
    card.addEventListener("drop", event => {
      event.preventDefault();
      const targetIndex = Number(card.dataset.splitTokenIndex);
      if (splitDraggedTokenIndex === null || splitDraggedTokenIndex === targetIndex) return;
      const [moved] = rule.tokens.splice(splitDraggedTokenIndex, 1);
      const insertIndex =
        splitDragInsertPosition === "after"
          ? (splitDraggedTokenIndex < targetIndex ? targetIndex : targetIndex + 1)
          : splitDraggedTokenIndex < targetIndex
            ? targetIndex - 1
            : targetIndex;
      rule.tokens.splice(insertIndex, 0, moved);
      splitDraggedTokenIndex = null;
      splitDragOverTokenIndex = null;
      splitDragInsertPosition = null;
      renderSplitFieldPool();
      renderSplitTokenList();
      updateSplitModalPreview();
    });
  });
}

function syncSplitRuleConfigFromModal() {
  const rule = currentSplitRule();
  rule.separator = splitSeparatorInput.value || "/";
  rule.dateFormat = splitDateFormatSelect.value;
  rule.amountFormat = splitAmountFormatSelect.value;
  rule.template = splitTemplateInput.value.trim() || currentSplitConfig().defaultTemplate;
  rule.showItemPrefix = splitShowPrefixCheckbox.checked;
}

function updateSplitModalPreview() {
  syncSplitRuleConfigFromModal();
  const rule = currentSplitRule();
  const config = currentSplitConfig();
  const exampleValues = Object.fromEntries(
    config.fieldDefinitions.map(item => [item.key, `示例${item.label}`]),
  );
  exampleValues.issue_date = rule.dateFormat === "YYYY-MM-DD" ? "2025-05-01" : "2025年05月01日";
  exampleValues.amount = "800.00";
  exampleValues.total_amount = "800.00";
  exampleValues.departure_station = "广州南站";
  exampleValues.arrival_station = "北京北站";
  exampleValues.departure_airport = "广州";
  exampleValues.arrival_airport = "北京";
  exampleValues.flight_number = "HU7814";
  exampleValues.seller_name = "北京大小酒店有限公司";

  let folderParts = [];
  if (rule.mode === "template") {
    folderParts = interpolateTemplate(rule.template, config.fieldDefinitions, exampleValues).split("/").filter(Boolean);
  } else {
    folderParts = rule.tokens
      .map(token => {
        if (token.type === "text") return token.value.trim();
        const value = exampleValues[token.value] || "";
        if (!value) return "";
        const label = config.fieldDefinitions.find(item => item.key === token.value)?.label || token.value;
        return rule.showItemPrefix ? `${label}_${value}` : value;
      })
      .filter(Boolean);
  }

  const separator = rule.separator === "/" ? "_" : rule.separator || "_";
  const filename = folderParts.join(separator) || "文件名称";
  splitModalPreview.textContent = `${folderParts.join("/") || "路径片段"}/${filename}.pdf`;
}

function interpolateTemplate(template, fieldDefinitions, valueMap) {
  const labelToKey = Object.fromEntries(fieldDefinitions.map(item => [item.label, item.key]));
  return (template || "").replace(/\{([^}]+)\}/g, (_, label) => valueMap[labelToKey[label] || label] || "");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

syncSplitHero();
renderSplitDocuments();
