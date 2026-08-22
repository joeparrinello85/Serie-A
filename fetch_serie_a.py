from datetime import datetime, timezone
import html as html_lib
import json
import os
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

API_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "fccf5ef3d21742fd923129a7165304da")
BASE_URL = "https://api.football-data.org/v4"
COMPETITION = "SA"


def fetch_api(endpoint: str) -> dict:
  url = f"{BASE_URL}{endpoint}"
  headers = {"X-Auth-Token": API_TOKEN, "User-Agent": "SerieATerminal/2.0"}
  try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
      return json.loads(response.read().decode("utf-8"))
  except Exception as e:
    print(f"API Error fetching {url}: {e}")
    return {}


def fetch_news() -> list:
  feed_url = "https://football-italia.net/feed/"
  articles = []
  try:
    req = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
      root = ET.fromstring(resp.read())
      for item in root.findall(".//item")[:6]:
        title = item.find("title").text if item.find("title") is not None else ""
        link = item.find("link").text if item.find("link") is not None else "#"
        pub_date = (
            item.find("pubDate").text
            if item.find("pubDate") is not None
            else ""
        )
        date_clean = pub_date[:16] if pub_date else ""
        articles.append({
            "title": html_lib.unescape(title),
            "link": link,
            "date": date_clean,
        })
  except Exception as e:
    print(f"Error fetching news: {e}")
  return articles


def fetch_transfers() -> list:
  url = "https://www.transfermarkt.co.uk/rss/news"
  transfers = []
  try:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
      root = ET.fromstring(resp.read())
      for item in root.findall(".//item")[:6]:
        title = item.find("title").text if item.find("title") is not None else ""
        link = item.find("link").text if item.find("link") is not None else "#"
        desc = (
            item.find("description").text
            if item.find("description") is not None
            else ""
        )
        desc_clean = re.sub("<[^<]+?>", "", desc).strip()[:110]
        transfers.append({
            "title": html_lib.unescape(title),
            "link": link,
            "desc": desc_clean + "...",
        })
  except Exception as e:
    print(f"Error fetching transfers: {e}")
  return transfers


def build_dashboard():
  print("1/5 Fetching Standings & Form...")
  standings_data = fetch_api(f"/competitions/{COMPETITION}/standings")

  print("2/5 Fetching Fixtures...")
  matches_data = fetch_api(f"/competitions/{COMPETITION}/matches")

  print("3/5 Fetching Top Scorers...")
  scorers_data = fetch_api(f"/competitions/{COMPETITION}/scorers")

  print("4/5 Fetching Dispatch...")
  news_items = fetch_news()

  print("5/5 Fetching Transfer Wire...")
  transfer_items = fetch_transfers()

  # 1. Standings Table with Form Badges
  table_rows = []
  for row in standings_data.get("standings", [{}])[0].get("table", []):
    pos = row.get("position")
    team = row.get("team", {}).get("name", "Unknown")
    short_name = row.get("team", {}).get("shortName", team)
    crest = row.get("team", {}).get("crest", "")
    played = row.get("playedGames", 0)
    won = row.get("won", 0)
    draw = row.get("draw", 0)
    lost = row.get("lost", 0)
    gd = row.get("goalDifference", 0)
    pts = row.get("points", 0)
    form_raw = row.get("form") or ""

    form_html = ""
    if form_raw:
      for f in form_raw.split(",")[-5:]:
        if f == "W":
          form_html += (
              '<span class="w-4 h-4 rounded bg-emerald-500/20 text-emerald-400'
              ' font-mono text-[9px] font-bold flex items-center'
              ' justify-center">W</span>'
          )
        elif f == "D":
          form_html += (
              '<span class="w-4 h-4 rounded bg-amber-500/20 text-amber-400'
              ' font-mono text-[9px] font-bold flex items-center'
              ' justify-center">D</span>'
          )
        elif f == "L":
          form_html += (
              '<span class="w-4 h-4 rounded bg-rose-500/20 text-rose-400'
              ' font-mono text-[9px] font-bold flex items-center'
              ' justify-center">L</span>'
          )

    zone_badge = ""
    zone_border = "border-transparent"
    if pos <= 4:
      zone_border = "border-l-cyan-500 bg-cyan-500/5"
      zone_badge = '<span class="text-[9px] font-bold text-cyan-400">UCL</span>'
    elif pos in (5, 6):
      zone_border = "border-l-blue-500 bg-blue-500/5"
      zone_badge = '<span class="text-[9px] font-bold text-blue-400">UEL</span>'
    elif pos >= 18:
      zone_border = "border-l-rose-500 bg-rose-500/5"
      zone_badge = '<span class="text-[9px] font-bold text-rose-400">REL</span>'

    table_rows.append(f"""
        <tr class="table-row border-b border-zinc-800/40 hover:bg-zinc-800/50 transition border-l-2 {zone_border}" data-team="{team.lower()}">
            <td class="py-3 px-3 font-mono text-zinc-400 text-xs font-semibold">{pos}</td>
            <td class="py-3 px-3">
                <div class="flex items-center gap-2.5">
                    <img src="{crest}" alt="{team}" class="w-6 h-6 object-contain drop-shadow-sm" onerror="this.style.display='none'"/>
                    <div>
                        <div class="font-semibold text-zinc-100 flex items-center gap-1.5">
                            <span>{short_name}</span>
                            {zone_badge}
                        </div>
                    </div>
                </div>
            </td>
            <td class="py-3 px-2 text-center font-mono text-zinc-300">{played}</td>
            <td class="py-3 px-2 text-center font-mono text-zinc-400 hidden sm:table-cell">{won}</td>
            <td class="py-3 px-2 text-center font-mono text-zinc-400 hidden sm:table-cell">{draw}</td>
            <td class="py-3 px-2 text-center font-mono text-zinc-400 hidden sm:table-cell">{lost}</td>
            <td class="py-3 px-2 text-center font-mono text-xs font-semibold { 'text-emerald-400' if gd > 0 else 'text-rose-400' if gd < 0 else 'text-zinc-400' }">{gd:+d}</td>
            <td class="py-3 px-3 text-center font-mono font-bold text-zinc-100 text-sm">{pts}</td>
            <td class="py-3 px-3 hidden md:table-cell">
                <div class="flex gap-1 justify-center">{form_html}</div>
            </td>
        </tr>
        """)

  # 2. Match Center Cards
  matches = matches_data.get("matches", [])
  active_matches = [
      m for m in matches if m.get("status") in ("TIMED", "SCHEDULED", "IN_PLAY")
  ][:8]
  if not active_matches:
    active_matches = [m for m in matches if m.get("status") == "FINISHED"][-8:]

  match_cards = []
  for m in active_matches:
    home = m.get("homeTeam", {}).get("shortName") or m.get(
        "homeTeam", {}
    ).get("name", "TBD")
    away = m.get("awayTeam", {}).get("shortName") or m.get(
        "awayTeam", {}
    ).get("name", "TBD")
    hc = m.get("homeTeam", {}).get("crest", "")
    ac = m.get("awayTeam", {}).get("crest", "")
    st = m.get("status")
    sh = m.get("score", {}).get("fullTime", {}).get("home")
    sa = m.get("score", {}).get("fullTime", {}).get("away")
    date_str = m.get("utcDate", "")[:10]

    status_badge = (
        '<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400'
        ' font-mono uppercase text-[10px] font-bold animate-pulse">LIVE</span>'
        if st == "IN_PLAY"
        else f'<span class="px-2 py-0.5 rounded bg-zinc-800/80 font-mono uppercase text-[10px] text-zinc-400">{st}</span>'
    )

    match_cards.append(f"""
        <div class="bg-zinc-900/70 border border-zinc-800/80 rounded-xl p-3.5 backdrop-blur-sm flex flex-col justify-between hover:border-zinc-700 transition">
            <div class="flex justify-between items-center text-xs text-zinc-500 mb-2.5">
                <span class="font-mono text-[11px] text-zinc-400">{date_str}</span>
                {status_badge}
            </div>
            <div class="space-y-2">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <img src="{hc}" class="w-5 h-5 object-contain" onerror="this.style.display='none'"/>
                        <span class="font-medium text-sm text-zinc-200">{home}</span>
                    </div>
                    <span class="font-mono font-bold text-sm text-zinc-100">{sh if sh is not None else ''}</span>
                </div>
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <img src="{ac}" class="w-5 h-5 object-contain" onerror="this.style.display='none'"/>
                        <span class="font-medium text-sm text-zinc-200">{away}</span>
                    </div>
                    <span class="font-mono font-bold text-sm text-zinc-100">{sa if sa is not None else ''}</span>
                </div>
            </div>
        </div>
        """)

  # 3. Top Scorers with Progress Bars
  scorers = scorers_data.get("scorers", [])[:6]
  max_goals = scorers[0].get("goals", 1) if scorers else 1
  scorer_rows = []
  for s in scorers:
    p = s.get("player", {}).get("name", "Unknown")
    t = s.get("team", {}).get("name", "")
    g = s.get("goals", 0)
    a = s.get("assists") or 0
    pct = int((g / max_goals) * 100) if max_goals > 0 else 0

    scorer_rows.append(f"""
        <div class="py-2.5 border-b border-zinc-800/40 last:border-0">
            <div class="flex justify-between items-baseline mb-1">
                <div>
                    <span class="text-sm font-semibold text-zinc-200">{p}</span>
                    <span class="text-xs text-zinc-500 ml-1.5">{t}</span>
                </div>
                <div class="font-mono text-xs">
                    <span class="font-bold text-cyan-400 text-sm">{g}G</span>
                    <span class="text-zinc-500 ml-1">({a}A)</span>
                </div>
            </div>
            <div class="w-full bg-zinc-800/60 rounded-full h-1.5 overflow-hidden">
                <div class="bg-gradient-to-r from-blue-500 to-cyan-400 h-1.5 rounded-full" style="width: {pct}%"></div>
            </div>
        </div>
        """)

  # 4. News Cards
  news_cards = [
      f"""
        <a href="{n['link']}" target="_blank" rel="noopener noreferrer" class="group block p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 hover:border-blue-500/50 hover:bg-zinc-800/40 transition">
            <div class="flex items-center gap-2 mb-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                <span class="text-[11px] font-mono text-zinc-500">{n['date']}</span>
            </div>
            <h4 class="text-sm font-semibold text-zinc-200 group-hover:text-cyan-400 transition leading-snug line-clamp-2">{n['title']}</h4>
        </a>
    """
      for n in news_items
  ]

  # 5. Transfer Cards
  transfer_cards = [
      f"""
        <a href="{t['link']}" target="_blank" rel="noopener noreferrer" class="group block p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 hover:border-emerald-500/50 hover:bg-zinc-800/40 transition">
            <h4 class="text-sm font-semibold text-zinc-200 group-hover:text-emerald-400 transition mb-1 leading-snug">{t['title']}</h4>
            <p class="text-xs text-zinc-400 leading-relaxed line-clamp-2">{t['desc']}</p>
        </a>
    """
      for t in transfer_items
  ]

  now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

  html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calcio Intelligence | Serie A Hub</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-[#090a0f] text-zinc-100 min-h-screen antialiased selection:bg-cyan-500 selection:text-black">
    
    <div class="h-1 w-full bg-gradient-to-r from-emerald-500 via-zinc-100 to-rose-500"></div>

    <div class="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
        
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center pb-6 border-b border-zinc-800/80 gap-4">
            <div class="space-y-1">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-600/30">
                        A
                    </div>
                    <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
                        Serie A Intelligence
                    </h1>
                </div>
                <p class="text-xs text-zinc-400">Fixtures, league metrics, golden boot race, and live transfer desk</p>
            </div>
            
            <div class="flex items-center gap-3">
                <div class="text-xs font-mono text-zinc-400 bg-zinc-900/90 border border-zinc-800 px-3.5 py-1.5 rounded-lg flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Synced: <span class="text-zinc-200 font-semibold">{now_utc}</span></span>
                </div>
            </div>
        </header>

        <section class="space-y-3">
            <div class="flex justify-between items-center">
                <h2 class="text-xs font-bold font-mono tracking-wider uppercase text-zinc-400 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-sm bg-cyan-400"></span> Match Center
                </h2>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {"".join(match_cards) if match_cards else '<p class="text-xs text-zinc-500">No matches found.</p>'}
            </div>
        </section>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            
            <div class="lg:col-span-2 bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md">
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4">
                    <div>
                        <h2 class="text-sm font-bold font-mono uppercase tracking-wider text-zinc-200">Classifica (Standings)</h2>
                        <div class="flex gap-3 text-[11px] font-mono text-zinc-400 mt-1">
                            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-cyan-500"></span> UCL (1-4)</span>
                            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-blue-500"></span> UEL (5-6)</span>
                            <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full bg-rose-500"></span> Relegation (18-20)</span>
                        </div>
                    </div>
                    
                    <input type="text" id="teamSearch" placeholder="Filter team..." 
                           class="bg-zinc-950 border border-zinc-800 text-xs px-3 py-1.5 rounded-lg text-zinc-200 focus:outline-none focus:border-cyan-500 transition w-full sm:w-40 font-mono"/>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs border-collapse">
                        <thead>
                            <tr class="border-b border-zinc-800 text-zinc-500 font-mono text-[11px]">
                                <th class="py-2.5 px-3">#</th>
                                <th class="py-2.5 px-3">Club</th>
                                <th class="py-2.5 px-2 text-center">P</th>
                                <th class="py-2.5 px-2 text-center hidden sm:table-cell">W</th>
                                <th class="py-2.5 px-2 text-center hidden sm:table-cell">D</th>
                                <th class="py-2.5 px-2 text-center hidden sm:table-cell">L</th>
                                <th class="py-2.5 px-2 text-center">GD</th>
                                <th class="py-2.5 px-3 text-center">PTS</th>
                                <th class="py-2.5 px-3 text-center hidden md:table-cell">Form</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody">
                            {"".join(table_rows)}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="bg-zinc-900/40 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md space-y-4">
                <div class="flex justify-between items-center border-b border-zinc-800/80 pb-3">
                    <h2 class="text-sm font-bold font-mono uppercase tracking-wider text-zinc-200">Capocannoniere</h2>
                    <span class="text-xs font-mono text-zinc-500">Goals (Assists)</span>
                </div>
                <div class="space-y-1">
                    {"".join(scorer_rows) if scorer_rows else '<p class="text-xs text-zinc-500">No scorer data available.</p>'}
                </div>
            </div>

        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="space-y-3">
                <h3 class="text-xs font-bold font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-sm bg-blue-500"></span> Football Italia Wire
                </h3>
                <div class="grid grid-cols-1 gap-2.5">
                    {"".join(news_cards) if news_cards else '<p class="text-xs text-zinc-500">No news feeds found.</p>'}
                </div>
            </div>

            <div class="space-y-3">
                <h3 class="text-xs font-bold font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-sm bg-emerald-500"></span> Transfermarkt Rumor Desk
                </h3>
                <div class="grid grid-cols-1 gap-2.5">
                    {"".join(transfer_cards) if transfer_cards else '<p class="text-xs text-zinc-500">No transfer data found.</p>'}
                </div>
            </div>
        </div>

    </div>

    <script>
        document.getElementById('teamSearch').addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase();
            document.querySelectorAll('#tableBody .table-row').forEach(function(row) {{
                const team = row.getAttribute('data-team') || '';
                row.style.display = team.includes(query) ? '' : 'none';
            }});
        }});
    </script>
</body>
</html>"""

  with open("index.html", "w", encoding="utf-8") as f:
    f.write(html)
  print("Refreshed dashboard with new UI: index.html")


if __name__ == "__main__":
  build_dashboard()