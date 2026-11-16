"""Download a Zenodo record's files, verify MD5 checksums, and write an attribution file.

Usage: zenodo_fetch.py <record_id> <out_dir>
Only for records whose licence is checked in this script (CC BY 4.0 here).
"""
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request

ALLOWED_LICENCES = {"cc-by-4.0", "cc0-1.0"}

record_id, out_dir = sys.argv[1], sys.argv[2]
os.makedirs(out_dir, exist_ok=True)

with urllib.request.urlopen(f"https://zenodo.org/api/records/{record_id}", timeout=120) as r:
    record = json.load(r)

licence = (record.get("metadata", {}).get("license", {}) or {}).get("id", "")
if licence not in ALLOWED_LICENCES:
    raise SystemExit(f"record {record_id} licence '{licence}' is not on the allowed list; not copied")

title = record["metadata"].get("title", "")
doi = record.get("doi", "")
files = record.get("files", [])
if not files:
    raise SystemExit("no files in record")

for f in files:
    name = f["key"]
    url = f["links"]["self"]
    expected_md5 = f["checksum"].split(":", 1)[-1]
    dest = os.path.join(out_dir, name)
    print(f"downloading {name} ({f.get('size', 0):,} bytes)")
    h = hashlib.md5()
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
            h.update(chunk)
    if h.hexdigest() != expected_md5:
        raise SystemExit(f"checksum mismatch for {name}: {h.hexdigest()} != {expected_md5}")
    print(f"  md5 ok {h.hexdigest()}")

stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
with open(os.path.join(out_dir, "ATTRIBUTION.txt"), "w", encoding="utf-8") as fh:
    fh.write(f"Title: {title}\n")
    fh.write(f"DOI: {doi}\n")
    fh.write(f"Source: {record.get('links', {}).get('self_html', '')}\n")
    fh.write(f"Licence: {licence} (Creative Commons Attribution 4.0 International)\n")
    fh.write("Licence text: https://creativecommons.org/licenses/by/4.0/\n")
    fh.write(f"Copied to shintiru Drive: {stamp}. Files verified against Zenodo MD5 checksums.\n")
    fh.write("Attribution: cite the title and DOI above when using this material.\n")
print("done:", title)
