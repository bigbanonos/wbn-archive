"""
WBC Pantheon Generator
======================
Reads wbc_pantheon_master.csv and produces:
  1. One HTML page per team-tournament combination
     -> output: docs/wbc-rosters/{country-slug}-{year}.html
  2. A master explorer page with filters across all teams/players
     -> output: docs/wbc-rosters/index.html

Usage:
  python3 generate.py

Output files go to: ./output/
Then copy to: wbn-archive/docs/wbc-rosters/
"""

import csv
import os
import re
from collections import defaultdict
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
CSV_PATH = Path(__file__).parent / "wbc_pantheon_master.csv"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# WBN brand
NAVY = "#0a0f1e"
NAVY2 = "#0f172a"
GOLD = "#f5c842"
NEON = "#00ff9d"
ACCENT = "#D50032"
WHITE = "#f0f4ff"
MUTED = "#8899bb"

# ============================================================
# UTILS
# ============================================================
def slugify(text):
    """Turn 'South Korea' into 'south-korea'."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def safe(value, default=""):
    """Return value if non-empty, else default."""
    return value if value else default

def fmt_stat(val, suffix=""):
    """Format stat value, return em-dash if empty."""
    if not val or val.strip() == "":
        return "&mdash;"
    return f"{val}{suffix}"

def br_url(player):
    """Build Baseball Reference URL from br_id."""
    bid = player.get('br_id', '').strip()
    if not bid:
        return ""
    first_letter = bid[0].lower()
    return f"https://www.baseball-reference.com/players/{first_letter}/{bid}.shtml"

def youtube_url(player):
    """Build YouTube highlight search URL."""
    name = player['player_name']
    tournament = player['tournament']
    query = f"{name} {tournament} highlights".replace(" ", "+")
    return f"https://www.youtube.com/results?search_query={query}"

# ============================================================
# READ CSV
# ============================================================
def read_csv():
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

# ============================================================
# GROUP PLAYERS BY TEAM
# ============================================================
def group_by_team(players):
    """Returns dict of team_key -> {meta, players}."""
    teams = defaultdict(lambda: {'meta': {}, 'players': []})

    for p in players:
        # team_key like "WBC 2026 Venezuela"
        key = f"{p['tournament']}-{slugify(p['team_country'])}"
        teams[key]['meta'] = {
            'tournament': p['tournament'],
            'country': p['team_country'],
            'country_code': p['team_country_code'],
            'finish': p['team_finish'],
            'pool': p['team_pool'],
            'color': p['team_color_hex'] or '#888888',
            'color2': p['team_color2_hex'] or '#888888',
        }
        teams[key]['players'].append(p)

    # Sort players within each team: hitters first by role, then pitchers by role
    role_priority = {
        'MVP': 0, 'Captain': 1, 'Star': 2, 'Ace': 3, 'Closer': 4,
        '': 99, 'Manager': 100
    }
    for key, team in teams.items():
        team['players'].sort(key=lambda p: (
            0 if p['position_group'] == 'Hitter' else 1,
            role_priority.get(p.get('player_role', ''), 50),
            p['player_name']
        ))
    return teams

# ============================================================
# RENDER PLAYER CARD
# ============================================================
def player_card(p, team_color):
    """Render a single player card HTML."""
    name = p['player_name']
    role = p.get('player_role', '').strip()
    position = p.get('position', '')
    bats = p.get('bats', '')
    throws = p.get('throws', '')
    height = p.get('height', '')
    weight = p.get('weight', '')
    born = p.get('born_year', '')
    birthplace = p.get('birthplace', '').replace('"', '')
    mlb_aff = p.get('mlb_affiliation', '').replace('"', '')
    domestic = p.get('domestic_league', '')
    note = p.get('key_stat_note', '').replace('"', '')

    is_pitcher = p['position_group'] == 'Pitcher'

    # Stat block
    if is_pitcher:
        stats = [
            ('ERA', fmt_stat(p.get('era', ''))),
            ('IP', fmt_stat(p.get('ip', ''))),
            ('K', fmt_stat(p.get('k', ''))),
            ('SV' if p.get('saves') else 'K/9',
             fmt_stat(p.get('saves')) if p.get('saves') else fmt_stat(p.get('k9'))),
        ]
    else:
        stats = [
            ('BA', fmt_stat(p.get('ba', ''))),
            ('HR', fmt_stat(p.get('hr', ''))),
            ('RBI', fmt_stat(p.get('rbi', ''))),
            ('OPS', fmt_stat(p.get('ops', ''))),
        ]

    # Role badge
    role_badge = ""
    if role:
        role_color = {
            'MVP': GOLD, 'Captain': WHITE, 'Star': NEON,
            'Ace': NEON, 'Closer': ACCENT, 'Manager': GOLD,
            'Final HR': ACCENT
        }.get(role, MUTED)
        role_badge = f'<span style="background:{role_color};color:{NAVY};font-family:Arial,sans-serif;font-size:.62rem;font-weight:900;letter-spacing:1.5px;padding:3px 8px;border-radius:3px;text-transform:uppercase;margin-left:8px;vertical-align:middle;">{role}</span>'

    bru = br_url(p)
    yt = youtube_url(p)

    # Build bio line
    bio_parts = []
    if position: bio_parts.append(f'<strong style="color:{WHITE};">{position}</strong>')
    if bats and throws: bio_parts.append(f'B/T: {bats}/{throws}')
    if height: bio_parts.append(height)
    if weight: bio_parts.append(f'{weight} lbs')
    if born: bio_parts.append(f'b. {born}')
    bio_line = ' &middot; '.join(bio_parts)

    aff_parts = []
    if birthplace: aff_parts.append(birthplace)
    if mlb_aff and mlb_aff != domestic: aff_parts.append(mlb_aff)
    if domestic and domestic != 'MLB': aff_parts.append(domestic)
    aff_line = ' &middot; '.join(aff_parts) if aff_parts else ''

    stat_grid = ''.join(
        f'<div style="text-align:center;padding:8px 4px;background:rgba(15,23,42,.5);border-radius:4px;">'
        f'<div style="font-family:Arial,sans-serif;font-weight:900;font-size:1.05rem;color:{WHITE};line-height:1;">{val}</div>'
        f'<div style="font-family:\'Courier New\',monospace;font-size:.6rem;color:{MUTED};letter-spacing:1.5px;text-transform:uppercase;margin-top:3px;">{lbl}</div>'
        f'</div>'
        for lbl, val in stats
    )

    links = ''
    if bru:
        links += f'<a href="{bru}" target="_blank" rel="noopener" style="font-family:\'Courier New\',monospace;font-size:.65rem;color:{NEON};letter-spacing:1px;text-transform:uppercase;text-decoration:none;border:1px solid rgba(0,255,157,.3);padding:4px 8px;border-radius:3px;display:inline-block;margin-right:6px;">BR &rarr;</a>'
    links += f'<a href="{yt}" target="_blank" rel="noopener" style="font-family:\'Courier New\',monospace;font-size:.65rem;color:{ACCENT};letter-spacing:1px;text-transform:uppercase;text-decoration:none;border:1px solid rgba(213,0,50,.3);padding:4px 8px;border-radius:3px;display:inline-block;">Highlights &rarr;</a>'

    return f'''<div class="player-card" data-name="{name.lower()}" data-position-group="{p['position_group'].lower()}" data-role="{role.lower()}" style="background:#111827;border:1px solid #1e2d4a;border-top:4px solid {team_color};border-radius:8px;padding:18px 18px 16px;display:flex;flex-direction:column;gap:10px;">
  <div>
    <div style="font-family:Arial,sans-serif;font-size:1.15rem;font-weight:900;color:{WHITE};line-height:1.15;">
      {name}{role_badge}
    </div>
    <div style="font-family:'Courier New',monospace;font-size:.7rem;color:{MUTED};margin-top:4px;letter-spacing:.3px;">
      {bio_line}
    </div>
    {f'<div style="font-family:Georgia,serif;font-size:.78rem;font-style:italic;color:{MUTED};margin-top:5px;">{aff_line}</div>' if aff_line else ''}
  </div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">
    {stat_grid}
  </div>
  {f'<div style="font-family:Georgia,serif;font-size:.82rem;color:{MUTED};line-height:1.5;font-style:italic;border-top:1px solid #1e2d4a;padding-top:10px;">{note}</div>' if note else ''}
  <div style="margin-top:auto;padding-top:8px;">{links}</div>
</div>'''

# ============================================================
# RENDER TEAM PAGE
# ============================================================
def render_team_page(team_key, team_data):
    meta = team_data['meta']
    players = team_data['players']
    color = meta['color']
    color2 = meta['color2']

    hitters = [p for p in players if p['position_group'] == 'Hitter']
    pitchers = [p for p in players if p['position_group'] == 'Pitcher']

    finish_label = {
        'Champion': '&#127942; CHAMPIONS',
        'Runner-up': '&#127939; RUNNER-UP',
        'Semifinalist': 'SEMIFINALIST',
        'Quarterfinalist': 'QUARTERFINALIST',
        'Pool Stage': 'POOL STAGE'
    }.get(meta['finish'], meta['finish'].upper())

    finish_color = {
        'Champion': GOLD,
        'Runner-up': '#c0c0c0',
        'Semifinalist': NEON,
        'Quarterfinalist': '#cd7f32',
    }.get(meta['finish'], MUTED)

    title = f"{meta['country']} {meta['tournament']} Roster"

    cards_hitters = '\n'.join(player_card(p, color) for p in hitters)
    cards_pitchers = '\n'.join(player_card(p, color) for p in pitchers)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | WBC Roster Explorer | World Baseball Network</title>
  <meta name="description" content="Complete {meta['country']} roster from the {meta['tournament']}. {len(players)} players including {len(hitters)} hitters and {len(pitchers)} pitchers. Stats, key contributors, Baseball Reference links.">
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,400;0,700;0,900;1,700;1,900&family=IBM+Plex+Mono:wght@400;500;700&family=Lora:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:{NAVY};color:{WHITE};font-family:'Lora',serif;font-size:15px;line-height:1.65;}}
    a{{text-decoration:none;color:inherit;}}
    .site-nav{{background:{NAVY2};border-bottom:1px solid #1e2d4a;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;position:sticky;top:0;z-index:100;}}
    .nav-brand{{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:.85rem;letter-spacing:1px;text-transform:uppercase;color:{WHITE};}}
    .nav-brand .neon{{color:{NEON};}}
    .nav-pill{{font-family:'Barlow Condensed',sans-serif;font-size:.7rem;font-weight:700;letter-spacing:1px;padding:4px 12px;border-radius:20px;border:1px solid #263354;color:{MUTED};text-transform:uppercase;}}
    .nav-pill:hover{{color:{WHITE};border-color:{WHITE};}}
    .nav-pill.active{{color:{GOLD};border-color:{GOLD};}}
    .hero{{padding:48px 24px 40px;border-bottom:4px solid {color};background:linear-gradient(135deg,{NAVY} 0%,#1a0a1f 100%);position:relative;overflow:hidden;}}
    .hero::before{{content:'';position:absolute;inset:0;background:linear-gradient(90deg,{color} 0%,transparent 8%);opacity:.15;}}
    .hero-inner{{max-width:1400px;margin:0 auto;position:relative;z-index:1;}}
    .breadcrumb{{font-family:'IBM Plex Mono',monospace;font-size:.7rem;color:{MUTED};letter-spacing:1.5px;text-transform:uppercase;margin-bottom:18px;}}
    .breadcrumb a{{color:{NEON};}}
    .hero h1{{font-family:'Barlow Condensed',sans-serif;font-size:clamp(3rem,8vw,6rem);font-weight:900;font-style:italic;letter-spacing:-2px;text-transform:uppercase;line-height:.9;margin-bottom:14px;}}
    .hero h1 .country{{color:{color};display:block;}}
    .finish-badge{{display:inline-block;background:{finish_color};color:{NAVY};font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:.85rem;letter-spacing:3px;padding:6px 16px;border-radius:4px;margin-bottom:18px;}}
    .pool-tag{{font-family:'Barlow Condensed',sans-serif;font-size:.75rem;font-weight:700;letter-spacing:2px;color:{MUTED};text-transform:uppercase;margin-left:14px;}}
    .meta-row{{display:flex;gap:36px;flex-wrap:wrap;margin-top:24px;padding-top:20px;border-top:1px solid #263354;}}
    .meta-item{{font-family:'IBM Plex Mono',monospace;font-size:.75rem;color:{MUTED};}}
    .meta-item strong{{display:block;font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:1.4rem;color:{NEON};letter-spacing:0;text-transform:uppercase;margin-bottom:4px;}}
    .filter-bar{{background:{NAVY2};border-bottom:1px solid #1e2d4a;padding:18px 24px;position:sticky;top:50px;z-index:90;}}
    .filter-inner{{max-width:1400px;margin:0 auto;display:flex;gap:14px;flex-wrap:wrap;align-items:center;}}
    .filter-label{{font-family:'Barlow Condensed',sans-serif;font-size:.7rem;font-weight:900;letter-spacing:2px;color:{GOLD};text-transform:uppercase;margin-right:6px;}}
    .filter-chip{{font-family:'Barlow Condensed',sans-serif;font-size:.72rem;font-weight:700;letter-spacing:1px;padding:5px 12px;border-radius:4px;border:1px solid #263354;background:#111827;color:{MUTED};text-transform:uppercase;cursor:pointer;}}
    .filter-chip.active{{background:{NEON};color:{NAVY};border-color:{NEON};}}
    .search-box{{margin-left:auto;background:#111827;border:1px solid #263354;border-radius:4px;padding:6px 12px;color:{WHITE};font-family:'Lora',serif;font-size:.85rem;width:200px;}}
    .roster-section{{padding:36px 24px;}}
    .roster-section.alt{{background:{NAVY2};}}
    .section-inner{{max-width:1400px;margin:0 auto;}}
    .section-head{{display:flex;align-items:baseline;gap:14px;border-bottom:2px solid #263354;padding-bottom:12px;margin-bottom:22px;flex-wrap:wrap;}}
    .section-title{{font-family:'Barlow Condensed',sans-serif;font-size:2rem;font-weight:900;font-style:italic;letter-spacing:-1px;text-transform:uppercase;line-height:1;}}
    .section-count{{font-family:'IBM Plex Mono',monospace;font-size:.78rem;color:{MUTED};letter-spacing:1px;}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:14px;}}
    .player-card.hidden{{display:none !important;}}
    .footer{{border-top:3px solid {GOLD};padding:36px 24px;background:{NAVY2};}}
    .footer-inner{{max-width:1400px;margin:0 auto;font-family:'IBM Plex Mono',monospace;font-size:.75rem;color:{MUTED};}}
    .footer-inner a{{color:{NEON};}}
    @media(max-width:700px){{.site-nav,.filter-bar{{position:static;}}}}
  </style>
</head>
<body>

<nav class="site-nav">
  <div class="nav-brand">Official Viewer's Guide<br><span class="neon">to International Baseball</span></div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;">
    <a href="/index.html" class="nav-pill">Home</a>
    <a href="/leagues.html" class="nav-pill">Leagues</a>
    <a href="/calendar.html" class="nav-pill">Calendar</a>
    <a href="/wbc-rosters/index.html" class="nav-pill active">WBC Rosters</a>
    <a href="/wbc2026.html" class="nav-pill">WBC 2026</a>
  </div>
</nav>

<div class="hero">
  <div class="hero-inner">
    <div class="breadcrumb">
      <a href="/wbc-rosters/index.html">WBC Roster Explorer</a> &middot; {meta['tournament']} &middot; {meta['country']}
    </div>
    <div class="finish-badge">{finish_label}</div>
    <span class="pool-tag">Pool {meta['pool']}</span>
    <h1>
      <span class="country">{meta['country']}</span>
      <span style="display:block;font-size:.4em;letter-spacing:4px;color:{MUTED};font-style:normal;font-weight:700;margin-top:14px;">
        {meta['tournament']} ROSTER
      </span>
    </h1>
    <div class="meta-row">
      <div class="meta-item"><strong>{len(players)}</strong>TOTAL PLAYERS</div>
      <div class="meta-item"><strong>{len(hitters)}</strong>HITTERS</div>
      <div class="meta-item"><strong>{len(pitchers)}</strong>PITCHERS</div>
      <div class="meta-item"><strong>POOL {meta['pool']}</strong>BRACKET</div>
    </div>
  </div>
</div>

<div class="filter-bar">
  <div class="filter-inner">
    <span class="filter-label">Filter</span>
    <button class="filter-chip active" data-filter="all">All</button>
    <button class="filter-chip" data-filter="hitter">Hitters</button>
    <button class="filter-chip" data-filter="pitcher">Pitchers</button>
    <button class="filter-chip" data-filter="mvp">MVP</button>
    <button class="filter-chip" data-filter="captain">Captain</button>
    <button class="filter-chip" data-filter="star">Stars</button>
    <button class="filter-chip" data-filter="ace">Aces</button>
    <button class="filter-chip" data-filter="closer">Closers</button>
    <input type="text" class="search-box" id="searchBox" placeholder="Search by name...">
  </div>
</div>

<div class="roster-section">
  <div class="section-inner">
    <div class="section-head">
      <h2 class="section-title">Hitters</h2>
      <span class="section-count">{len(hitters)} players</span>
    </div>
    <div class="grid">
      {cards_hitters}
    </div>
  </div>
</div>

<div class="roster-section alt">
  <div class="section-inner">
    <div class="section-head">
      <h2 class="section-title">Pitchers</h2>
      <span class="section-count">{len(pitchers)} players</span>
    </div>
    <div class="grid">
      {cards_pitchers}
    </div>
  </div>
</div>

<div class="footer">
  <div class="footer-inner">
    <strong style="color:{WHITE};font-family:'Barlow Condensed',sans-serif;font-size:1rem;letter-spacing:1px;text-transform:uppercase;">WBC Roster Explorer</strong> &middot;
    A publication of <a href="https://worldbaseball.com">World Baseball Network</a> &middot;
    <a href="/wbc-rosters/index.html">Browse all teams</a>
  </div>
</div>

<script>
const cards = document.querySelectorAll('.player-card');
const chips = document.querySelectorAll('.filter-chip');
const searchBox = document.getElementById('searchBox');
let activeFilter = 'all';

function applyFilter() {{
  const search = searchBox.value.toLowerCase().trim();
  cards.forEach(card => {{
    const name = card.dataset.name;
    const group = card.dataset.positionGroup;
    const role = card.dataset.role;
    let visible = true;
    if (activeFilter !== 'all') {{
      if (activeFilter === 'hitter' || activeFilter === 'pitcher') {{
        visible = (group === activeFilter);
      }} else {{
        visible = (role === activeFilter);
      }}
    }}
    if (visible && search) {{
      visible = name.includes(search);
    }}
    card.classList.toggle('hidden', !visible);
  }});
}}

chips.forEach(chip => chip.addEventListener('click', () => {{
  chips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeFilter = chip.dataset.filter;
  applyFilter();
}}));

searchBox.addEventListener('input', applyFilter);
</script>

</body>
</html>'''
    return html

# ============================================================
# RENDER MASTER INDEX PAGE
# ============================================================
def render_index(teams_dict):
    """Master WBC Roster Explorer index with all teams."""
    teams_list = sorted(teams_dict.items(), key=lambda x: (
        x[1]['meta']['tournament'],
        {'Champion': 0, 'Runner-up': 1, 'Semifinalist': 2, 'Quarterfinalist': 3, 'Pool Stage': 4}.get(x[1]['meta']['finish'], 99),
        x[1]['meta']['country']
    ))

    total_players = sum(len(t['players']) for _, t in teams_list)

    cards = []
    for key, team in teams_list:
        m = team['meta']
        n_hitters = sum(1 for p in team['players'] if p['position_group'] == 'Hitter')
        n_pitchers = sum(1 for p in team['players'] if p['position_group'] == 'Pitcher')
        slug = slugify(m['country']) + "-" + m['tournament'].split()[-1]

        finish_color = {
            'Champion': GOLD, 'Runner-up': '#c0c0c0',
            'Semifinalist': NEON, 'Quarterfinalist': '#cd7f32',
        }.get(m['finish'], MUTED)

        cards.append(f'''<a href="/wbc-rosters/{slug}.html" class="team-card" data-tournament="{m['tournament']}" data-finish="{m['finish'].lower()}" data-country="{m['country'].lower()}" style="background:#111827;border:1px solid #1e2d4a;border-top:5px solid {m['color']};border-radius:10px;padding:22px 22px 18px;display:flex;flex-direction:column;gap:10px;text-decoration:none;color:inherit;transition:.2s;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:1.7rem;font-weight:900;font-style:italic;letter-spacing:-.5px;line-height:1;color:{m['color']};text-transform:uppercase;">{m['country']}</div>
    <span style="background:{finish_color};color:{NAVY};font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:.62rem;letter-spacing:1.5px;padding:3px 8px;border-radius:3px;text-transform:uppercase;">{m['finish']}</span>
  </div>
  <div style="font-family:'IBM Plex Mono',monospace;font-size:.7rem;color:{MUTED};letter-spacing:1px;text-transform:uppercase;">{m['tournament']} &middot; Pool {m['pool']}</div>
  <div style="display:flex;gap:14px;font-family:'IBM Plex Mono',monospace;font-size:.72rem;color:{MUTED};margin-top:6px;border-top:1px solid #1e2d4a;padding-top:10px;">
    <span><strong style="color:{WHITE};font-family:'Barlow Condensed',sans-serif;font-size:1.05rem;display:block;">{len(team['players'])}</strong>PLAYERS</span>
    <span><strong style="color:{WHITE};font-family:'Barlow Condensed',sans-serif;font-size:1.05rem;display:block;">{n_hitters}</strong>HITTERS</span>
    <span><strong style="color:{WHITE};font-family:'Barlow Condensed',sans-serif;font-size:1.05rem;display:block;">{n_pitchers}</strong>PITCHERS</span>
  </div>
  <div style="margin-top:auto;padding-top:8px;font-family:'Barlow Condensed',sans-serif;font-size:.7rem;font-weight:700;letter-spacing:1.5px;color:{NEON};text-transform:uppercase;">View Roster &rarr;</div>
</a>''')

    cards_html = '\n'.join(cards)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WBC Roster Explorer | World Baseball Network</title>
  <meta name="description" content="Complete rosters from every team at the World Baseball Classic. {total_players} players across {len(teams_list)} teams. The definitive WBC pantheon by World Baseball Network.">
  <link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,400;0,700;0,900;1,700;1,900&family=IBM+Plex+Mono:wght@400;500;700&family=Lora:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{background:{NAVY};color:{WHITE};font-family:'Lora',serif;font-size:15px;line-height:1.65;}}
    a{{text-decoration:none;color:inherit;}}
    .site-nav{{background:{NAVY2};border-bottom:1px solid #1e2d4a;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;}}
    .nav-brand{{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:.85rem;letter-spacing:1px;text-transform:uppercase;}}
    .nav-brand .neon{{color:{NEON};}}
    .nav-pill{{font-family:'Barlow Condensed',sans-serif;font-size:.7rem;font-weight:700;letter-spacing:1px;padding:4px 12px;border-radius:20px;border:1px solid #263354;color:{MUTED};text-transform:uppercase;}}
    .nav-pill.active{{color:{GOLD};border-color:{GOLD};}}
    .hero{{padding:64px 24px 48px;border-bottom:4px solid {GOLD};}}
    .hero-inner{{max-width:1400px;margin:0 auto;}}
    .eyebrow{{font-family:'Barlow Condensed',sans-serif;font-size:.7rem;font-weight:900;letter-spacing:5px;text-transform:uppercase;color:{GOLD};margin-bottom:14px;}}
    .hero h1{{font-family:'Barlow Condensed',sans-serif;font-size:clamp(3rem,8vw,6.5rem);font-weight:900;font-style:italic;letter-spacing:-2px;text-transform:uppercase;line-height:.9;margin-bottom:18px;}}
    .hero h1 .l2{{color:{NEON};display:block;}}
    .hero-lede{{font-family:'Lora',serif;font-size:1.1rem;font-style:italic;color:{MUTED};max-width:760px;line-height:1.75;margin-top:18px;}}
    .hero-lede strong{{color:{WHITE};font-style:normal;}}
    .stats-strip{{display:flex;gap:48px;flex-wrap:wrap;margin-top:32px;padding-top:24px;border-top:1px solid #263354;}}
    .stat strong{{display:block;font-family:'Barlow Condensed',sans-serif;font-size:2.2rem;font-weight:900;color:{NEON};line-height:1;}}
    .stat span{{font-family:'IBM Plex Mono',monospace;font-size:.65rem;color:{MUTED};letter-spacing:2px;text-transform:uppercase;}}
    .filter-bar{{background:{NAVY2};border-bottom:1px solid #1e2d4a;padding:18px 24px;}}
    .filter-inner{{max-width:1400px;margin:0 auto;display:flex;gap:12px;flex-wrap:wrap;align-items:center;}}
    .filter-label{{font-family:'Barlow Condensed',sans-serif;font-size:.7rem;font-weight:900;letter-spacing:2px;color:{GOLD};text-transform:uppercase;}}
    .filter-chip{{font-family:'Barlow Condensed',sans-serif;font-size:.72rem;font-weight:700;letter-spacing:1px;padding:5px 12px;border-radius:4px;border:1px solid #263354;background:#111827;color:{MUTED};text-transform:uppercase;cursor:pointer;}}
    .filter-chip.active{{background:{NEON};color:{NAVY};border-color:{NEON};}}
    .grid-wrap{{padding:48px 24px;}}
    .grid-inner{{max-width:1400px;margin:0 auto;}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px;}}
    .team-card:hover{{transform:translateY(-3px);border-color:{MUTED}!important;}}
    .team-card.hidden{{display:none!important;}}
    .footer{{border-top:3px solid {GOLD};padding:36px 24px;background:{NAVY2};font-family:'IBM Plex Mono',monospace;font-size:.75rem;color:{MUTED};text-align:center;}}
    .footer a{{color:{NEON};}}
  </style>
</head>
<body>

<nav class="site-nav">
  <div class="nav-brand">Official Viewer's Guide<br><span class="neon">to International Baseball</span></div>
  <div style="display:flex;gap:6px;flex-wrap:wrap;">
    <a href="/index.html" class="nav-pill">Home</a>
    <a href="/leagues.html" class="nav-pill">Leagues</a>
    <a href="/calendar.html" class="nav-pill">Calendar</a>
    <a href="/wbc-rosters/index.html" class="nav-pill active">WBC Rosters</a>
    <a href="/wbc2026.html" class="nav-pill">WBC 2026</a>
  </div>
</nav>

<div class="hero">
  <div class="hero-inner">
    <div class="eyebrow">&#9733; The WBC Roster Explorer &#9733;</div>
    <h1>Every Player.<br><span class="l2">Every Country.</span></h1>
    <p class="hero-lede">
      The complete pantheon of the World Baseball Classic, by World Baseball Network. <strong>{total_players} players. {len(teams_list)} national teams.</strong> Filter by tournament, country, or finish. Click any team for a full roster page with stats, contributions, and Baseball Reference links to every player.
    </p>
    <div class="stats-strip">
      <div class="stat"><strong>{total_players}</strong><span>Players</span></div>
      <div class="stat"><strong>{len(teams_list)}</strong><span>National Teams</span></div>
      <div class="stat"><strong>1</strong><span>Tournament</span></div>
      <div class="stat"><strong>4</strong><span>Pools</span></div>
    </div>
  </div>
</div>

<div class="filter-bar">
  <div class="filter-inner">
    <span class="filter-label">Finish</span>
    <button class="filter-chip active" data-filter-finish="all">All</button>
    <button class="filter-chip" data-filter-finish="champion">Champion</button>
    <button class="filter-chip" data-filter-finish="runner-up">Runner-up</button>
    <button class="filter-chip" data-filter-finish="semifinalist">Semifinalists</button>
    <button class="filter-chip" data-filter-finish="quarterfinalist">Quarterfinalists</button>
    <button class="filter-chip" data-filter-finish="pool stage">Pool Stage</button>
  </div>
</div>

<div class="grid-wrap">
  <div class="grid-inner">
    <div class="grid">
      {cards_html}
    </div>
  </div>
</div>

<div class="footer">
  <strong style="color:{WHITE};font-family:'Barlow Condensed',sans-serif;font-size:1rem;letter-spacing:1px;text-transform:uppercase;">WBC Roster Explorer</strong> &middot;
  A publication of <a href="https://worldbaseball.com">World Baseball Network</a> &middot;
  Generated from master spreadsheet
</div>

<script>
const cards = document.querySelectorAll('.team-card');
const chips = document.querySelectorAll('[data-filter-finish]');
chips.forEach(c => c.addEventListener('click', () => {{
  chips.forEach(x => x.classList.remove('active'));
  c.classList.add('active');
  const f = c.dataset.filterFinish;
  cards.forEach(card => {{
    card.classList.toggle('hidden', f !== 'all' && card.dataset.finish !== f);
  }});
}}));
</script>

</body>
</html>'''

# ============================================================
# MAIN
# ============================================================
def main():
    print("Reading CSV...")
    players = read_csv()
    print(f"  {len(players)} players loaded")

    print("Grouping by team...")
    teams = group_by_team(players)
    print(f"  {len(teams)} team-tournament combinations")

    print("Generating team pages...")
    for key, team_data in teams.items():
        meta = team_data['meta']
        slug = slugify(meta['country']) + "-" + meta['tournament'].split()[-1]
        outfile = OUTPUT_DIR / f"{slug}.html"
        with open(outfile, 'w', encoding='utf-8') as f:
            f.write(render_team_page(key, team_data))
        print(f"  ✓ {slug}.html ({len(team_data['players'])} players)")

    print("Generating master index...")
    with open(OUTPUT_DIR / "index.html", 'w', encoding='utf-8') as f:
        f.write(render_index(teams))
    print("  ✓ index.html")

    print(f"\n✅ Generated {len(teams) + 1} HTML files in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
