import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import html as html_lib
from datetime import datetime, timedelta, timezone

API_TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "fccf5ef3d21742fd923129a7165304da")
BASE_URL = "https://api.football-data.org/v4"
COMPETITION = "SA"
RETENTION_HOURS = 36  # Keep completed matchday scores visible for 36 hours


def fetch_api(endpoint: str) -> dict:
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "X-Auth-Token": API_TOKEN,
        "User-Agent": "SerieATerminal/2.0"
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        print(f"API Error fetching {url}: {e}")
        return {}


def fetch_news() -> list:
    """Fetches breaking headlines from Football-Italia RSS."""
    feed_url = "https://football-italia.net/feed/"
    articles = []
    try:
        req = urllib.request.Request(
            feed_url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
            for item in root.findall(".//item")[:10]:
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else "#"
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                date_clean = pub_date[:16] if pub_date else ""
                articles.append({
                    "title": html_lib.unescape(title),
                    "link": link,
                    "date": date_clean
                })
    except Exception as e:
        print(f"Error fetching news: {e}")
    return articles


def fetch_youtube_highlights() -> list:
    """Fetches strictly the top 2 newest Serie A match highlights from CBS Sports Golazo."""
    channel_url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCET00YnetHT7tOpu12v8jxg"
    videos = []
    
    EXCLUDED_KEYWORDS = [
        "UCL", "CHAMPIONS LEAGUE", "CARABAO", "EFL", "PREMIER LEAGUE", 
        "LIGA MX", "REACTION", "PREDICTING", "PODCAST", "CONFERENZA", 
        "INTERVIEW", "INTERVISTA", "SHORT"
    ]
    
    try:
        req = urllib.request.Request(
            channel_url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            root = ET.fromstring(resp.read())
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015"
            }

            for entry in root.findall("atom:entry", ns):
                video_id_el = entry.find("yt:videoId", ns)
                title_el = entry.find("atom:title", ns)
                published_el = entry.find("atom:published", ns)

                if video_id_el is not None and title_el is not None:
                    raw_title = title_el.text or ""
                    vid = video_id_el.text or ""
                    pub = published_el.text[:10] if published_el is not None and published_el.text else ""
                    upper_title = raw_title.upper()

                    # 1. Require Serie A and highlight indicators
                    if not (("SERIE A" in upper_title or "EXTENDED HIGHLIGHTS" in upper_title) and "HIGHLIGHT" in upper_title):
                        continue

                    # 2. Skip non-Serie A leagues and studio talk
                    if any(bad_word in upper_title for bad_word in EXCLUDED_KEYWORDS):
                        continue

                    # 3. Clean up the title display
                    clean_title = (
                        raw_title.replace("HIGHLIGHTS |", "")
                        .replace("HIGHLIGHTS:", "")
                        .replace("Extended Highlights |", "")
                        .replace("| Serie A | CBS Sports Golazo", "")
                        .replace("| Serie A", "")
                        .replace("| CBS Sports Golazo", "")
                        .strip()
                    )
                    if "|" in clean_title:
                        clean_title = clean_title.split("|")[0].strip()

                    videos.append({
                        "id": vid,
                        "title": clean_title,
                        "date": pub
                    })

                    if len(videos) == 2:
                        break

    except Exception as e:
        print(f"Error fetching CBS Golazo highlights: {e}")

    return videos


def build_dashboard():
    print("1/5 Fetching Standings & Form...")
    standings_data = fetch_api(f"/competitions/{COMPETITION}/standings")

    print("2/5 Fetching Fixtures...")
    matches_data = fetch_api(f"/competitions/{COMPETITION}/matches")

    print("3/5 Fetching Top Scorers...")
    scorers_data = fetch_api(f"/competitions/{COMPETITION}/scorers")

    print("4/5 Fetching Dispatch Headlines...")
    news_items = fetch_news()

    print("5/5 Fetching YouTube Match Highlights...")
    highlight_videos = fetch_youtube_highlights()

    # 1. Standings Table
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
                    form_html += '<span class="w-4 h-4 rounded bg-emerald-500/20 text-emerald-400 font-mono text-[9px] font-bold flex items-center justify-center">W</span>'
                elif f == "D":
                    form_html += '<span class="w-4 h-4 rounded bg-amber-500/20 text-amber-400 font-mono text-[9px] font-bold flex items-center justify-center">D</span>'
                elif f == "L":
                    form_html += '<span class="w-4 h-4 rounded bg-rose-500/20 text-rose-400 font-mono text-[9px] font-bold flex items-center justify-center">L</span>'

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

    # 2. Match Center: Show full current/relevant matchday slate with retention buffer
    matches = matches_data.get("matches", [])
    now_dt = datetime.now(timezone.utc)
    
    # Check for matches currently live or paused
    live_matchdays = {m.get("matchday") for m in matches if m.get("status") in ("IN_PLAY", "PAUSED")}
    
    if live_matchdays:
        current_matchday = min(live_matchdays)
    else:
        # Check the last finished matchday and see if it's within the retention window
        finished_matches = [m for m in matches if m.get("status") == "FINISHED" and m.get("utcDate")]
        last_finished_matchday = finished_matches[-1].get("matchday") if finished_matches else None
        
        keep_last_finished = False
        if last_finished_matchday:
            last_round_matches = [m for m in finished_matches if m.get("matchday") == last_finished_matchday]
            try:
                # Find the kickoff timestamp of the final match in that round
                last_game_date_str = max(m.get("utcDate") for m in last_round_matches)
                last_game_dt = datetime.fromisoformat(last_game_date_str.replace("Z", "+00:00"))
                
                # If within RETENTION_HOURS of the final game, keep showing the finished matchday
                if now_dt - last_game_dt < timedelta(hours=RETENTION_HOURS):
                    keep_last_finished = True
            except Exception as e:
                print(f"Date parse error: {e}")

        if keep_last_finished:
            current_matchday = last_finished_matchday
        else:
            # Fall back to next upcoming scheduled matchday
            upcoming_matchdays = [
                m.get("matchday") for m in matches 
                if m.get("status") in ("TIMED", "SCHEDULED") and m.get("matchday") is not None
            ]
            current_matchday = upcoming_matchdays[0] if upcoming_matchdays else (last_finished_matchday or 1)

    # Filter matches for the active matchday
    if current_matchday:
        active_matches = [m for m in matches if m.get("matchday") == current_matchday]
    else:
        active_matches = matches[-10:]

    match_cards = []
    for m in active_matches:
        home = m.get("homeTeam", {}).get("shortName") or m.get("homeTeam", {}).get("name", "TBD")
        away = m.get("awayTeam", {}).get("shortName") or m.get("awayTeam", {}).get("name", "TBD")
        hc = m.get("homeTeam", {}).get("crest", "")
        ac = m.get("awayTeam", {}).get("crest", "")
        st = m.get("status")
        sh = m.get("score", {}).get("fullTime", {}).get("home")
        sa = m.get("score", {}).get("fullTime", {}).get("away")
        utc_date_str = m.get("utcDate", "")

        match_cards.append(f"""
        <div class="bg-zinc-900/70 border border-zinc-800/80 rounded-xl p-3.5 backdrop-blur-sm flex flex-col justify-between hover:border-zinc-700 transition match-card" data-utc="{utc_date_str}" data-status="{st}">
            <div class="flex justify-between items-center text-xs text-zinc-500 mb-2.5">
                <span class="font-mono text-[11px] text-zinc-400 match-date">{utc_date_str[:10]}</span>
                <span class="match-badge">
                    <span class="px-2 py-0.5 rounded bg-zinc-800 font-mono uppercase text-[10px] text-zinc-400">{st}</span>
                </span>
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

    # 3. Highlights Cards (CBS Sports Golazo)
    highlight_cards = []
    for v in highlight_videos:
        highlight_cards.append(f"""
        <div class="bg-zinc-900/70 border border-zinc-800/80 rounded-xl overflow-hidden backdrop-blur-sm flex flex-col justify-between hover:border-zinc-700 transition group">
            <div class="relative w-full pb-[56.25%] bg-zinc-950">
                <iframe 
                    class="absolute top-0 left-0 w-full h-full"
                    src="https://www.youtube-nocookie.com/embed/{v['id']}?rel=0" 
                    title="{v['title']}" 
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                    referrerpolicy="strict-origin-when-cross-origin"
                    loading="lazy"
                    allowfullscreen>
                </iframe>
            </div>
            <div class="p-3 flex justify-between items-start gap-2">
                <div>
                    <div class="flex items-center gap-1.5 mb-1">
                        <span class="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded border bg-emerald-600/30 text-emerald-400 border-emerald-500/30">CBS Golazo</span>
                        <span class="font-mono text-[10px] text-zinc-500">{v['date']}</span>
                    </div>
                    <h3 class="text-xs font-semibold text-zinc-200 line-clamp-2 group-hover:text-cyan-400 transition">{v['title']}</h3>
                </div>
                <a href="https://www.youtube.com/watch?v={v['id']}" target="_blank" rel="noopener noreferrer" 
                   class="shrink-0 text-[10px] font-mono bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-2 py-1 rounded transition" 
                   title="Open on YouTube">
                    ↗
                </a>
            </div>
        </div>
        """)

    # 4. Top Scorers
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

    # 5. News Ticker
    ticker_items_html = ""
    for n in news_items:
        ticker_items_html += f"""
        <a href="{n['link']}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 px-6 text-xs text-zinc-300 hover:text-cyan-400 whitespace-nowrap">
            <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            <span class="font-semibold text-zinc-100">{n['title']}</span>
            <span class="text-[10px] font-mono text-zinc-500">[{n['date']}]</span>
        </a>
        """

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    matchday_header = f"Match Center (Round {current_matchday})" if current_matchday else "Match Center"

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="strict-origin-when-cross-origin">
    <title>Calcio Intelligence | Serie A Hub</title>

    <!-- Social Preview / Open Graph Tags -->
    <meta property="og:title" content="Calcio Intelligence | Serie A Hub" />
    <meta property="og:description" content="Live standings, matchday fixtures, top scorers, and CBS Sports Golazo highlights." />
    <meta property="og:type" content="website" />
    <!-- Replace with your own hosted banner image or a generic Serie A logo URL -->
    <meta property="og:image" content="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Serie_A_logo_2019.svg/1200px-Serie_A_logo_2019.svg.png" />

    <!-- Twitter / X Preview Tags -->
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="Calcio Intelligence | Serie A Hub" />
    <meta name="twitter:description" content="Live standings, matchday fixtures, top scorers, and CBS Sports Golazo highlights." />
    <meta name="twitter:image" content="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Serie_A_logo_2019.svg/1200px-Serie_A_logo_2019.svg.png" />

    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
        .ticker-track {{
            display: inline-flex;
            width: max-content;
            will-change: transform;
        }}
    </style>
</head>
<body class="bg-[#090a0f] text-zinc-100 min-h-screen antialiased selection:bg-cyan-500 selection:text-black">
    
    <!-- Tricolore Header Bar -->
    <div class="h-1 w-full bg-gradient-to-r from-emerald-500 via-zinc-100 to-rose-500"></div>

    <!-- Live Breaking News Stock Ticker -->
    <div class="bg-zinc-950/90 border-b border-zinc-800/80 sticky top-0 z-50 backdrop-blur-md">
        <div class="flex items-center">
            <div class="bg-blue-600/90 text-white font-mono text-[11px] font-bold uppercase tracking-wider px-3.5 py-2 flex items-center gap-2 shrink-0 z-10 shadow-md">
                <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                <span>DISPATCH</span>
            </div>
            <div class="ticker-container overflow-hidden whitespace-nowrap flex-1 py-2">
                <div class="ticker-track">
                    {ticker_items_html}
                    {ticker_items_html}
                </div>
            </div>
        </div>
    </div>

    <div class="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
        
        <!-- Main Header -->
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
                <p class="text-xs text-zinc-400">Fixtures, league metrics, golden boot race, and official match highlights</p>
            </div>
            
            <div class="flex items-center gap-3">
                <div class="text-xs font-mono text-zinc-400 bg-zinc-900/90 border border-zinc-800 px-3.5 py-1.5 rounded-lg flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    <span>Synced: <span class="text-zinc-200 font-semibold">{now_utc}</span></span>
                </div>
            </div>
        </header>

        <!-- Match Center Grid -->
        <section class="space-y-3">
            <div class="flex justify-between items-center">
                <h2 class="text-xs font-bold font-mono tracking-wider uppercase text-zinc-400 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-sm bg-cyan-400"></span> {matchday_header}
                </h2>
                <span id="userTimezoneLabel" class="text-[11px] font-mono text-zinc-500">Local Kickoffs</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {"".join(match_cards) if match_cards else '<p class="text-xs text-zinc-500">No matches found.</p>'}
            </div>
        </section>

        <!-- CBS Sports Golazo Highlights Section -->
        <section class="space-y-3">
            <div class="flex justify-between items-center">
                <h2 class="text-xs font-bold font-mono tracking-wider uppercase text-zinc-400 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-sm bg-emerald-500"></span> Match Highlights & Extended Recaps
                </h2>
                <span class="text-[11px] font-mono text-zinc-500">CBS Sports Golazo</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                {"".join(highlight_cards) if highlight_cards else '<p class="text-xs text-zinc-500">No match highlights available at this time.</p>'}
            </div>
        </section>

        <!-- Main Content Area: Standings & Capocannoniere -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            
            <!-- Standings Table (2 Columns) -->
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

            <!-- Top Scorers (1 Column) -->
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

    </div>

    <!-- Client-Side Scripts -->
    <script>
        // 1. Instant Team Filter
        document.getElementById('teamSearch').addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase();
            document.querySelectorAll('#tableBody .table-row').forEach(function(row) {{
                const team = row.getAttribute('data-team') || '';
                row.style.display = team.includes(query) ? '' : 'none';
            }});
        }});

        // 2. Client-Side Timezone Auto-Converter & Status Badge Manager
        document.addEventListener('DOMContentLoaded', function() {{
            const userTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const tzShort = new Date().toLocaleTimeString('en-US', {{ timeZoneName: 'short' }}).split(' ')[2] || '';
            const tzLabel = document.getElementById('userTimezoneLabel');
            if (tzLabel && tzShort) {{
                tzLabel.textContent = `Times in ${{tzShort}} (${{userTz}})`;
            }}

            document.querySelectorAll('.match-card').forEach(function(card) {{
                const rawUtc = card.getAttribute('data-utc');
                const status = (card.getAttribute('data-status') || '').toUpperCase();
                if (!rawUtc) return;

                const matchDate = new Date(rawUtc);
                const dateEl = card.querySelector('.match-date');
                const badgeEl = card.querySelector('.match-badge');

                const dayName = matchDate.toLocaleDateString('en-US', {{ weekday: 'short' }});
                const monthDay = matchDate.toLocaleDateString('en-US', {{ month: 'short', day: 'numeric' }});
                const timeStr = matchDate.toLocaleTimeString('en-US', {{ hour: 'numeric', minute: '2-digit' }});

                if (dateEl) {{
                    dateEl.textContent = `${{dayName}}, ${{monthDay}}`;
                }}

                if (badgeEl) {{
                    if (status === 'IN_PLAY' || status === 'LIVE') {{
                        badgeEl.innerHTML = '<span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-mono uppercase text-[10px] font-bold animate-pulse">LIVE</span>';
                    }} else if (status === 'PAUSED') {{
                        badgeEl.innerHTML = '<span class="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 font-mono uppercase text-[10px] font-bold">HT</span>';
                    }} else if (status === 'FINISHED') {{
                        badgeEl.innerHTML = '<span class="px-2 py-0.5 rounded bg-zinc-800 font-mono uppercase text-[10px] text-zinc-400">FT</span>';
                    }} else if (status === 'POSTPONED' || status === 'SUSPENDED' || status === 'CANCELLED') {{
                        badgeEl.innerHTML = `<span class="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 font-mono uppercase text-[10px] font-bold">${{status.slice(0, 4)}}</span>`;
                    }} else {{
                        badgeEl.innerHTML = `<span class="px-2 py-0.5 rounded bg-blue-500/10 text-cyan-400 font-mono text-[10px] font-semibold">${{timeStr}}</span>`;
                    }}
                }}
            }});
        }});

        // Continuous, tab-resilient JS Marquee Engine
        (function() {{
            const track = document.querySelector('.ticker-track');
            const container = document.querySelector('.ticker-container');
            if (!track || !container) return;

            let pos = 0;
            let isHovered = false;
            const speed = 0.65;

            container.addEventListener('mouseenter', function() {{ isHovered = true; }});
            container.addEventListener('mouseleave', function() {{ isHovered = false; }});

            function step() {{
                if (!isHovered) {{
                    pos -= speed;
                    const halfWidth = track.scrollWidth / 2;
                    if (Math.abs(pos) >= halfWidth) {{
                        pos = 0;
                    }}
                    track.style.transform = `translate3d(${{pos}}px, 0, 0)`;
                }}
                requestAnimationFrame(step);
            }}

            requestAnimationFrame(step);
        }})();
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Dashboard refreshed successfully: index.html")


if __name__ == "__main__":
    build_dashboard()