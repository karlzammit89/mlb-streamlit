import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from streamlit_calendar import calendar

st.set_page_config(layout="wide")

# =========================
# TITLE
# =========================
st.title("⚾ MLB Interactive Dashboard")

# =========================
# SESSION STATE
# =========================
if "selected_game_pk" not in st.session_state:
    st.session_state.selected_game_pk = None

# =========================
# HELPERS
# =========================
def convert_to_et(raw_time):
    if not raw_time:
        return None
    try:
        dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo("America/New_York")).replace(microsecond=0)
    except:
        return None


def get_game_color(status):
    status = status.lower()
    if "final" in status:
        return "#6c757d"  # gray
    if "in progress" in status or "live" in status:
        return "#28a745"  # green
    return "#007bff"      # blue


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
    if "double" in text and "double play" not in text:
        return "🟢"
    if "triple" in text:
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
# DATE SELECTION
# =========================
selected_date = st.date_input("Select date", datetime.today())
date_str = selected_date.strftime("%Y-%m-%d")

# =========================
# LOAD SCHEDULE
# =========================
url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
data = requests.get(url).json()

events = []

for d in data.get("dates", []):
    for g in d.get("games", []):

        et_time = convert_to_et(g.get("gameDate"))
        status = g.get("status", {}).get("detailedState", "Scheduled")

        if not et_time:
            continue

        events.append({
            "title": f'{g["teams"]["away"]["team"]["name"]} @ {g["teams"]["home"]["team"]["name"]}',
            "start": et_time.isoformat(),
            "end": (et_time + timedelta(hours=3)).isoformat(),
            "id": str(g["gamePk"]),
            "color": get_game_color(status),
        })

# =========================
# CALENDAR VIEW
# =========================
st.subheader("📅 Game Calendar")

calendar_options = {
    "initialView": "dayGridMonth",
    "height": 650,
}

calendar_response = calendar(events=events, options=calendar_options)

# =========================
# HANDLE CLICK
# =========================
if calendar_response and calendar_response.get("eventClick"):
    game_id = calendar_response["eventClick"]["event"]["id"]
    st.session_state.selected_game_pk = game_id

# =========================
# GAME FEED
# =========================
if st.session_state.selected_game_pk:

    game_pk = st.session_state.selected_game_pk
    st.subheader(f"🎮 Game Feed: {game_pk}")

    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    data = requests.get(url).json()

    at_bats = []

    for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

        result_event = play.get("result", {}).get("event")
        result_desc = play.get("result", {}).get("description")

        away_score = play.get("result", {}).get("awayScore")
        home_score = play.get("result", {}).get("homeScore")

        inning = play.get("about", {}).get("inning")
        half_inning = play.get("about", {}).get("halfInning", "")

        pitches = []
        last_pitch_time = None

        for event in play.get("playEvents", []):
            if event.get("isPitch"):
                pitches.append(event.get("details", {}).get("description"))
                last_pitch_time = convert_to_et(event.get("startTime"))

        at_bats.append({
            "atBatIndex": play.get("atBatIndex"),
            "batter": play.get("matchup", {}).get("batter", {}).get("fullName"),
            "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName"),
            "result": result_event,
            "desc": result_desc,
            "score": f"{away_score} - {home_score}",
            "inning": inning,
            "half": half_inning,
            "pitches": pitches,
            "lastPitch": last_pitch_time
        })

    # =========================
    # DISPLAY FEED
    # =========================
    prev_score = None

    for ab in at_bats:

        emoji = get_result_emoji(ab["result"], ab["desc"])
        inning_label = f"{ab['inning']} ({ab['half']})"

        with st.container(border=True):
            st.subheader(f"{emoji} At Bat {ab['atBatIndex']}")

            if prev_score and prev_score != ab["score"]:
                st.write(f"🏟️ {inning_label} | 📊 {ab['score']} 🔥 SCORING PLAY")
            else:
                st.write(f"🏟️ {inning_label} | 📊 {ab['score']}")

            st.write(f"👤 {ab['batter']} vs 🧢 {ab['pitcher']}")
            st.write(f"📌 {ab['result']} — {ab['desc']}")

            if ab["lastPitch"]:
                st.caption(f"Last pitch: {ab['lastPitch']}")

            st.markdown("**Pitches:**")
            for i, p in enumerate(ab["pitches"], 1):
                st.write(f"{i}. {p}")

        prev_score = ab["score"]

    st.success(f"Loaded {len(at_bats)} at-bats")
