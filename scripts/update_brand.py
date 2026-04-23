"""
========================================================================
update_brand.py — Site-wide Brand Update for Classic Baseball World
========================================================================

One-time site update script. Does two things:

1. Adds the WBN logo (top-left of every page nav)
2. Updates brand name from "BASEBALL WITHOUT BORDERS" to
   "OFFICIAL VIEWER'S GUIDE TO INTERNATIONAL BASEBALL GAMES"

USAGE (from wbn-archive root):
    python scripts/update_brand.py

The script walks through every .html file in docs/ and docs/league/,
makes backups (filename.html.bak), then updates the nav section.

Safe to run. If anything goes wrong, restore from .bak files with:
    Get-ChildItem docs -Recurse -Filter *.bak | ForEach-Object {
        Move-Item $_.FullName ($_.FullName -replace '\.bak$','')
    }

========================================================================
"""

import os
import re
import shutil

# Directories to update
TARGETS = ['docs', 'docs/league']

# What we're looking for — the old nav logo line
# Pattern 1: "BASEBALL WITHOUT BORDERS" text
OLD_BRAND = 'BASEBALL WITHOUT BORDERS'
NEW_BRAND = "OFFICIAL VIEWER'S GUIDE TO INTERNATIONAL BASEBALL GAMES"

# New nav HTML that includes the logo
# The LOGO_PATH is the site-relative path — works from any page
def make_new_logo_block(logo_path='/assets/img/wbn-logo.jpg'):
    """Generate the new logo + brand block for the nav."""
    return f'''<a href="/index.html" class="brand-block" style="display:flex;align-items:center;gap:10px;text-decoration:none;">
      <img src="{logo_path}" alt="World Baseball Network" class="wbn-logo" style="height:38px;width:auto;display:block;">
      <span class="logo" style="font-family:var(--display);font-weight:900;font-size:0.75rem;letter-spacing:1px;line-height:1.1;color:var(--text);max-width:180px;">OFFICIAL VIEWER'S GUIDE<br>TO INTERNATIONAL BASEBALL</span>
    </a>'''


# Pattern to match old "<div class="logo">BASEBALL WITHOUT BORDERS</div>" style blocks
OLD_LOGO_PATTERNS = [
    re.compile(r'<div class="logo">BASEBALL WITHOUT BORDERS</div>', re.IGNORECASE),
    re.compile(r'<div class="logo">BASEBALL\s+WITHOUT\s+BORDERS</div>', re.IGNORECASE),
]


def find_html_files():
    """Find all .html files under target directories."""
    files = []
    for target in TARGETS:
        if not os.path.isdir(target):
            print(f"⚠️  Directory not found: {target}")
            continue
        # Non-recursive within each target dir
        for name in os.listdir(target):
            if name.endswith('.html'):
                files.append(os.path.join(target, name))
    return files


def backup_file(filepath):
    """Create a .bak backup if one doesn't already exist."""
    bak = filepath + '.bak'
    if not os.path.exists(bak):
        shutil.copy2(filepath, bak)


def update_file(filepath):
    """Apply logo + brand update to a single HTML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    replaced = False

    # Replace the logo div with new logo block
    new_logo_block = make_new_logo_block()
    for pattern in OLD_LOGO_PATTERNS:
        if pattern.search(content):
            content = pattern.sub(new_logo_block, content)
            replaced = True

    # Also replace any remaining plain-text "BASEBALL WITHOUT BORDERS"
    # (e.g., footer brand, page titles)
    if OLD_BRAND in content:
        content = content.replace(OLD_BRAND, 'OFFICIAL VIEWER\'S GUIDE')
        replaced = True

    if replaced and content != original:
        backup_file(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def main():
    files = find_html_files()
    if not files:
        print("No HTML files found. Are you running from wbn-archive root?")
        return

    print(f"\nFound {len(files)} HTML files to check.\n")

    updated = 0
    skipped = 0
    for f in files:
        try:
            if update_file(f):
                print(f"  ✅ Updated: {f}")
                updated += 1
            else:
                print(f"  ⏭️  Skipped (no match): {f}")
                skipped += 1
        except Exception as e:
            print(f"  ❌ Error on {f}: {e}")

    print(f"\n{'=' * 60}")
    print(f"  Summary: {updated} updated, {skipped} skipped")
    print(f"{'=' * 60}")
    print(f"\n💡 Backups saved as .bak next to each updated file.")
    print(f"   To restore: rename any .bak back to .html")
    print(f"\n🖼️  MAKE SURE the logo file exists at:")
    print(f"   docs/assets/img/wbn-logo.jpg")
    print(f"\n")


if __name__ == '__main__':
    main()
