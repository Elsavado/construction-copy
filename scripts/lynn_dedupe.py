"""Choose which files to copy: skip content already on shintiru, skip repeats inside the run.

Usage: lynn_dedupe.py <shintiru_list.json> <out_dir> <LABEL=list.json> [...]
Writes files_from_<LABEL>.txt (paths to copy, relative to each link) and summary.json.
Files without a Drive MD5 (Google Docs, Sheets, Slides) cannot be compared, so they are skipped and counted.
"""
import json
import os
import sys

shintiru = json.load(open(sys.argv[1], encoding="utf-8"))
out_dir = sys.argv[2]
pairs = [a.split("=", 1) for a in sys.argv[3:]]
os.makedirs(out_dir, exist_ok=True)

existing = set()
for i in shintiru:
    md5 = (i.get("Hashes") or {}).get("md5")
    if md5:
        existing.add(md5)

seen = set()
summary = {}
for label, path in pairs:
    items = json.load(open(path, encoding="utf-8"))
    keep, stats = [], {"listed": len(items), "copy": 0, "skip_already_on_shintiru": 0,
                       "skip_repeat_in_run": 0, "skip_no_hash": 0, "copy_bytes": 0}
    for it in items:
        md5 = (it.get("Hashes") or {}).get("md5")
        if not md5:
            stats["skip_no_hash"] += 1
        elif md5 in existing:
            stats["skip_already_on_shintiru"] += 1
        elif md5 in seen:
            stats["skip_repeat_in_run"] += 1
        else:
            seen.add(md5)
            keep.append(it["Path"])
            stats["copy"] += 1
            stats["copy_bytes"] += max(it.get("Size", 0), 0)
    with open(os.path.join(out_dir, f"files_from_{label}.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(keep) + ("\n" if keep else ""))
    summary[label] = stats

with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=1)
for label, s in summary.items():
    print(label, s)
