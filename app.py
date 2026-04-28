import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# TITLE
# =========================
st.title("⚾ MLB Dashboard")

# =========================
# Monday-first calendar via CSS injection
# =========================
st.markdown("""
<style>
/* Shift Streamlit's date picker to start on Monday */
[data-testid="stDateInput"] table thead tr th:first-child {
    display: none;
}
[data-testid="stDateInput"] table tbody tr td:first-child {
    display: none;
}
</style>
""", unsafe_allow_html=True)

# =========================
# STATE
# =========================
if "selected_game_pk" not in st.session_state:
    st.session_state.selected_game_pk = None

# =========================
# TIME HELPERS (ET - 24 HOUR)
# =========================
ET = ZoneInfo("America/New_York")

def convert_to_et(raw_time):
    if not raw_time:
        return None
    try:
        dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        return dt.astimezone(ET)
    except:
        return None

def format_et(dt):
    if not dt:
        return "TBD"
    return dt.strftime("%H:%M") + " ET"

def format_full_et(dt):
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " ET"

# =========================
# EMOJIS
# =========================
def get_result_emoji(result_event: str, desc: str = ""):
    text = f"{result_event or ''} {desc or ''}".lower()
    if "home run" in text:
        return "💥"
    if "strikeout" in text:
        return "❌"
    if "walk" in text:
        return "🚶"
    if "single" in text:
        return "🟢"
    if "double play" in text:
        return "❌"
    if "error" in text:
        return "🟡"
    if "stolen base" in text:
        return "🏃"
    if "out" in text:
        return "❌"
    return "⚾"

def get_pitch_emoji(pitch_result: str):
    r = (pitch_result or "").lower()
    if "ball" in r:
        return "🔵"
    if "called strike" in r:
        return "🔴"
    if "swinging strike" in r:
        return "💨"
    if "foul" in r:
        return "🟡"
    if "in play" in r:
        return "⚾"
    if "hit by pitch" in r:
        return "🤕"
    return "⚪"

# =========================
# TEAM ABBREVIATIONS
# =========================
TEAM_ABBREV = {
    "Arizona Diamondbacks": "ARI",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Oakland Athletics": "OAK",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD",
    "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSH",
}

def get_team_abbrev(team_id, name):
    return TEAM_ABBREV.get(name, name[:3].upper())

# =========================
# GAME VIEW
# =========================
if st.session_state.selected_game_pk:

    game_pk = st.session_state.selected_game_pk

    if st.button("⬅ Back to Schedule"):
        st.session_state.selected_game_pk = None
        st.rerun()

    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    data = requests.get(url).json()

    home_team = data.get("gameData", {}).get("teams", {}).get("home", {}).get("name", "Home")
    away_team = data.get("gameData", {}).get("teams", {}).get("away", {}).get("name", "Away")

    home_id = data.get("gameData", {}).get("teams", {}).get("home", {}).get("id")
    away_id = data.get("gameData", {}).get("teams", {}).get("away", {}).get("id")

    home_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home_id}.svg"
    away_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away_id}.svg"

    linescore = data.get("liveData", {}).get("linescore", {})
    home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
    away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)

    away_abbr = get_team_abbrev(away_id, away_team)
    home_abbr = get_team_abbrev(home_id, home_team)

    # =========================
    # HEADER
    # =========================
    c1, c2, c3 = st.columns([1, 6, 1])

    with c1:
        st.image(away_logo, width=60)

    with c2:
        st.markdown(
            f"""
            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 700;
                font-size: clamp(16px, 2.6vw, 28px);
                gap: 10px;
                flex-wrap: wrap;
                text-align: center;
            ">
                <span>{away_abbr}</span>
                <span style="color:#888;">{away_score}</span>
                <span>-</span>
                <span style="color:#888;">{home_score}</span>
                <span>{home_abbr}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.image(home_logo, width=60)

    # =========================
    # FILTERS
    # =========================
    USE_INNING_FILTER = st.checkbox("Filter by Inning", value=False)
    USE_TIME_FILTER = st.checkbox("Filter by actual time (ET)", value=False)

    START_DT = None
    END_DT = None

    at_bats = []

    for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

        start_dt = convert_to_et(play.get("about", {}).get("startTime"))
        end_dt = convert_to_et(play.get("about", {}).get("endTime"))

        last_pitch_dt = None

        # ---- Pitch-by-pitch data ----
        pitches = []
        pitch_num = 0
        balls = 0
        strikes = 0

        for event in play.get("playEvents", []):
            if event.get("isPitch"):
                pitch_num += 1
                details = event.get("details", {})
                pitch_type = event.get("pitchData", {}).get("startSpeed")
                pitch_name = details.get("type", {}).get("description", "Unknown")
                call_desc = details.get("description", "")
                call_code = details.get("call", {}).get("code", "")

                # Update count
                count = event.get("count", {})
                b = count.get("balls", balls)
                s = count.get("strikes", strikes)

                pitches.append({
                    "num": pitch_num,
                    "pitch_name": pitch_name,
                    "call": call_desc,
                    "speed_mph": pitch_type,
                    "balls": b,
                    "strikes": s,
                    "start_time": convert_to_et(event.get("startTime")),
                })

                last_pitch_dt = convert_to_et(event.get("startTime"))

        raw_inning = play.get("about", {}).get("inning")

        at_bats.append({
            "atBatIndex": play.get("atBatIndex"),
            "batter": play.get("matchup", {}).get("batter", {}).get("fullName"),
            "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName"),
            "result": play.get("result", {}).get("event"),
            "desc": play.get("result", {}).get("description"),
            "away_score": play.get("result", {}).get("awayScore"),
            "home_score": play.get("result", {}).get("homeScore"),
            "inning_raw": raw_inning,
            "inning_group": "Extra Innings" if raw_inning >= 10 else raw_inning,
            "half_inning": play.get("about", {}).get("halfInning"),
            "start_dt": start_dt,
            "end_dt": end_dt,
            "last_pitch_dt": last_pitch_dt,
            "pitches": pitches,
        })

    # =========================
    # INNING FILTER UI
    # =========================
    all_innings = sorted(
        {ab["inning_group"] for ab in at_bats if ab["inning_group"] is not None},
        key=lambda x: (x == "Extra Innings", x if isinstance(x, int) else 999)
    )

    selected_innings = []

    if USE_INNING_FILTER:
        selected_innings = st.multiselect(
            "Select innings",
            options=all_innings,
            default=[]
        )

    # =========================
    # FILTER LOGIC
    # =========================
    run_filters = st.button("🚀 Apply Filters")

    def inning_match(ab):
        if not USE_INNING_FILTER:
            return True
        if not selected_innings:
            return False
        return ab["inning_group"] in selected_innings

    def time_match(ab):
        if not USE_TIME_FILTER:
            return True
        if not ab["start_dt"]:
            return False
        return START_DT <= ab["start_dt"] <= END_DT

    filtered = at_bats

    if run_filters:
        filtered = [
            ab for ab in at_bats
            if inning_match(ab) and time_match(ab)
        ]

    # =========================
    # OUTPUT
    # =========================
    prev_score = None

    for ab in filtered:

        emoji = get_result_emoji(ab["result"], ab["desc"])
        inning_label = f"{ab['inning_raw']} ({ab['half_inning']})"

        st.subheader(f"{emoji} At Bat {ab['atBatIndex']}")

        score = f"{ab['away_score']} - {ab['home_score']}"

        if score != prev_score and prev_score is not None:
            st.write(f"🏟️ {inning_label} | 📊 {score} 🔥 SCORING PLAY 🔥")
        else:
            st.write(f"🏟️ {inning_label} | 📊 {score}")

        st.write(f"👤 {ab['batter']} vs 🧢 {ab['pitcher']}")
        st.write(f"📌 {ab['result']} - {ab['desc']}")

        st.write(f"🕒 At Bat Start: {format_full_et(ab['start_dt'])}")
        st.success(f"🕒 Last Pitch: {format_full_et(ab['last_pitch_dt'])}")
        st.write(f"🕒 At Bat End: {format_full_et(ab['end_dt'])}")

        # =========================
        # PITCH-BY-PITCH
        # =========================
        if ab["pitches"]:
            with st.expander(f"🎯 Pitch-by-Pitch ({len(ab['pitches'])} pitches)"):
                for p in ab["pitches"]:
                    p_emoji = get_pitch_emoji(p["call"])
                    speed_str = f" · {p['speed_mph']:.1f} mph" if p["speed_mph"] else ""
                    count_str = f"Count: {p['balls']}-{p['strikes']}"
                    time_str = format_full_et(p["start_time"]) if p["start_time"] else ""
                    st.markdown(
                        f"{p_emoji} **Pitch {p['num']}** — {p['pitch_name']}{speed_str}  \n"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;📣 *{p['call']}* | {count_str}"
                        + (f" | 🕒 {time_str}" if time_str else "")
                    )

        st.divider()
        prev_score = score

# =========================
# SCHEDULE VIEW
# =========================
else:

    # Monday-first date input via locale workaround
    import locale
    date = st.date_input(
        "Select date",
        datetime.today(),
        format="YYYY-MM-DD",
    )
    date_str = date.strftime("%Y-%m-%d")

    st.markdown(f"## 📅 MLB Schedule — {date_str}")

    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
    data = requests.get(url).json()

    games = []

    for d in data.get("dates", []):
        for g in d.get("games", []):

            away = g["teams"]["away"]["team"]
            home = g["teams"]["home"]["team"]
            away_abbr = get_team_abbrev(away["id"], away["name"])
            home_abbr = get_team_abbrev(home["id"], home["name"])

            games.append({
                "gamePk": g["gamePk"],
                "away_name": away["name"],
                "home_name": home["name"],
                "away_abbr": away_abbr,
                "home_abbr": home_abbr,
                "away_logo": f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away['id']}.svg",
                "home_logo": f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home['id']}.svg",
                "time": convert_to_et(g.get("gameDate")),
                "status": g.get("status", {}).get("detailedState", "Scheduled"),
                "away_score": g["teams"]["away"].get("score", 0),
                "home_score": g["teams"]["home"].get("score", 0),
            })

    # Schedule card CSS
    st.markdown("""
    <style>
    .schedule-card {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
    }
    .team-logo-col {
        display: flex;
        flex-direction: column;
        gap: 4px;
        flex-shrink: 0;
    }
    .team-logo-col img {
        width: 24px;
        height: 24px;
    }
    .game-info {
        flex: 1;
        min-width: 0;
        font-size: 13px;
        line-height: 1.4;
    }
    .matchup {
        font-weight: 700;
        font-size: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .game-meta {
        color: #888;
        font-size: 11px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    </style>
    """, unsafe_allow_html=True)

    cols = st.columns(2)

    for i, game in enumerate(games):

        with cols[i % 2]:

            time_str = format_et(game["time"])
            status = game["status"]
            away_abbr = game["away_abbr"]
            home_abbr = game["home_abbr"]

            if status.lower() != "scheduled":
                score_str = f"{game['away_score']}-{game['home_score']}"
                meta_line = f"🕒 {time_str} · {status} · {score_str}"
            else:
                meta_line = f"🕒 {time_str} · {status}"

            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 4, 1])

                with c1:
                    st.image(game["away_logo"], width=24)
                    st.image(game["home_logo"], width=24)

                with c2:
                    st.markdown(
                        f"<div class='matchup'>{away_abbr} @ {home_abbr}</div>"
                        f"<div class='game-meta'>{meta_line}</div>",
                        unsafe_allow_html=True,
                    )

                with c3:
                    if st.button("▶", key=f"go_{game['gamePk']}", use_container_width=True, help=f"{game['away_name']} @ {game['home_name']}"):
                        st.session_state.selected_game_pk = game["gamePk"]
                        st.rerun()
