#!/usr/bin/env python3
"""
SNI Spoofing RAR Downloader & Reporter
Downloads the tool from the provided URL, extracts it, and reports its contents.
Requires: unrar (system), rarfile (Python)
Install on Termux: pkg install unrar && pip install rarfile
Usage: python3 sniff_download_and_report.py
"""

import os, sys, urllib.request, rarfile
from pathlib import Path

# ── Configuration ──────────────────────────────────
RAR_URL = "https://tools.irbots.com/uploads/1779215034file_16854.rar"
DOWNLOAD_FILENAME = "sniff_tool.rar"
EXTRACT_DIR = "sniff_extracted"

# ── Helper functions ───────────────────────────────
def download_file(url, dest):
    print(f"⬇️  Downloading {url} ...")
    try:
        urllib.request.urlretrieve(url, dest)
        size = Path(dest).stat().st_size
        print(f"✅ Downloaded {size:,} bytes to {dest}")
        return True
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return False

def extract_and_report(rar_path, extract_dir):
    if not Path(rar_path).exists():
        print(f"❌ RAR file not found: {rar_path}")
        return False

    try:
        rf = rarfile.RarFile(rar_path)
    except rarfile.BadRarFile:
        print("❌ The file is not a valid RAR archive.")
        return False
    except Exception as e:
        print(f"❌ Cannot open RAR: {e}")
        return False

    print("\n📄 Archive contents:\n")
    for f in rf.infolist():
        type_str = "<DIR>" if f.isdir() else "FILE"
        print(f"  {type_str:6}  {f.filename:40}  {f.file_size:>10,} bytes")

    # Extract
    out_path = Path(extract_dir)
    out_path.mkdir(exist_ok=True)
    rf.extractall(out_path)
    print(f"\n📁 Extracted to {out_path.resolve()}")

    # Scan for interesting files
    print("\n🔍 Scanning for configuration / script files...")
    interesting = []
    for root, dirs, files in os.walk(out_path):
        for file in files:
            full = Path(root) / file
            ext = full.suffix.lower()
            if ext in ('.json', '.bat', '.ps1', '.txt', '.ini', '.conf', '.yaml', '.yml',
                       '.xml', '.config', '.cfg', '.log', '.dat', '.bin'):
                interesting.append(full)
    if interesting:
        print(f"Found {len(interesting)} potentially interesting files:")
        for f in interesting:
            rel = f.relative_to(out_path)
            print(f"\n  📝 {rel}")
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                    lines = fh.readlines()
                    for line in lines[:10]:
                        print(f"      {line.rstrip()}")
                    if len(lines) > 10:
                        print(f"      ... ({len(lines)} lines total)")
            except Exception:
                # binary file
                print("      (binary file – showing size)")
    else:
        print("No obvious config/script files found (check the extracted folder manually).")

    return True

def main():
    print("🛠️  SNI Spoofing RAR Downloader & Reporter\n")

    # Download
    if not download_file(RAR_URL, DOWNLOAD_FILENAME):
        sys.exit(1)

    # Extract & report
    if not extract_and_report(DOWNLOAD_FILENAME, EXTRACT_DIR):
        sys.exit(1)

    print("\n✅ Done. Review the extracted folder for the SNI Spoofing executable and configs.")

if __name__ == "__main__":
    main()
