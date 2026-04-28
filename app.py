import streamlit as st
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =========================
# TITLE
# =========================
st.title("⚾ MLB Dashboard")

# =========================
# MODE
# =========================
mode = st.radio("Select Mode", ["Schedule", "Game Feed"])

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
# MODE 1 — SCHEDULE
# =========================
if mode == "Schedule":

    date = st.date_input("Select date", datetime.today())
    date_str = date.strftime("%Y-%m-%d")

    if st.button("Load Games"):

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

        if games:
            for game in games:
                time_only = game["time"].split(" ")[1][:5] if game["time"] else "N/A"
                st.write(f"{game['gamePk']} | ⚾ {game['matchup']} | 🕒 {time_only} (ET)")
        else:
            st.warning("No games found")


# =========================
# MODE 2 — GAME FEED
# =========================
if mode == "Game Feed":

    game_pk = st.text_input("Enter Game ID", "823878")

    USE_INNING_FILTER = st.checkbox("Filter by Inning", value=False)
    TARGET_INNINGS = []

    if USE_INNING_FILTER:
        TARGET_INNINGS = st.multiselect(
            "Select Innings",
            list(range(1, 10)) + ["Extra Innings"],
            default=[1]
        )

    USE_TIME_FILTER = st.checkbox("Filter by Actual Time (ET)", value=False)

    et_now = datetime.now(ZoneInfo("America/New_York"))

    today_start = et_now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = et_now.replace(hour=23, minute=59, second=0, microsecond=0)

    if "start_time" not in st.session_state:
        st.session_state.start_time = today_start.strftime("%Y-%m-%d %H:%M")

    if "end_time" not in st.session_state:
        st.session_state.end_time = today_end.strftime("%Y-%m-%d %H:%M")

    START_TIME = None
    END_TIME = None

    if USE_TIME_FILTER:
        START_TIME = st.text_input("Start Time (YYYY-MM-DD HH:MM)", st.session_state.start_time)
        END_TIME = st.text_input("End Time (YYYY-MM-DD HH:MM)", st.session_state.end_time)

    # =========================
    # LOAD GAME
    # =========================
    if st.button("Load Game Feed"):

        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        data = requests.get(url).json()

        at_bats = []

        START_DT = None
        END_DT = None

        if USE_TIME_FILTER and START_TIME and END_TIME:
            START_DT = datetime.fromisoformat(START_TIME).replace(tzinfo=ZoneInfo("America/New_York"))
            END_DT = datetime.fromisoformat(END_TIME).replace(tzinfo=ZoneInfo("America/New_York"))

        # =========================
        # BUILD PLAY DATA
        # =========================
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
        # FILTER
        # =========================
        def inning_filter(ab):
            inning = ab.get("inning")

            if not USE_INNING_FILTER:
                return True

            if inning is None:
                return False

            if "Extra Innings" in TARGET_INNINGS and inning >= 10:
                return True

            return inning in TARGET_INNINGS

        filtered_at_bats = []

        for ab in at_bats:

            if USE_TIME_FILTER and ab["startTime"] and START_DT and END_DT:
                ab_dt = convert_to_et(ab["startTime"])
                if not ab_dt or not (START_DT <= ab_dt <= END_DT):
                    continue

            if not inning_filter(ab):
                continue

            filtered_at_bats.append(ab)

        # =========================
        # OUTPUT
        # =========================
        prev_score = None

        for ab in filtered_at_bats:

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

        st.success(f"Loaded {len(filtered_at_bats)} events")
