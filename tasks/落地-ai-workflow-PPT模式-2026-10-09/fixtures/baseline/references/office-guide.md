# Office 文件读写避坑指南

openpyxl / python-docx / pypdf 三个库的常见坑。按需 grep 本文件相应小节。

## openpyxl（Excel）

- 读公式文件用 `load_workbook(path, data_only=True)` 才拿到计算值；`data_only=False` 拿到公式串。文件若从未被 Excel 打开计算过，data_only 返回 None
- `read_only=True` 大文件省内存，但只能顺序迭代一次
- 单元格空值是 `None` 不是空串；写 JSON 行数据时先转换
- 写文件 `wb.save()` 后才能读到；同名文件被 Excel 占用会 PermissionError，先让用户关闭
- 日期列读出来是 datetime，转字符串注意格式化，避免序列化报错

## python-docx（Word）

- 中文字体必须设两层：`run.font.name = "宋体"` 且 `run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")`，只设前者对中文无效
- Heading 样式的字号由模板控制，改字号要覆盖 style 或直接设 run.font.size
- 读表格：`doc.tables[i].rows[j].cells[k].text`；合并单元格会重复返回相同文本，需去重
- 页眉页脚正文遍历不到，在 `doc.sections[i].header` 下

## pypdf（PDF）

- `extract_text()` 对扫描件返回空串——扫描件需 OCR（超出本 skill，向用户说明）
- 中文 PDF 提取可能出现乱码/缺字，属字体嵌入问题；换 `pdfplumber`（需另装）常可解决
- 页码从 0 起；`--pages 1-3` 在脚本内已转为 0 起索引
- 合并用 `PdfWriter.append()`，能保留书签；`merge()` 需自己处理位置

## 编码与 Windows

- 所有文本输出/写文件用 UTF-8；写文件加 BOM（`utf-8-sig`）保证 Excel/WPS 双击打开不乱码
- cmd 控制台默认 GBK：脚本内已 `sys.stdout.reconfigure(encoding="utf-8")`；仍乱码则 `chcp 65001`
- PowerShell 调用带空格路径必须加引号并用 `&` 运算符
