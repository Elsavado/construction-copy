"""Manifest for one Drive folder: counts PowerPoint slides and PDF pages, writes MANIFEST.csv and MANIFEST.md.

Usage: manifest_any.py <staged_dir> <lsjson_file> <folder_label> <destination_path> <out_dir>
Compiled by IRT Corp (irtranscripts.com).
"""
import csv
import datetime as dt
import hashlib
import json
import os
import sys

from pptx import Presentation
from pypdf import PdfReader

ORG = "IRT Corp (irtranscripts.com)"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_units(local, ext):
    try:
        if ext == "pptx":
            return len(Presentation(local).slides), "slides"
        if ext == "pdf":
            return len(PdfReader(local).pages), "pages"
    except Exception as exc:  # keep the manifest complete if one file is unreadable
        return None, "error: " + type(exc).__name__
    return None, ""


def main(stage_dir, ls_path, label, dest, out_dir):
    with open(ls_path, encoding="utf-8") as fh:
        items = json.load(fh)
    rows = []
    for it in sorted(items, key=lambda i: i["Path"]):
        local = os.path.join(stage_dir, it["Path"])
        ext = it["Name"].rsplit(".", 1)[-1].lower() if "." in it["Name"] else ""
        units, unit_label, digest = None, "", ""
        if os.path.exists(local):
            units, unit_label = count_units(local, ext)
            digest = sha256(local)
        rows.append({
            "file_path": it["Path"], "type": ext, "bytes": it["Size"],
            "mb": round(it["Size"] / 1e6, 3), "modified_utc": it.get("ModTime", ""),
            "drive_file_id": it.get("ID", ""),
            "count": "" if units is None else units, "count_unit": unit_label,
            "sha256": digest, "destination_path": f"{dest}/{it['Path']}",
        })

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "MANIFEST.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    total_bytes = sum(r["bytes"] for r in rows)
    slides = [r for r in rows if r["count_unit"] == "slides"]
    pages = [r for r in rows if r["count_unit"] == "pages"]
    slide_total = sum(int(r["count"]) for r in slides)
    page_total = sum(int(r["count"]) for r in pages)
    type_counts = {}
    for r in rows:
        type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Manifest: {label}",
        "",
        f"Compiled by **{ORG}** on {generated}.",
        "",
        f"Destination: shintiru Drive, folder **{dest}**.",
        "",
        "## Totals",
        "",
        f"- Files: **{len(rows)}**",
        "- By type: " + ", ".join(f"{k or 'none'} {v}" for k, v in sorted(type_counts.items())),
        f"- Size: **{total_bytes / 1e6:.1f} MB** ({total_bytes:,} bytes)",
        f"- PowerPoint slides: **{slide_total}** across {len(slides)} files",
        f"- PDF pages: **{page_total}** across {len(pages)} files",
        f"- Word documents (.doc/.docx) and other files are counted as files only, not pages.",
        "",
        "## Files",
        "",
        "Full detail, including Drive IDs, modified dates and SHA-256 checksums, is in MANIFEST.csv.",
        "",
        "| File | Type | MB | Slides or pages | Destination |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['file_path']} | {r['type']} | {r['mb']} | {r['count']} | {r['destination_path']} |")
    with open(os.path.join(out_dir, "MANIFEST.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"files={len(rows)} bytes={total_bytes} slides={slide_total} pdf_pages={page_total}")


if __name__ == "__main__":
    main(*sys.argv[1:6])
