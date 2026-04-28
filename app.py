import streamlit as st
import requests
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

# =========================
# TITLE
# =========================
st.title("⚾ MLB Dashboard")

# =========================
# Monday-first calendar via JS locale override
# =========================
st.components.v1.html("""
<script>
(function() {
    const origDateTimeFormat = Intl.DateTimeFormat;
    function PatchedDateTimeFormat(locale, options) {
        return new origDateTimeFormat('en-GB', options);
    }
    PatchedDateTimeFormat.supportedLocalesOf = origDateTimeFormat.supportedLocalesOf.bind(origDateTimeFormat);
    Intl.DateTimeFormat = PatchedDateTimeFormat;
})();
</script>
""", height=0)

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
        return "🔴"
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

    if st.button("Back to Schedule"):
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

    # HEADER
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
    # BUILD AT-BATS
    # =========================
    at_bats = []

    for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

        start_dt = convert_to_et(play.get("about", {}).get("startTime"))
        end_dt = convert_to_et(play.get("about", {}).get("endTime"))
        last_pitch_dt = None
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
        away_sc = play.get("result", {}).get("awayScore", 0)
        home_sc = play.get("result", {}).get("homeScore", 0)

        at_bats.append({
            "atBatIndex": play.get("atBatIndex"),
            "batter": play.get("matchup", {}).get("batter", {}).get("fullName"),
            "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName"),
            "result": play.get("result", {}).get("event"),
            "desc": play.get("result", {}).get("description"),
            "away_score": away_sc,
            "home_score": home_sc,
            "inning_raw": raw_inning,
            "inning_group": "Extra Innings" if raw_inning >= 10 else raw_inning,
            "half_inning": play.get("about", {}).get("halfInning"),
            "start_dt": start_dt,
            "end_dt": end_dt,
            "last_pitch_dt": last_pitch_dt,
            "pitches": pitches,
        })

    # =========================
    # TAG SCORING PLAYS
    # A scoring play is any at-bat where the combined score
    # (away + home) is higher than the previous at-bat's score.
    # We pre-compute this so the filter can use it.
    # =========================
    prev_total = 0
    for ab in at_bats:
        total = (ab["away_score"] or 0) + (ab["home_score"] or 0)
        ab["is_scoring_play"] = total > prev_total
        prev_total = total

    # =========================
    # DERIVE GAME TIME BOUNDS FOR FILTER DEFAULTS
    # =========================
    game_start_raw = data.get("gameData", {}).get("datetime", {}).get("dateTime")
    game_start_default = convert_to_et(game_start_raw)

    all_end_dts = [ab["end_dt"] for ab in at_bats if ab["end_dt"]]
    game_end_default = max(all_end_dts) if all_end_dts else None

    if not game_start_default:
        all_start_dts = [ab["start_dt"] for ab in at_bats if ab["start_dt"]]
        game_start_default = min(all_start_dts) if all_start_dts else None

    # =========================
    # FILTER CHECKBOXES
    # =========================
    USE_INNING_FILTER = st.checkbox("🏟️ Filter by Inning", value=False)
    USE_TIME_FILTER = st.checkbox("🕐 Filter by Actual Time (ET)", value=False)
    USE_SCORING_FILTER = st.checkbox("🔥 Scoring Plays Only", value=False)

    START_DT = None
    END_DT = None

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
    # TIME FILTER UI
    # =========================
    if USE_TIME_FILTER:
        default_start_time = game_start_default.time() if game_start_default else dtime(12, 0)
        default_end_time = game_end_default.time() if game_end_default else dtime(23, 59)

        tf_col1, tf_col2 = st.columns(2)
        with tf_col1:
            start_time_input = st.time_input(
                "Start (ET)",
                value=default_start_time,
                step=60,
            )
        with tf_col2:
            end_time_input = st.time_input(
                "End (ET)",
                value=default_end_time,
                step=60,
            )

        ref_date = game_start_default.date() if game_start_default else datetime.today().date()
        START_DT = datetime.combine(ref_date, start_time_input).replace(tzinfo=ET)
        END_DT = datetime.combine(ref_date, end_time_input).replace(tzinfo=ET)

    # =========================
    # APPLY FILTERS
    # =========================
    run_filters = st.button("Apply Filters")

    def inning_match(ab):
        if not USE_INNING_FILTER:
            return True
        if not selected_innings:
            return False
        return ab["inning_group"] in selected_innings

    def time_match(ab):
        if not USE_TIME_FILTER:
            return True
        if not ab["start_dt"] or START_DT is None or END_DT is None:
            return False
        return START_DT <= ab["start_dt"] <= END_DT

    def scoring_match(ab):
        if not USE_SCORING_FILTER:
            return True
        return ab["is_scoring_play"]

    filtered = at_bats
    if run_filters:
        filtered = [
            ab for ab in at_bats
            if inning_match(ab) and time_match(ab) and scoring_match(ab)
        ]

    # =========================
    # INFO BANNERS (shown after Apply Filters)
    # =========================
    if run_filters:
        total = len(at_bats)
        showing = len(filtered)

        if USE_INNING_FILTER:
            inning_labels = [str(i) for i in selected_innings] if selected_innings else ["none selected"]
            st.info(f"🏟️ **Inning filter:** Innings {', '.join(inning_labels)} — showing **{showing}** of **{total}** at-bats")

        if USE_TIME_FILTER:
            st.info(f"🕐 **Time filter:** {START_DT.strftime('%H:%M')} → {END_DT.strftime('%H:%M')} ET — showing **{showing}** of **{total}** at-bats")

        if USE_SCORING_FILTER:
            total_scoring = sum(1 for ab in at_bats if ab["is_scoring_play"])
            st.info(f"🔥 **Scoring plays filter:** {total_scoring} scoring play(s) in game — showing **{showing}** of **{total}** at-bats")

        if showing == 0:
            st.warning("⚠️ No results found — please check the filters applied.")
            st.stop()

    # =========================
    # OUTPUT
    # =========================
    prev_score = None

    for ab in filtered:
        emoji = get_result_emoji(ab["result"], ab["desc"])
        half = (ab["half_inning"] or "").capitalize()
        inning_label = f"{half} {ab['inning_raw']}"

        st.subheader(f"{emoji} At Bat #{ab['atBatIndex']}")

        score = f"{ab['away_score']} - {ab['home_score']}"

        # Inning + score row
        if ab["is_scoring_play"]:
            st.markdown(f"🏟️ **Inning:** {inning_label} &nbsp;|&nbsp; 📊 **Score:** {score} &nbsp; 🔥 *Scoring Play!*")
        else:
            st.markdown(f"🏟️ **Inning:** {inning_label} &nbsp;|&nbsp; 📊 **Score:** {score}")

        # Matchup
        st.markdown(f"👤 **Batter:** {ab['batter']} &nbsp;|&nbsp; 🧢 **Pitcher:** {ab['pitcher']}")

        # Result
        st.markdown(f"📋 **Result:** {ab['result']}")
        st.caption(f"📝 {ab['desc']}")

        # Timestamps
        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.markdown(f"🕐 **At Bat Start**  \n`{format_full_et(ab['start_dt']) or 'N/A'}`")
        with col_t2:
            st.markdown(f"⚡ **Last Pitch**  \n`{format_full_et(ab['last_pitch_dt']) or 'N/A'}`")
        with col_t3:
            st.markdown(f"🕔 **At Bat End**  \n`{format_full_et(ab['end_dt']) or 'N/A'}`")

        # Pitch-by-pitch
        if ab["pitches"]:
            with st.expander(f"🎯 Pitch-by-Pitch — {len(ab['pitches'])} pitches"):
                for p in ab["pitches"]:
                    p_emoji = get_pitch_emoji(p["call"])
                    speed_str = f"  🗲 {p['speed_mph']:.1f} mph" if p["speed_mph"] else ""
                    count_str = f"⚖️ Count: **{p['balls']}-{p['strikes']}**"
                    time_str = f"🕒 {format_full_et(p['start_time'])}" if p["start_time"] else ""
                    st.markdown(
                        f"{p_emoji} **Pitch {p['num']}** — 📌 {p['pitch_name']}{speed_str}  \n"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;📣 *{p['call']}* &nbsp;|&nbsp; {count_str}"
                        + (f" &nbsp;|&nbsp; {time_str}" if time_str else "")
                    )

        st.divider()
        prev_score = score

# =========================
# SCHEDULE VIEW
# =========================
else:

    date = st.date_input(
        "Select date",
        datetime.today(),
        format="YYYY-MM-DD",
    )
    date_str = date.strftime("%Y-%m-%d")

    st.markdown(f"## MLB Schedule — {date_str}")

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

    card_items = []
    for game in games:
        time_str = format_et(game["time"])
        status = game["status"]
        if status.lower() != "scheduled":
            meta = f"{time_str} &middot; {status} &middot; {game['away_score']}-{game['home_score']}"
        else:
            meta = f"{time_str} &middot; {status}"

        card_items.append({
            "gamePk": game["gamePk"],
            "away_abbr": game["away_abbr"],
            "home_abbr": game["home_abbr"],
            "away_logo": game["away_logo"],
            "home_logo": game["home_logo"],
            "meta": meta,
            "away_name": game["away_name"],
            "home_name": game["home_name"],
        })

    st.markdown("""
<style>
div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlockBorderWrapper"] {
    height: 80px !important;
    min-height: 80px !important;
    max-height: 80px !important;
    overflow: hidden;
}
.game-matchup {
    font-weight: 700;
    font-size: 16px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin: 0;
}
.game-meta {
    font-size: 12px;
    color: #999;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-top: 2px;
}
</style>
""", unsafe_allow_html=True)

    cols = st.columns(2)
    for i, item in enumerate(card_items):
        with cols[i % 2]:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 5, 1])
                with c1:
                    st.image(item["away_logo"], width=26)
                    st.image(item["home_logo"], width=26)
                with c2:
                    st.markdown(
                        f"<p class='game-matchup'>{item['away_abbr']} @ {item['home_abbr']}</p>"
                        f"<p class='game-meta'>{item['meta']}</p>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    if st.button(
                        "▶",
                        key=f"go_{item['gamePk']}",
                        use_container_width=True,
                        help=f"{item['away_name']} @ {item['home_name']}",
                    ):
                        st.session_state.selected_game_pk = item["gamePk"]
                        st.rerun()
