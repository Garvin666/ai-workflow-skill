"""office_io.py - Excel/Word/PDF 读写统一入口（子命令式）。

子命令:
    excel-read   <file.xlsx> [--sheet 名称或序号] [--max-rows N] [--fmt table|json]
    excel-write  <file.xlsx> --rows <json文件|->        # rows=[[...],...], 首行为表头
    word-read    <file.docx> [--max-para N]
    word-write   <file.docx> --text <txt文件|-> [--title 标题]
    pdf-extract  <file.pdf> [--pages 1-3] [--out 文件]  # 缺省打印 stdout
    pdf-merge    <out.pdf> <in1.pdf> <in2.pdf> ...

写文件统一 utf-8-sig（带 BOM，Excel/WPS 直接打开不乱码）；Word 中文指定宋体/微软雅黑。
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def _read_source(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read()
    with open(arg, "r", encoding="utf-8-sig") as f:
        return f.read()


def cmd_excel_read(args) -> None:
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


def cmd_excel_write(args) -> None:
    from copy import copy

    from openpyxl import Workbook

    rows = json.loads(_read_source(args.rows))
    if not rows:
        print("[ERROR] rows 为空", file=sys.stderr)
        raise SystemExit(1)
    wb = Workbook()
    ws = wb.active
    ws.title = args.sheet or "Sheet1"
    for r in rows:
        ws.append(r)
    # 首行加粗（用 copy 模块，openpyxl 3.1 已弃用 font.copy）
    for cell in ws[1]:
        cell.font = copy(cell.font)
        cell.font.bold = True
    wb.save(args.file)
    print(f"[ OK ] 已写入 {args.file}（{len(rows)} 行 x {len(rows[0])} 列）")


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
    p.add_argument("file")
    p.add_argument("--sheet", help="工作表名或序号（缺省 0）")
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--fmt", choices=["table", "json"], default="table")
    p.set_defaults(func=cmd_excel_read)

    p = sub.add_parser("excel-write")
    p.add_argument("file")
    p.add_argument("--rows", required=True, help="JSON 文件路径或 - （stdin）")
    p.add_argument("--sheet", help="工作表名")
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
