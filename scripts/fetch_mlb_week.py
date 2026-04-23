"""
========================================================================
fetch_mlb_week.py — MLB Weekly Schedule Generator for Baseball Without Borders
========================================================================

Pulls the MLB schedule for any week and outputs ready-to-paste HTML rows
for the Official Viewer's Guide. Uses MLB's public StatsAPI — free, no key.

USAGE (PowerShell, from anywhere):
    cd C:\\Users\\test\\Documents\\wbn-archive\\scripts
    python fetch_mlb_week.py 2026-05-04 2026-05-10

    # Or with no dates — uses current week:
    python fetch_mlb_week.py

The script will print HTML to the terminal AND save to a file:
    mlb_week_2026-05-04.html   (in the same /scripts folder)

Just copy/paste the contents into your Viewer's Guide template.

NO SUBSCRIPTION. NO API KEY. FREE FOREVER.
Data source: https://statsapi.mlb.com (MLB's public stats API)

Author: Baseball Without Borders (WBN)
========================================================================
"""

import urllib.request
import json
import sys
import os
from datetime import datetime, timedelta


# ── COLOR PALETTE (matches Viewer's Guide template) ──
COLORS = {
    'mlb':    '#D50032',
    'accent': '#f5c842',
    'neon':   '#00ff9d',
    'muted':  '#8899bb',
}

# ── BROADCASTER HINTS ──
# Maps day-of-week + game characteristics to likely national broadcaster
# MLB 2026 rights landscape:
#   - NBC/Peacock: Sunday Night Baseball (was ESPN)
#   - Apple TV+: Friday Night Baseball doubleheader
#   - TBS/Max: Tuesday Night Baseball
#   - FOX/FS1: Select Saturdays
#   - ESPN: Retains ~30 midweek windows + MLB Network distribution
#   - Netflix: Marquee events only (Opening Night, Derby, Field of Dreams)


def fetch_mlb_schedule(start_date, end_date):
    """Fetch raw MLB schedule data from statsapi.mlb.com."""
    url = (
        f"https://statsapi.mlb.com/api/v1/schedule"
        f"?sportId=1"
        f"&startDate={start_date}"
        f"&endDate={end_date}"
        f"&hydrate=team,linescore,broadcasts,probablePitcher"
    )

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BWB/1.0'})
        response = urllib.request.urlopen(req, timeout=30)
        return json.loads(response.read())
    except Exception as e:
        print(f"❌ Error fetching MLB data: {e}")
        print(f"URL tried: {url}")
        sys.exit(1)


def format_time_et(iso_utc):
    """Convert '2026-05-04T23:05:00Z' UTC to '7:05 PM ET' display string."""
    try:
        dt = datetime.strptime(iso_utc, '%Y-%m-%dT%H:%M:%SZ')
        # UTC → ET. EDT is UTC-4, EST is UTC-5.
        # May–Oct is EDT.
        et_offset = -4 if dt.month >= 3 and dt.month <= 10 else -5
        et = dt + timedelta(hours=et_offset)
        hour = et.hour
        suffix = 'AM' if hour < 12 else 'PM'
        display_hour = hour if 1 <= hour <= 12 else (hour - 12 if hour > 12 else 12)
        return f"{display_hour}:{et.minute:02d} {suffix}"
    except Exception:
        return "TBD"


def day_of_week(iso_date):
    """Get 'Mon', 'Tue', etc. from '2026-05-04'."""
    dt = datetime.strptime(iso_date, '%Y-%m-%d')
    return ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dt.weekday()]


def full_day(iso_date):
    """Get 'Monday May 4'."""
    dt = datetime.strptime(iso_date, '%Y-%m-%d')
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    months = ['January','February','March','April','May','June','July','August','September','October','November','December']
    return f"{days[dt.weekday()]} {months[dt.month - 1]} {dt.day}"


def infer_national_broadcaster(game, iso_date):
    """Best guess at national TV window based on day and game flags."""
    broadcasts = game.get('broadcasts', [])
    # Look for national broadcasters in the broadcast list
    national = [b for b in broadcasts if b.get('isNational')]
    if national:
        names = [b.get('name', '') for b in national]
        priority = ['FOX', 'FS1', 'ESPN', 'TBS', 'Apple TV+', 'Peacock', 'NBC', 'MLB Network', 'Netflix']
        for p in priority:
            for n in names:
                if p.lower() in n.lower():
                    return n
        return names[0]
    # Fallback by day
    dow = datetime.strptime(iso_date, '%Y-%m-%d').weekday()
    return {
        0: '',          # Monday — regional/local
        1: 'TBS · Max', # Tuesday Night Baseball
        2: '',          # Wed — regional
        3: '',          # Thu — regional
        4: 'Apple TV+', # Friday Night Baseball
        5: '',          # Sat — regional (sometimes FOX)
        6: 'NBC · Peacock',  # Sunday Night Baseball (new 2026)
    }.get(dow, '')


def generate_html(schedule, start_date, end_date):
    """Build the HTML rows for the Viewer's Guide."""
    dates = schedule.get('dates', [])
    total = schedule.get('totalGames', 0)

    html_parts = []
    html_parts.append(f'''<!-- ═════════════════════════════════════════════════════════════════ -->
<!-- MLB WEEK · {start_date} to {end_date} · {total} games                     -->
<!-- Auto-generated by fetch_mlb_week.py from statsapi.mlb.com              -->
<!-- ═════════════════════════════════════════════════════════════════ -->

<div class="league-block mlb">
  <div class="league-head">
    <div class="lh-flag">🇺🇸</div>
    <div>
      <div class="lh-abbr">MLB</div>
      <div class="lh-full">Major League Baseball · Week of {start_date}</div>
    </div>
    <div class="lh-meta">{total} games · Times in ET</div>
  </div>
''')

    for date_entry in dates:
        iso_date = date_entry.get('date', '')
        games = date_entry.get('games', [])
        if not games:
            continue

        html_parts.append(f'''
  <div class="day-block">
    <div class="day-head">
      <span class="day-abbr">{day_of_week(iso_date)}</span>
      <span class="day-full">{full_day(iso_date)}</span>
      <span class="day-count">{len(games)} games</span>
    </div>
    <div class="game-list">''')

        for game in games:
            teams = game.get('teams', {})
            away = teams.get('away', {}).get('team', {}).get('name', 'TBD')
            home = teams.get('home', {}).get('team', {}).get('name', 'TBD')
            time_et = format_time_et(game.get('gameDate', ''))
            broadcaster = infer_national_broadcaster(game, iso_date)
            venue = game.get('venue', {}).get('name', '')
            status = game.get('status', {}).get('detailedState', '')

            # Probable pitchers
            away_pitcher = teams.get('away', {}).get('probablePitcher', {}).get('fullName', 'TBD')
            home_pitcher = teams.get('home', {}).get('probablePitcher', {}).get('fullName', 'TBD')

            broadcast_html = f'<span class="game-tv">{broadcaster}</span>' if broadcaster else ''
            pitchers_html = (
                f'<span class="game-pitchers">{away_pitcher} vs {home_pitcher}</span>'
                if away_pitcher != 'TBD' or home_pitcher != 'TBD' else ''
            )

            html_parts.append(f'''
      <div class="game-row">
        <span class="game-time">{time_et}</span>
        <span class="game-matchup"><strong>{away}</strong> @ <strong>{home}</strong></span>
        {broadcast_html}
        {pitchers_html}
      </div>''')

        html_parts.append('''
    </div>
  </div>''')

    html_parts.append('''
</div>

<!-- ═════════════════════════════════════════════════════════════════ -->
<!-- END MLB WEEK · generated automatically · verify broadcaster before publish -->
<!-- ═════════════════════════════════════════════════════════════════ -->

<style>
  /* Minimal styles — merge into main Viewer's Guide CSS if not already present */
  .league-block.mlb { border-left: 4px solid #D50032; padding: 20px 24px; background: #111827; border-radius: 8px; margin-bottom: 20px; }
  .league-head { display: flex; align-items: center; gap: 14px; padding-bottom: 12px; margin-bottom: 14px; border-bottom: 1px solid #1e2d4a; }
  .lh-flag { font-size: 1.8rem; }
  .lh-abbr { font-family: 'Barlow Condensed', sans-serif; font-weight: 900; font-size: 1.4rem; letter-spacing: -0.5px; }
  .lh-full { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #8899bb; text-transform: uppercase; letter-spacing: 1px; }
  .lh-meta { margin-left: auto; font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #f5c842; }
  .day-block { margin-bottom: 18px; }
  .day-head { display: flex; align-items: baseline; gap: 12px; padding-bottom: 6px; border-bottom: 1px dashed #1e2d4a; margin-bottom: 8px; }
  .day-abbr { font-family: 'Barlow Condensed', sans-serif; font-weight: 900; font-size: 1rem; color: #f5c842; letter-spacing: 2px; }
  .day-full { font-family: 'Lora', serif; font-style: italic; color: #f0f4ff; }
  .day-count { font-family: 'IBM Plex Mono', monospace; font-size: 0.65rem; color: #8899bb; margin-left: auto; }
  .game-list { display: flex; flex-direction: column; gap: 6px; padding-left: 12px; }
  .game-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; padding: 4px 0; font-size: 0.88rem; }
  .game-time { font-family: 'IBM Plex Mono', monospace; font-size: 0.8rem; color: #f5c842; font-weight: 700; min-width: 76px; }
  .game-matchup { font-family: 'Lora', serif; color: #f0f4ff; }
  .game-matchup strong { color: #f0f4ff; font-family: 'Barlow Condensed', sans-serif; font-weight: 700; letter-spacing: 0.3px; }
  .game-tv { font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; color: #00ff9d; font-weight: 700; padding: 2px 8px; background: rgba(0,255,157,0.08); border-radius: 3px; }
  .game-pitchers { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: #8899bb; font-style: italic; }
</style>
''')

    return '\n'.join(html_parts)


def generate_stats_summary(schedule, start_date):
    """Print a nice summary to the terminal."""
    dates = schedule.get('dates', [])
    total = schedule.get('totalGames', 0)

    print(f"\n{'=' * 64}")
    print(f"  MLB SCHEDULE — Week of {start_date}")
    print(f"{'=' * 64}\n")
    print(f"  Total games: {total}")
    print(f"  Days with games: {len(dates)}")

    for date_entry in dates:
        iso_date = date_entry.get('date', '')
        games = date_entry.get('games', [])
        if games:
            print(f"\n  {full_day(iso_date)} ({len(games)} games)")
            for g in games[:3]:
                away = g.get('teams', {}).get('away', {}).get('team', {}).get('abbreviation', 'TBD')
                home = g.get('teams', {}).get('home', {}).get('team', {}).get('abbreviation', 'TBD')
                time = format_time_et(g.get('gameDate', ''))
                print(f"    {time} · {away} @ {home}")
            if len(games) > 3:
                print(f"    + {len(games) - 3} more games")
    print(f"\n{'=' * 64}\n")


def get_current_week_dates():
    """Return Monday–Sunday of current week."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    return monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')


def main():
    # Parse args
    if len(sys.argv) == 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    elif len(sys.argv) == 1:
        start_date, end_date = get_current_week_dates()
        print(f"No dates provided — using current week: {start_date} to {end_date}")
    else:
        print("Usage: python fetch_mlb_week.py [YYYY-MM-DD YYYY-MM-DD]")
        print("Example: python fetch_mlb_week.py 2026-05-04 2026-05-10")
        sys.exit(1)

    # Validate
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        print(f"❌ Dates must be in YYYY-MM-DD format. Got: {start_date} to {end_date}")
        sys.exit(1)

    print(f"\n🔄 Fetching MLB schedule from {start_date} to {end_date}...")
    schedule = fetch_mlb_schedule(start_date, end_date)

    generate_stats_summary(schedule, start_date)

    # Generate HTML
    html = generate_html(schedule, start_date, end_date)

    # Save to file next to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, f'mlb_week_{start_date}.html')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ HTML saved to: {output_file}")
    print(f"   Copy this file's contents into the MLB section of your Viewer's Guide.\n")
    print(f"💡 Tip: open the file in VS Code to preview and adjust broadcaster tags.\n")


if __name__ == '__main__':
    main()
