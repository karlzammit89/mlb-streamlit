import streamlit as st
import requests
from datetime import datetime, timedelta
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

if "games" not in st.session_state:
    st.session_state.games = []


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


def convert_to_et_str(raw_time):
    dt = convert_to_et(raw_time)
    if not dt:
        return None

    is_dst = dt.dst() != timedelta(0)
    tz_label = "EDT" if is_dst else "EST"

    return dt.strftime(f"%Y-%m-%d %H:%M:%S {tz_label}")


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
# GAME FEED VIEW (FULL SCREEN REPLACE)
# =========================
if st.session_state.selected_game_pk:

    game_pk = st.session_state.selected_game_pk

    if st.button("⬅ Back to Schedule"):
        st.session_state.selected_game_pk = None
        st.rerun()

    st.markdown(f"## 🎮 Game Feed: {game_pk}")

    USE_INNING_FILTER = st.checkbox("Filter by Inning", value=False)
    TARGET_INNINGS = []

    if USE_INNING_FILTER:
        TARGET_INNINGS = st.multiselect(
            "Select Innings",
            list(range(1, 10)) + ["Extra Innings"],
            default=[1]
        )

    USE_TIME_FILTER = st.checkbox("Filter by Actual Time (ET)", value=False)

    START_DT = None
    END_DT = None

    if USE_TIME_FILTER:

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input("Start Date", datetime.today(), key="start_date")
            start_time = st.time_input("Start Time", datetime.now().time(), key="start_time")

        with col2:
            end_date = st.date_input("End Date", datetime.today(), key="end_date")
            end_time = st.time_input("End Time", datetime.now().time(), key="end_time")

        START_DT = datetime.combine(start_date, start_time).replace(tzinfo=ZoneInfo("America/New_York"))
        END_DT = datetime.combine(end_date, end_time).replace(tzinfo=ZoneInfo("America/New_York"))

    # =========================
    # LOAD GAME FEED
    # =========================
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    data = requests.get(url).json()

    at_bats = []

    for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

        start_time = convert_to_et_str(play.get("about", {}).get("startTime"))
        end_time = convert_to_et_str(play.get("about", {}).get("endTime"))

        result_event = play.get("result", {}).get("event")
        result_desc = play.get("result", {}).get("description")

        away_score = play.get("result", {}).get("awayScore")
        home_score = play.get("result", {}).get("homeScore")

        inning = play.get("about", {}).get("inning")
        half_inning = play.get("about", {}).get("halfInning", "")

        last_pitch_time = None
        pitches = []

        for event in play.get("playEvents", []):
            if event.get("isPitch"):
                pitches.append(event.get("details", {}).get("description"))
                last_pitch_time = convert_to_et_str(event.get("startTime"))

        at_bats.append({
            "atBatIndex": play.get("atBatIndex"),
            "batter": play.get("matchup", {}).get("batter", {}).get("fullName"),
            "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName"),
            "result": result_event,
            "desc": result_desc,
            "score": f"{away_score} - {home_score}",
            "startTime": start_time,
            "endTime": end_time,
            "lastPitchTime": last_pitch_time,
            "inning": inning,
            "half_inning": half_inning,
            "pitches": pitches
        })

    # =========================
    # OUTPUT
    # =========================
    prev_score = None

    for ab in at_bats:

        emoji = get_result_emoji(ab["result"], ab["desc"])
        inning_label = f"{ab['inning']} ({ab['half_inning']})" if ab["inning"] else "N/A"

        st.subheader(f"{emoji} At Bat {ab['atBatIndex']}")

        if ab["score"] != prev_score and prev_score is not None:
            st.write(f"🏟️ {inning_label} | 📊 {ab['score']} 🔥 SCORING PLAY 🔥")
        else:
            st.write(f"🏟️ {inning_label} | 📊 {ab['score']}")

        st.write(f"👤 {ab['batter']} vs 🧢 {ab['pitcher']}")
        st.write(f"📌 Result: {ab['result']} - {ab['desc']}")

        st.write(f"🕒 At Bat Start Time: {ab['startTime']}")
        st.success(f"🕒 Last Pitch Thrown: {ab['lastPitchTime']}")
        st.write(f"🕒 At Bat End Time: {ab['endTime']}")

        st.markdown("### 🧩 Pitches")
        for i, p in enumerate(ab["pitches"], start=1):
            st.write(f"⚾ Pitch {i}: {p if p else '(no description)'}")

        st.divider()

        prev_score = ab["score"]


# =========================
# SCHEDULE VIEW (AUTO LOAD ON DATE CHANGE)
# =========================
else:

    date = st.date_input("Select date", datetime.today())
    date_str = date.strftime("%Y-%m-%d")

    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}"
    data = requests.get(url).json()

    games = [
        {
            "gamePk": g["gamePk"],
            "matchup": f'{g["teams"]["away"]["team"]["name"]} @ {g["teams"]["home"]["team"]["name"]}',
            "time": convert_to_et_str(g.get("gameDate"))
        }
        for d in data.get("dates", [])
        for g in d.get("games", [])
    ]

    st.session_state.games = games

    if games:

        st.markdown("### 📅 Games")

        for game in games:

            time_only = game["time"].split(" ")[1][:5] if game["time"] else "N/A"

            with st.container():

                if st.button(
                    f"⚾ {game['matchup']} | 🕒 {time_only} (ET) | ID: {game['gamePk']}",
                    key=f"game_{game['gamePk']}"
                ):
                    st.session_state.selected_game_pk = game["gamePk"]
                    st.rerun()

            st.divider()

    else:
        st.warning("No games found for this date")
