"""Combined manifest for the two Drive folders, compiled by IRT Corp (irtranscripts.com).

Inputs: rclone lsjson output for each source folder, and the staged local copies.
Counts PowerPoint slides (including converted .ppt) and PDF pages, then writes
MANIFEST.csv and MANIFEST.md into the output directory.
"""
import csv
import datetime as dt
import hashlib
import json
import os
import sys

from pptx import Presentation
from pypdf import PdfReader

DEST = "Construction and management"
ORG = "IRT Corp (irtranscripts.com)"
SOURCES = [
    ("2130 Construction Technology 1", "A"),
    ("Y1S2", "B"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_units(local, ext):
    """Return (count, unit label). Count is None when the file cannot be counted."""
    try:
        if ext == "pptx":
            return len(Presentation(local).slides), "slides"
        if ext == "ppt":
            converted = os.path.splitext(local)[0] + ".pptx"
            if os.path.exists(converted):
                return len(Presentation(converted).slides), "slides (from .ppt)"
            return None, "not converted"
        if ext == "pdf":
            return len(PdfReader(local).pages), "pages"
    except Exception as exc:  # one unreadable file should not stop the manifest
        return None, "error: " + type(exc).__name__
    return None, ""


def main(ls_a, ls_b, stage_root, out_dir):
    rows = []
    for (folder, stage_key), ls_path in zip(SOURCES, [ls_a, ls_b]):
        with open(ls_path, encoding="utf-8") as fh:
            items = json.load(fh)
        for it in sorted(items, key=lambda i: i["Path"]):
            local = os.path.join(stage_root, stage_key, it["Path"])
            ext = it["Name"].rsplit(".", 1)[-1].lower() if "." in it["Name"] else ""
            units, label = None, ""
            digest = ""
            if os.path.exists(local):
                units, label = count_units(local, ext)
                digest = sha256(local)
            rows.append({
                "source_folder": folder,
                "source_path": it["Path"],
                "file_name": it["Name"],
                "type": ext,
                "bytes": it["Size"],
                "mb": round(it["Size"] / 1e6, 3),
                "modified_utc": it.get("ModTime", ""),
                "drive_file_id": it.get("ID", ""),
                "count": "" if units is None else units,
                "count_unit": label,
                "sha256": digest,
                "destination_path": f"{DEST}/{folder}/{it['Path']}",
            })

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "MANIFEST.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def slide_rows(subset):
        return [r for r in subset if r["count"] != "" and r["count_unit"].startswith("slides")]

    def page_rows(subset):
        return [r for r in subset if r["count"] != "" and r["count_unit"] == "pages"]

    total_bytes = sum(r["bytes"] for r in rows)
    slides, pages = slide_rows(rows), page_rows(rows)
    slide_total = sum(int(r["count"]) for r in slides)
    page_total = sum(int(r["count"]) for r in pages)
    type_counts = {}
    for r in rows:
        type_counts[r["type"]] = type_counts.get(r["type"], 0) + 1
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Combined manifest: two Google Drive folders",
        "",
        f"Compiled by **{ORG}** on {generated}.",
        "",
        f"Destination: shintiru Drive, folder **{DEST}**.",
        "",
        "## Totals",
        "",
        f"- Files: **{len(rows)}**",
        "- By type: " + ", ".join(f"{k or 'none'} {v}" for k, v in sorted(type_counts.items())),
        f"- Size: **{total_bytes / 1e6:.1f} MB** ({total_bytes:,} bytes)",
        f"- PowerPoint slides (including converted .ppt): **{slide_total}** across {len(slides)} files",
        f"- PDF pages: **{page_total}** across {len(pages)} files",
        "",
        "## Per folder",
        "",
        "| Folder | Files | Size (MB) | Slides | PDF pages |",
        "|---|---|---|---|---|",
    ]
    for folder, _ in SOURCES:
        fr = [r for r in rows if r["source_folder"] == folder]
        fs = sum(int(r["count"]) for r in slide_rows(fr))
        fp = sum(int(r["count"]) for r in page_rows(fr))
        size_mb = sum(r["bytes"] for r in fr) / 1e6
        lines.append(f"| {folder} | {len(fr)} | {size_mb:.1f} | {fs} | {fp} |")
    lines += [
        "",
        "## Files",
        "",
        "Full detail, including Drive IDs, modified dates and SHA-256 checksums, is in MANIFEST.csv.",
        "",
        "| Folder | File | Type | MB | Slides or pages | Destination |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['source_folder']} | {r['source_path']} | {r['type']} | {r['mb']} | "
                     f"{r['count']} | {r['destination_path']} |")
    with open(os.path.join(out_dir, "MANIFEST.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"files={len(rows)} bytes={total_bytes} slides={slide_total} pdf_pages={page_total}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
