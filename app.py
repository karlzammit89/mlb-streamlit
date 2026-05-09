import streamlit as st
import requests
from datetime import datetime, time as dtime, date as ddate
from zoneinfo import ZoneInfo

# =========================
# PAGE CONFIG & TITLE
# =========================
st.set_page_config(page_title="MLB Dashboard", page_icon="⚾", layout="wide")
st.title("⚾ MLB Dashboard")

# Monday-first calendar via JS locale override
st.components.v1.html("""
<script>
(function() {
    const orig = Intl.DateTimeFormat;
    Intl.DateTimeFormat = function(l, o) { return new orig('en-GB', o); };
    Intl.DateTimeFormat.supportedLocalesOf = orig.supportedLocalesOf.bind(orig);
})();
</script>
""", height=0)

# =========================
# CONSTANTS
# =========================
ET = ZoneInfo("America/New_York")

TEAM_ABBREV = {
    "Arizona Diamondbacks": "ARI", "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL", "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC", "Chicago White Sox": "CWS",
    "Cincinnati Reds": "CIN", "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL", "Detroit Tigers": "DET",
    "Houston Astros": "HOU", "Kansas City Royals": "KC",
    "Los Angeles Angels": "LAA", "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA", "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN", "New York Mets": "NYM",
    "New York Yankees": "NYY", "Oakland Athletics": "OAK",
    "Philadelphia Phillies": "PHI", "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SD", "San Francisco Giants": "SF",
    "Seattle Mariners": "SEA", "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TB", "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR", "Washington Nationals": "WSH",
}

RESULT_EMOJI = {
    "home run": "💥", "strikeout": "❌", "walk": "🚶",
    "single": "🟢", "double play": "❌", "error": "🟡",
    "stolen base": "🏃", "out": "❌",
}

PITCH_EMOJI = {
    "ball": "🔵", "called strike": "🔴", "swinging strike": "🔴",
    "foul": "🟡", "in play": "⚾", "hit by pitch": "🤕",
}

# =========================
# SESSION STATE
# =========================
if "selected_game_pk" not in st.session_state:
    st.session_state.selected_game_pk = None
if "schedule_date" not in st.session_state:
    st.session_state.schedule_date = datetime.today().date()

# =========================
# HELPERS
# =========================
def abbrev(name: str) -> str:
    return TEAM_ABBREV.get(name, name[:3].upper())

def to_et(raw: str):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(ET)
    except Exception:
        return None

def fmt_et(dt) -> str:
    return dt.strftime("%H:%M ET") if dt else "TBD"

def fmt_full_et(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S ET") if dt else "N/A"

def result_emoji(event: str, desc: str = "") -> str:
    text = f"{event or ''} {desc or ''}".lower()
    for k, v in RESULT_EMOJI.items():
        if k in text:
            return v
    return "⚾"

def pitch_emoji(call: str) -> str:
    r = (call or "").lower()
    for k, v in PITCH_EMOJI.items():
        if k in r:
            return v
    return "⚪"

# =========================
# CACHED API CALLS
# =========================
@st.cache_data(ttl=60, show_spinner=False)
def fetch_game(game_pk: int) -> dict:
    return requests.get(
        f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live",
        timeout=10,
    ).json()

@st.cache_data(ttl=300, show_spinner=False)
def fetch_schedule(date_str: str) -> dict:
    return requests.get(
        f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}",
        timeout=10,
    ).json()

# =========================
# AT-BAT PARSER (cached per game_pk)
# =========================
@st.cache_data(ttl=60, show_spinner=False)
def parse_at_bats(game_pk: int):
    data = fetch_game(game_pk)
    at_bats = []
    prev_total = 0

    for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):
        about   = play.get("about", {})
        result  = play.get("result", {})
        matchup = play.get("matchup", {})

        start_dt      = to_et(about.get("startTime"))
        end_dt        = to_et(about.get("endTime"))
        last_pitch_dt = None
        pitches       = []

        for ev in play.get("playEvents", []):
            if not ev.get("isPitch"):
                continue
            details = ev.get("details", {})
            count   = ev.get("count", {})
            p_time  = to_et(ev.get("startTime"))
            pitches.append({
                "num":            len(pitches) + 1,
                "pitch_name":     details.get("type", {}).get("description", "Unknown"),
                "call":           details.get("description", ""),
                "speed_mph":      ev.get("pitchData", {}).get("startSpeed"),
                "balls":          count.get("balls", 0),
                "strikes":        count.get("strikes", 0),
                "start_time":     p_time,
                "start_time_str": fmt_full_et(p_time),
            })
            last_pitch_dt = p_time

        away_sc  = result.get("awayScore", 0)
        home_sc  = result.get("homeScore", 0)
        total    = (away_sc or 0) + (home_sc or 0)
        raw_inn  = about.get("inning") or 0

        at_bats.append({
            "atBatIndex":      play.get("atBatIndex"),
            "batter":          matchup.get("batter", {}).get("fullName", ""),
            "pitcher":         matchup.get("pitcher", {}).get("fullName", ""),
            "result":          result.get("event", ""),
            "desc":            result.get("description", ""),
            "away_score":      away_sc,
            "home_score":      home_sc,
            "inning_raw":      raw_inn,
            "inning_group":    "Extra Innings" if raw_inn >= 10 else raw_inn,
            "half_inning":     about.get("halfInning", ""),
            "start_dt":        start_dt,
            "end_dt":          end_dt,
            "last_pitch_dt":   last_pitch_dt,
            "pitches":         pitches,
            "is_scoring_play": total > prev_total,
            "score_str":       f"{away_sc} - {home_sc}",
            "start_dt_str":    fmt_full_et(start_dt),
            "end_dt_str":      fmt_full_et(end_dt),
            "last_pitch_str":  fmt_full_et(last_pitch_dt),
        })
        prev_total = total

    return data, at_bats

# =========================
# SCHEDULE PARSER (cached)
# =========================
@st.cache_data(ttl=300, show_spinner=False)
def parse_schedule(date_str: str):
    data = fetch_schedule(date_str)
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            away    = g["teams"]["away"]["team"]
            home    = g["teams"]["home"]["team"]
            away_ab = abbrev(away["name"])
            home_ab = abbrev(home["name"])
            status  = g.get("status", {}).get("detailedState", "Scheduled")
            game_dt = to_et(g.get("gameDate"))
            time_s  = fmt_et(game_dt)
            away_sc      = g["teams"]["away"].get("score", 0)
            home_sc      = g["teams"]["home"].get("score", 0)
            innings      = g.get("linescore", {}).get("currentInning", 9) or 9
            extra_inn    = innings > 9

            games.append({
                "gamePk":        g["gamePk"],
                "away_name":     away["name"],
                "home_name":     home["name"],
                "away_abbr":     away_ab,
                "home_abbr":     home_ab,
                "away_logo":     f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away['id']}.svg",
                "home_logo":     f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home['id']}.svg",
                "time_str":      time_s,
                "status":        status,
                "away_score":    away_sc,
                "home_score":    home_sc,
                "innings":       innings,
                "extra_innings": extra_inn,
            })
    return games

# ======================================================
# GAME VIEW
# ======================================================
if st.session_state.selected_game_pk:

    game_pk = st.session_state.selected_game_pk

    if st.button("⬅ Back to Schedule"):
        st.session_state.selected_game_pk = None
        st.rerun()

    with st.spinner("Loading game data…"):
        data, at_bats = parse_at_bats(game_pk)

    gd      = data.get("gameData", {})
    teams   = gd.get("teams", {})
    home_t  = teams.get("home", {})
    away_t  = teams.get("away", {})
    home_id = home_t.get("id")
    away_id = away_t.get("id")
    home_ab = abbrev(home_t.get("name", "Home"))
    away_ab = abbrev(away_t.get("name", "Away"))

    ls        = data.get("liveData", {}).get("linescore", {})
    home_runs = ls.get("teams", {}).get("home", {}).get("runs", 0)
    away_runs = ls.get("teams", {}).get("away", {}).get("runs", 0)

    # --- Header ---
    c1, c2, c3 = st.columns([1, 6, 1])
    with c1:
        st.image(f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away_id}.svg", width=60)
    with c2:
        st.markdown(
            f"""<div style="display:flex;align-items:center;justify-content:center;
                font-weight:700;font-size:clamp(16px,2.6vw,28px);gap:10px;flex-wrap:wrap;text-align:center;">
                <span>{away_ab}</span><span style="color:#888;">{away_runs}</span>
                <span>-</span>
                <span style="color:#888;">{home_runs}</span><span>{home_ab}</span>
            </div>""",
            unsafe_allow_html=True,
        )
    with c3:
        st.image(f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home_id}.svg", width=60)

    st.divider()

    # --- Filter defaults ---
    game_start_raw     = gd.get("datetime", {}).get("dateTime")
    game_start_default = to_et(game_start_raw)
    all_end_dts        = [ab["end_dt"] for ab in at_bats if ab["end_dt"]]
    game_end_default   = max(all_end_dts) if all_end_dts else None
    if not game_start_default:
        all_start_dts      = [ab["start_dt"] for ab in at_bats if ab["start_dt"]]
        game_start_default = min(all_start_dts) if all_start_dts else None

    # --- Filters ---
    USE_INNING_FILTER  = st.checkbox("🏟️ Filter by Inning",          value=False)
    USE_TIME_FILTER    = st.checkbox("🕐 Filter by Actual Time (ET)", value=False)
    USE_SCORING_FILTER = st.checkbox("🔥 Scoring Plays Only",         value=False)

    START_DT = END_DT = None
    selected_innings  = []

    if USE_INNING_FILTER:
        all_innings = sorted(
            {ab["inning_group"] for ab in at_bats if ab["inning_group"] is not None},
            key=lambda x: (x == "Extra Innings", x if isinstance(x, int) else 999),
        )
        selected_innings = st.multiselect("Select innings", options=all_innings, default=[])

    if USE_TIME_FILTER:
        def_start_date = game_start_default.date() if game_start_default else ddate.today()
        def_end_date   = game_end_default.date()   if game_end_default   else ddate.today()
        def_start_time = game_start_default.time() if game_start_default else dtime(12, 0)
        def_end_time   = game_end_default.time()   if game_end_default   else dtime(23, 59)

        st.markdown("**Start date/time (ET)**")
        sc1, sc2 = st.columns(2)
        with sc1:
            start_date_input = st.date_input("Start date", value=def_start_date, key="tf_start_date")
        with sc2:
            start_time_input = st.time_input("Start time", value=def_start_time, step=60, key="tf_start_time")

        st.markdown("**End date/time (ET)**")
        ec1, ec2 = st.columns(2)
        with ec1:
            end_date_input = st.date_input("End date", value=def_end_date, key="tf_end_date")
        with ec2:
            end_time_input = st.time_input("End time", value=def_end_time, step=60, key="tf_end_time")

        START_DT = datetime.combine(start_date_input, start_time_input).replace(tzinfo=ET)
        END_DT   = datetime.combine(end_date_input,   end_time_input).replace(tzinfo=ET)

    run_filters = st.button("🚀 Apply Filters")

    def passes(ab):
        if USE_INNING_FILTER:
            if not selected_innings or ab["inning_group"] not in selected_innings:
                return False
        if USE_TIME_FILTER:
            if not ab["start_dt"] or START_DT is None or END_DT is None:
                return False
            if not (START_DT <= ab["start_dt"] <= END_DT):
                return False
        if USE_SCORING_FILTER and not ab["is_scoring_play"]:
            return False
        return True

    filtered = at_bats if not run_filters else [ab for ab in at_bats if passes(ab)]

    # --- Info banners ---
    if run_filters:
        total   = len(at_bats)
        showing = len(filtered)

        if showing == 0:
            st.warning("⚠️ No results found — please check the filters applied.")
            st.stop()

        if USE_INNING_FILTER:
            labels = [str(i) for i in selected_innings] if selected_innings else ["none selected"]
            st.info(f"🏟️ **Inning filter:** Innings {', '.join(labels)} — showing **{showing}** of **{total}** at-bats")

        if USE_TIME_FILTER:
            st.info(
                f"🕐 **Time filter:** {START_DT.strftime('%Y-%m-%d %H:%M')} → "
                f"{END_DT.strftime('%Y-%m-%d %H:%M')} ET — showing **{showing}** of **{total}** at-bats"
            )

        if USE_SCORING_FILTER:
            n_scoring = sum(1 for ab in at_bats if ab["is_scoring_play"])
            st.info(f"🔥 **Scoring plays filter:** {n_scoring} scoring play(s) in game — showing **{showing}** of **{total}** at-bats")

    # --- Output ---
    for ab in filtered:
        emoji      = result_emoji(ab["result"], ab["desc"])
        half       = ab["half_inning"].capitalize()
        inning_lbl = f"{half} {ab['inning_raw']}"

        st.subheader(f"{emoji} At Bat #{ab['atBatIndex']}")

        if ab["is_scoring_play"]:
            st.markdown(f"🏟️ **Inning:** {inning_lbl} &nbsp;|&nbsp; 📊 **Score:** {ab['score_str']} &nbsp; 🔥 *Scoring Play!*")
        else:
            st.markdown(f"🏟️ **Inning:** {inning_lbl} &nbsp;|&nbsp; 📊 **Score:** {ab['score_str']}")

        st.markdown(f"👤 **Batter:** {ab['batter']} &nbsp;|&nbsp; 🧢 **Pitcher:** {ab['pitcher']}")
        st.markdown(f"📋 **Result:** {ab['result']}")
        st.caption(f"📝 {ab['desc']}")

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.markdown(f"🕐 **At Bat Start**  \n`{ab['start_dt_str']}`")
        with col_t2:
            st.markdown(f"⚡ **Last Pitch**  \n`{ab['last_pitch_str']}`")
        with col_t3:
            st.markdown(f"🕔 **At Bat End**  \n`{ab['end_dt_str']}`")

        if ab["pitches"]:
            with st.expander(f"🎯 Pitch-by-Pitch — {len(ab['pitches'])} pitches"):
                for p in ab["pitches"]:
                    speed_str = f"  🗲 {p['speed_mph']:.1f} mph" if p["speed_mph"] else ""
                    st.markdown(
                        f"{pitch_emoji(p['call'])} **Pitch {p['num']}** — 📌 {p['pitch_name']}{speed_str}  \n"
                        f"&nbsp;&nbsp;&nbsp;&nbsp;📣 *{p['call']}* &nbsp;|&nbsp; "
                        f"⚖️ Count: **{p['balls']}-{p['strikes']}**"
                        + (f" &nbsp;|&nbsp; 🕒 {p['start_time_str']}" if p["start_time"] else "")
                    )

        st.divider()

# ======================================================
# SCHEDULE VIEW
# ======================================================
else:

    date     = st.date_input("Select date", st.session_state.schedule_date, format="YYYY-MM-DD")
    st.session_state.schedule_date = date
    date_str = date.strftime("%Y-%m-%d")
    st.markdown(f"## MLB Schedule — {date_str}")

    with st.spinner("Loading schedule…"):
        games = parse_schedule(date_str)

    if not games:
        st.info("No games scheduled for this date.")
        st.stop()

    # Card inner content uses unsafe_allow_html inside st.container(border=True).
    # The border/click is handled by native Streamlit — no iframe, no JS bridge needed.
    st.markdown("""
<style>
/* Uniform card height */
div[data-testid="stVerticalBlockBorderWrapper"] {
    min-height: 150px;
}
.sched-team-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
}
.sched-team-row img {
    width: 34px;
    height: 34px;
    object-fit: contain;
}
.sched-team-name {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 0.4px;
}
.sched-score {
    font-size: 22px;
    font-weight: 800;
    color: #aaa;
    margin-left: auto;
}
.sched-meta {
    font-size: 13px;
    color: #999;
    margin-top: 4px;
    border-top: 1px solid rgba(255,255,255,0.08);
    padding-top: 5px;
}
.sched-extra {
    display: inline-block;
    background: #e67e22;
    color: #fff;
    font-size: 11px;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 6px;
    vertical-align: middle;
    letter-spacing: 0.5px;
}
</style>
""", unsafe_allow_html=True)

    cols = st.columns(2)
    for i, g in enumerate(games):
        is_live_or_final = g["status"].lower() not in ("scheduled", "pre-game", "warmup")

        away_score_html = f'<span class="sched-score">{g["away_score"]}</span>' if is_live_or_final else ""
        home_score_html = f'<span class="sched-score">{g["home_score"]}</span>' if is_live_or_final else ""

        # Meta line: time + status only — score already shown inline on each team row
        # Extra innings badge shown when game went past 9
        extra_badge = ' <span class="sched-extra">F/OT</span>' if g.get("extra_innings") and is_live_or_final else ""
        if is_live_or_final:
            meta = f'{g["time_str"]} &middot; {g["status"]}{extra_badge}'
        else:
            meta = f'{g["time_str"]} &middot; {g["status"]}'

        inner_html = f"""
<div class="sched-team-row">
  <img src="{g['away_logo']}" />
  <span class="sched-team-name">{g['away_abbr']}</span>
  {away_score_html}
</div>
<div class="sched-team-row">
  <img src="{g['home_logo']}" />
  <span class="sched-team-name">{g['home_abbr']}</span>
  {home_score_html}
</div>
<div class="sched-meta">{meta}</div>
"""

        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(inner_html, unsafe_allow_html=True)
                if st.button(
                    f"▶  Open  {g['away_abbr']} @ {g['home_abbr']}",
                    key=f"go_{g['gamePk']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_game_pk = g["gamePk"]
                    st.rerun()
