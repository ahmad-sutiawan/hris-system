#!/usr/bin/env python3
"""Generate MANUAL-BPS-HRIS.pdf from docs/MANUAL-BPS-HRIS.md using ReportLab."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "docs" / "MANUAL-BPS-HRIS.md"
PDF_PATH = ROOT / "docs" / "MANUAL-BPS-HRIS.pdf"

NAVY = colors.HexColor("#140B6E")
ACCENT = colors.HexColor("#3269CC")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#E2E8F0")


def _styles():
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontSize=26,
            leading=32,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub",
            parent=base["Normal"],
            fontSize=13,
            leading=18,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontSize=18,
            leading=24,
            textColor=NAVY,
            spaceBefore=18,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=14,
            leading=18,
            textColor=ACCENT,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontSize=12,
            leading=16,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=4,
        ),
        "quote": ParagraphStyle(
            "Quote",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=12,
            textColor=MUTED,
            spaceAfter=8,
            borderPadding=6,
        ),
        "toc": ParagraphStyle(
            "TOC",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            leftIndent=8,
            spaceAfter=3,
        ),
    }


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _inline(text: str) -> str:
    text = _escape(text.strip())
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier' size='9'>\1</font>", text)
    text = re.sub(r"\[(.+?)\]\(#.+?\)", r"\1", text)
    return text


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and s.count("|") >= 2


def _parse_table_rows(lines: list[str]) -> list[list[str]]:
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in cells):
            continue
        rows.append([_inline(c) for c in cells])
    return rows


def _table_flowable(rows: list[list[str]], styles) -> Table:
    if not rows:
        return Spacer(1, 1)
    col_count = max(len(r) for r in rows)
    normalized = [r + [""] * (col_count - len(r)) for r in rows]
    wrapped = []
    for row in normalized:
        wrapped.append([Paragraph(cell or "—", styles["body"]) for cell in row])
    tbl = Table(wrapped, repeatRows=1, hAlign="LEFT")
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tbl


def _page_break_marker(line: str) -> bool:
    return "page-break-after" in line


def build_story(md_text: str, styles) -> list:
    story = []
    lines = md_text.splitlines()
    i = 0
    in_yaml = False
    skip_toc_block = False

    while i < len(lines):
        line = lines[i]
        raw = line.rstrip()

        if raw.strip() == "---":
            in_yaml = not in_yaml
            i += 1
            continue
        if in_yaml:
            i += 1
            continue
        if _page_break_marker(raw):
            story.append(PageBreak())
            i += 1
            continue
        if not raw.strip():
            story.append(Spacer(1, 4))
            i += 1
            continue

        if raw.startswith("# "):
            title = _inline(raw[2:])
            if title.startswith("BAGIAN "):
                story.append(PageBreak())
                story.append(Paragraph(title, styles["h1"]))
            elif "Manual Book BPS HRIS" in raw:
                story.append(Spacer(1, 35 * mm))
                story.append(Paragraph(title, styles["cover_title"]))
                story.append(Spacer(1, 8 * mm))
                story.append(
                    Paragraph(
                        "Panduan Karyawan (Web &amp; Mobile)<br/>"
                        "Panduan Admin &amp; HR (Web)",
                        styles["cover_sub"],
                    )
                )
                story.append(Spacer(1, 6 * mm))
                story.append(Paragraph("Versi 1.0 · Juni 2026", styles["cover_sub"]))
                story.append(PageBreak())
            else:
                story.append(Paragraph(title, styles["h1"]))
            i += 1
            continue

        if raw.startswith("## "):
            h = _inline(raw[3:])
            if h.startswith("Daftar Isi"):
                skip_toc_block = True
            story.append(Paragraph(h, styles["h2"]))
            i += 1
            continue

        if raw.startswith("### "):
            story.append(Paragraph(_inline(raw[4:]), styles["h3"]))
            i += 1
            continue

        if skip_toc_block and raw.startswith("### Bagian"):
            skip_toc_block = False

        if skip_toc_block and re.match(r"^\d+\.", raw.strip()):
            story.append(Paragraph(_inline(raw.strip()), styles["toc"]))
            i += 1
            continue

        if _is_table_row(raw):
            table_lines = []
            while i < len(lines) and _is_table_row(lines[i]):
                table_lines.append(lines[i])
                i += 1
            rows = _parse_table_rows(table_lines)
            story.append(_table_flowable(rows, styles))
            story.append(Spacer(1, 8))
            continue

        if raw.startswith("> "):
            story.append(Paragraph(_inline(raw[2:]), styles["quote"]))
            i += 1
            continue

        if raw.startswith("- [ ]"):
            story.append(Paragraph(f"☐ {_inline(raw[5:])}", styles["bullet"]))
            i += 1
            continue

        if raw.startswith("- "):
            story.append(Paragraph(f"• {_inline(raw[2:])}", styles["bullet"]))
            i += 1
            continue

        if re.match(r"^\d+\.\s", raw):
            story.append(Paragraph(_inline(raw), styles["bullet"]))
            i += 1
            continue

        if raw.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(_escape(lines[i]))
                i += 1
            i += 1
            code = "<br/>".join(code_lines)
            story.append(
                Paragraph(
                    f"<font face='Courier' size='9' color='#334155'>{code}</font>",
                    styles["quote"],
                )
            )
            continue

        if raw.strip().startswith("<div") or raw.strip().startswith("</div"):
            i += 1
            continue

        story.append(Paragraph(_inline(raw), styles["body"]))
        i += 1

    return story


def generate(md_path: Path = MD_PATH, pdf_path: Path = PDF_PATH) -> Path:
    if not md_path.exists():
        raise FileNotFoundError(md_path)

    styles = _styles()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="Manual Book BPS HRIS",
        author="PT BPS",
    )

    md_text = md_path.read_text(encoding="utf-8")
    story = build_story(md_text, styles)

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 12 * mm, "Manual Book BPS HRIS v1.0 — PT BPS")
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Halaman {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return pdf_path


if __name__ == "__main__":
    out = generate()
    print(f"Generated: {out} ({out.stat().st_size // 1024} KB)")
