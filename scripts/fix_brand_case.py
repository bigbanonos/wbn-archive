"""
fix_brand_case.py — Convert brand name from ALL CAPS to Title Case

Fixes the overcorrection from update_brand.py.
Run once, from the wbn-archive root:
    python scripts/fix_brand_case.py
"""

import os

TARGETS = ['docs', 'docs/league']

# What to find → replace with
REPLACEMENTS = [
    # Main brand — the site-wide logo block
    ("OFFICIAL VIEWER'S GUIDE<br>TO INTERNATIONAL BASEBALL",
     "Official Viewer's Guide<br>to International Baseball"),
    # Any remaining all-caps version (already-updated footers, etc.)
    ("OFFICIAL VIEWER'S GUIDE TO INTERNATIONAL BASEBALL GAMES",
     "Official Viewer's Guide to International Baseball Games"),
    ("OFFICIAL VIEWER'S GUIDE",
     "Official Viewer's Guide"),
]


def find_html_files():
    files = []
    for target in TARGETS:
        if not os.path.isdir(target):
            continue
        for name in os.listdir(target):
            if name.endswith('.html'):
                files.append(os.path.join(target, name))
    return files


def update_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    files = find_html_files()
    print(f"\nChecking {len(files)} HTML files...\n")

    updated = 0
    for f in files:
        try:
            if update_file(f):
                print(f"  ✅ Fixed case: {f}")
                updated += 1
        except Exception as e:
            print(f"  ❌ Error on {f}: {e}")

    print(f"\n{'=' * 50}")
    print(f"  Summary: {updated} files corrected to Title Case")
    print(f"{'=' * 50}\n")


if __name__ == '__main__':
    main()
