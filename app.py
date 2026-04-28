import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# TITLE
# =========================
st.title("⚾ MLB Dashboard")

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

    # =========================
    # HEADER (RESTORED)
    # =========================
    c1, c2, c3 = st.columns([1, 4, 1])

    with c1:
        st.image(away_logo, width=60)

    with c2:
        st.markdown(
            f"""
            <div style="
                text-align: center;
                font-weight: 700;
                font-size: clamp(14px, 2.2vw, 24px);
                line-height: 1.4;
            ">
                {away_team} {away_score} - {home_score} {home_team}
                <br>
                <span style="font-size: 14px; font-weight: 500;">
                    {data.get("gameData", {}).get("status", {}).get("detailedState", "Unknown")}
                </span>
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

        for event in play.get("playEvents", []):
            if event.get("isPitch"):
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

        st.divider()

        prev_score = score

# =========================
# SCHEDULE VIEW
# =========================
else:

    date = st.date_input("Select date", datetime.today())
    date_str = date.strftime("%Y-%m-%d")

    st.markdown(f"## 📅 MLB Schedule — {date_str}")

    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
    data = requests.get(url).json()

    games = []

    for d in data.get("dates", []):
        for g in d.get("games", []):

            away = g["teams"]["away"]["team"]
            home = g["teams"]["home"]["team"]

            games.append({
                "gamePk": g["gamePk"],
                "away_name": away["name"],
                "home_name": home["name"],
                "away_logo": f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away['id']}.svg",
                "home_logo": f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home['id']}.svg",
                "time": convert_to_et(g.get("gameDate")),
                "status": g.get("status", {}).get("detailedState", "Scheduled"),
                "away_score": g["teams"]["away"].get("score", 0),
                "home_score": g["teams"]["home"].get("score", 0),
            })

    cols = st.columns(2)

    for i, game in enumerate(games):

        with cols[i % 2]:

            time_str = format_et(game["time"])

            status_line = (
                f"🏷️ {game['status']} | 📊 {game['away_score']} - {game['home_score']}"
                if game["status"].lower() != "scheduled"
                else f"🏷️ {game['status']}"
            )

            with st.container(border=True):

                c1, c2, c3 = st.columns([1, 5, 1])

                with c1:
                    st.image(game["away_logo"], width=26)
                    st.image(game["home_logo"], width=26)

                with c2:
                    st.markdown(
                        f"**{game['away_name']} @ {game['home_name']}**  \n"
                        f"🕒 {time_str} | {status_line}"
                    )

                with c3:
                    if st.button("▶ GO", key=f"go_{game['gamePk']}", use_container_width=True):
                        st.session_state.selected_game_pk = game["gamePk"]
                        st.rerun()
