"""office_io.py - Excel/Word/PDF 读写统一入口（子命令式）。

子命令:
    excel-read   <file.xlsx|file.csv> [--sheet 名称或序号] [--max-rows N] [--fmt table|json]
    excel-write  <file.xlsx> --rows <json文件|-> [--sheet 名称] [--no-format] [--widths 12,20]
    word-read    <file.docx> [--max-para N]
    word-write   <file.docx> --text <txt文件|-> [--title 标题]
    pdf-extract  <file.pdf> [--pages 1-3] [--out 文件]  # 缺省打印 stdout
    pdf-merge    <out.pdf> <in1.pdf> <in2.pdf> ...

excel-write 的 --rows 支持两种 JSON 结构:
    单表: [[...], [...]]                       # 首行为表头
    多表: [{"name": "Sheet1", "rows": [[...]]}, {"name": "Sheet2", "rows": [[...]]}]

写文件统一 utf-8-sig（带 BOM，Excel/WPS 直接打开不乱码）；Word 中文指定宋体/微软雅黑。
默认格式化：表头加粗 + 冻结首行 + 自适应列宽（可用 --no-format 关闭，--widths 手工指定）。
"""
import argparse
import csv
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

MAX_COL_WIDTH = 50


def _read_source(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read()
    with open(arg, "r", encoding="utf-8-sig") as f:
        return f.read()


def _read_csv(path: str, max_rows: int | None) -> list[list[str]]:
    for enc in ("utf-8-sig", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                rows = []
                for i, row in enumerate(csv.reader(f)):
                    if max_rows and i >= max_rows:
                        break
                    rows.append(["" if c is None else str(c) for c in row])
                return rows
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return [list(r) for r in csv.reader(f)]


def cmd_excel_read(args) -> None:
    if str(args.file).lower().endswith(".csv"):
        rows = _read_csv(args.file, args.max_rows)
    else:
        from openpyxl import load_workbook

        wb = load_workbook(args.file, data_only=True, read_only=True)
        if args.sheet is None:
            ws = wb.worksheets[0]
        elif isinstance(args.sheet, str):
            ws = wb[args.sheet]
        else:
            ws = wb[wb.sheetnames[int(args.sheet)]]
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if args.max_rows and i >= args.max_rows:
                break
            rows.append(["" if c is None else str(c) for c in row])
        wb.close()
    if args.fmt == "json":
        print(json.dumps(rows, ensure_ascii=False))
    else:
        for r in rows:
            print("\t".join(r))


def _disp_width(text: str) -> int:
    """中文/全角按 2 列宽估算。"""
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in text)


def _write_sheet(ws, rows: list[list], fmt: bool, widths: list[int] | None) -> None:
    from copy import copy

    for r in rows:
        ws.append(r)
    if not fmt:
        return
    for cell in ws[1]:
        cell.font = copy(cell.font)
        cell.font.bold = True
    ws.freeze_panes = "A2"
    n_cols = max((len(r) for r in rows), default=0)
    for idx in range(1, n_cols + 1):
        if widths:
            w = widths[idx - 1] if idx - 1 < len(widths) else widths[-1]
        else:
            col_letter = ws.cell(row=1, column=idx).column_letter
            w = max((_disp_width(str(c.value)) for c in ws[col_letter] if c.value is not None), default=8) + 2
            w = min(max(w, 8), MAX_COL_WIDTH)
        ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = w


def cmd_excel_write(args) -> None:
    from openpyxl import Workbook

    payload = json.loads(_read_source(args.rows))
    if not payload:
        print("[ERROR] rows 为空", file=sys.stderr)
        raise SystemExit(1)

    widths = [int(x) for x in args.widths.split(",")] if args.widths else None
    wb = Workbook()

    if isinstance(payload[0], dict) and "rows" in payload[0]:  # 多表结构
        sheets = [(str(s.get("name") or f"Sheet{i + 1}"), s.get("rows") or []) for i, s in enumerate(payload)]
        wb.remove(wb.active)
        for name, rows in sheets:
            if not rows:
                print(f"[WARN] 工作表 {name} 无数据，跳过", file=sys.stderr)
                continue
            _write_sheet(wb.create_sheet(title=name[:31]), rows, not args.no_format, widths)
        summary = f"{len(sheets)} 个工作表"
    else:  # 单表结构（向后兼容）
        rows = payload
        ws = wb.active
        ws.title = args.sheet or "Sheet1"
        _write_sheet(ws, rows, not args.no_format, widths)
        summary = f"{len(rows)} 行 x {len(rows[0])} 列"

    wb.save(args.file)
    print(f"[ OK ] 已写入 {args.file}（{summary}，格式化={'关闭' if args.no_format else '开'}）")


def cmd_word_read(args) -> None:
    from docx import Document

    doc = Document(args.file)
    for i, p in enumerate(doc.paragraphs):
        if args.max_para and i >= args.max_para:
            break
        if p.text.strip():
            print(p.text)


def cmd_word_write(args) -> None:
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document()
    text = _read_source(args.text)
    if args.title:
        h = doc.add_heading(args.title, level=1)
        for run in h.runs:
            run.font.name = "微软雅黑"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    for para in [p for p in text.splitlines() if p.strip()]:
        p = doc.add_paragraph(para)
        for run in p.runs:
            run.font.name = "宋体"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    doc.save(args.file)
    print(f"[ OK ] 已写入 {args.file}")


def _parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(total))
    pages = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            pages.extend(range(int(a) - 1, int(b)))
        else:
            pages.append(int(part) - 1)
    return [p for p in pages if 0 <= p < total]


def cmd_pdf_extract(args) -> None:
    from pypdf import PdfReader

    reader = PdfReader(args.file)
    idx = _parse_pages(args.pages, len(reader.pages))
    text = "\n".join(reader.pages[i].extract_text() or "" for i in idx)
    if args.out:
        with open(args.out, "w", encoding="utf-8-sig") as f:
            f.write(text)
        print(f"[ OK ] 已提取 {len(idx)} 页到 {args.out}")
    else:
        print(text)


def cmd_pdf_merge(args) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for src in args.inputs:
        writer.append(src)
    with open(args.out, "wb") as f:
        writer.write(f)
    print(f"[ OK ] 已合并 {len(args.inputs)} 个文件到 {args.out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Office 文件读写统一入口")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("excel-read")
    p.add_argument("file", help=".xlsx 或 .csv")
    p.add_argument("--sheet", help="工作表名或序号（缺省 0；csv 忽略）")
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--fmt", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_excel_read)

    p = sub.add_parser("excel-write")
    p.add_argument("file")
    p.add_argument("--rows", required=True, help="JSON 文件路径或 - （stdin）；支持单表/多表结构")
    p.add_argument("--sheet", help="单表结构时的工作表名")
    p.add_argument("--no-format", action="store_true", help="关闭表头加粗/冻结/自适应列宽")
    p.add_argument("--widths", help="手工列宽，如 12,20,40（末位沿用至其余列）")
    p.set_defaults(func=cmd_excel_write)

    p = sub.add_parser("word-read")
    p.add_argument("file")
    p.add_argument("--max-para", type=int, default=None)
    p.set_defaults(func=cmd_word_read)

    p = sub.add_parser("word-write")
    p.add_argument("file")
    p.add_argument("--text", required=True, help="文本文件路径或 - （stdin）")
    p.add_argument("--title")
    p.set_defaults(func=cmd_word_write)

    p = sub.add_parser("pdf-extract")
    p.add_argument("file")
    p.add_argument("--pages", help="如 1-3,5")
    p.add_argument("--out")
    p.set_defaults(func=cmd_pdf_extract)

    p = sub.add_parser("pdf-merge")
    p.add_argument("out")
    p.add_argument("inputs", nargs="+")
    p.set_defaults(func=cmd_pdf_merge)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
