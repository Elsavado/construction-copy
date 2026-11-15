"""Choose law-related files for the LAW folder.

Keeps files whose names look like law material (statutes, constitutions, judgments, course
outlines, notes). Leaves out court filings by private parties (plaints, petitions, applications,
motions, affidavits, summons, pleadings). Skips files already on shintiru and repeats in the run.

Usage: law_select.py <shintiru_list.json> <out_dir> <src_label=list.json> [...]
Writes files_from_<label>.txt and summary.json. Only counts are printed.
"""
import json
import os
import re
import sys

LAW = re.compile(r"\blaw|legal|statut|\bact\b|act\d|constitution|court|judg|tribunal|jurisprud|"
                 r"\bcase\b|treaty|convention|criminal|contract|tort|regulation|\bbill\b|ruling|"
                 r"precedent|evidence|procedure|sexual offen", re.I)
FILING = re.compile(r"plaint|petition|affidavit|interrogat|summons|notice of motion|\bmotion\b|"
                    r"application|pleading|complaint|injunction|written statement|defen[cs]e|"
                    r"answer to|attachment before", re.I)

MODE = os.environ.get("MODE", "law")  # "law" = non-filing law material; "filings" = only the filings
shintiru = json.load(open(sys.argv[1], encoding="utf-8"))
out_dir = sys.argv[2]
pairs = [a.split("=", 1) for a in sys.argv[3:]]
os.makedirs(out_dir, exist_ok=True)

existing = {(i.get("Hashes") or {}).get("md5") for i in shintiru}
existing.discard(None)
seen = set()
summary = {}
for label, path in pairs:
    items = json.load(open(path, encoding="utf-8"))
    st = {"listed": len(items), "law_related": 0, "left_out_court_filings": 0, "copy": 0,
          "skip_already_on_shintiru": 0, "skip_repeat": 0, "skip_no_hash": 0, "copy_bytes": 0}
    keep = []
    for it in items:
        name = it["Name"]
        if not LAW.search(name):
            continue
        if FILING.search(name):
            if MODE != "filings":
                st["left_out_court_filings"] += 1
                continue
        elif MODE == "filings":
            continue
        st["law_related"] += 1
        md5 = (it.get("Hashes") or {}).get("md5")
        if not md5:
            st["skip_no_hash"] += 1
        elif md5 in existing:
            st["skip_already_on_shintiru"] += 1
        elif md5 in seen:
            st["skip_repeat"] += 1
        else:
            seen.add(md5)
            keep.append(it["Path"])
            st["copy"] += 1
            st["copy_bytes"] += max(it.get("Size", 0), 0)
    with open(os.path.join(out_dir, f"files_from_{label}.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(keep) + ("\n" if keep else ""))
    summary[label] = st

with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=1)
tot = {k: sum(s[k] for s in summary.values()) for k in next(iter(summary.values()))}
print("TOTAL", tot)
