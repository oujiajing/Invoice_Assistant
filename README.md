# 发票助手 V1

本项目是一个本地运行的发票文件重命名网页工具，当前支持：

- 发票台账管理
- 常规数电发票
- 铁路电子客票
- 航空电子客票
- 批量上传 `PDF / OFD` 文件
- 自动解析票面字段
- 通过勾选拼接或模板输入设置重命名规则
- 预览新文件名并导出重命名后的压缩包
- 支持导出 Excel 台账，并按票种自定义勾选导出列
- 支持 `全选 / 反选` Excel 导出列

## 启动方式

1. 打开终端并进入项目目录：

```powershell
cd C:\Users\ojj\Desktop\fapiaozhushou
```

2. 安装依赖：

```powershell
python -m pip install -r requirements.txt
```

3. 启动服务：

```powershell
python app.py
```

4. 浏览器访问：

```text
http://127.0.0.1:5050
```

## 当前范围

- 当前已实现“常规数电发票”、“铁路电子客票”和“航空电子客票”
- 新增“发票台账管理”页面，支持混合上传、筛选、详情预览、批量下载与删除
- 支持本地网页运行，不做公网部署
- 导出为重命名后的 ZIP，不直接覆盖原始文件
- Excel 导出固定保留 `原文件名`，其余为用户勾选的票面字段列
- OFD 仅覆盖文本可提取的常见场景，不包含 OCR 扫描件增强
- 航空电子客票已支持两类常见机票发票版式

## 目录说明

- `app.py`：Flask 入口与 API
- `invoice_helper/railway.py`：铁路电子客票解析与重命名规则
- `invoice_helper/general_invoice.py`：常规数电发票解析与重命名规则
- `invoice_helper/airline_invoice.py`：航空电子客票解析与重命名规则
- `templates/index.html`：页面结构
- `static/styles.css`：页面样式
- `static/app.js`：前端交互逻辑
- `tests/`：解析器、规则与 API 测试

## 测试

```powershell
python -m pytest -q
```
