"""Markup helpers shared by generators and posting scripts."""

from __future__ import annotations

import html
import re


def _inline_markdown_to_html(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_lines = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("### "):
            html_lines.append(f"<h3>{_inline_markdown_to_html(stripped[4:])}</h3>")
            i += 1
            continue

        if stripped.startswith("## "):
            html_lines.append(f"<h2>{_inline_markdown_to_html(stripped[3:])}</h2>")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").replace(" ", "")) <= {"-", ":"}:
            header_cells = _split_table_row(lines[i])
            body_rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                body_rows.append(_split_table_row(lines[i]))
                i += 1

            html_lines.append("<table>")
            html_lines.append("<thead><tr>" + "".join(f"<th>{_inline_markdown_to_html(cell)}</th>" for cell in header_cells) + "</tr></thead>")
            html_lines.append("<tbody>")
            for row in body_rows:
                html_lines.append("<tr>" + "".join(f"<td>{_inline_markdown_to_html(cell)}</td>" for cell in row) + "</tr>")
            html_lines.append("</tbody>")
            html_lines.append("</table>")
            continue

        if stripped.startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(lines[i].strip()[2:])
                i += 1
            html_lines.append("<ul>")
            for item in items:
                html_lines.append(f"<li>{_inline_markdown_to_html(item)}</li>")
            html_lines.append("</ul>")
            continue

        paragraph_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if not next_line:
                i += 1
                break
            if next_line.startswith(("## ", "### ", "- ", "|")):
                break
            paragraph_lines.append(next_line)
            i += 1
        paragraph_text = " ".join(paragraph_lines)
        html_lines.append(f"<p>{_inline_markdown_to_html(paragraph_text)}</p>")

    return "\n".join(html_lines).strip()
