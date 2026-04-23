import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# TITLE
# =========================
st.title("⚾ MLB Dashboard")

# =========================
# CLOCK (ET)
# =========================
def get_now_et():
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")

st.sidebar.markdown("### 🕒 Current Eastern Time")
st.sidebar.write(get_now_et())
st.sidebar.markdown("---")

# =========================
# MODE
# =========================
mode = st.radio("Select Mode", ["Schedule", "Game Feed"])

# =========================
# HELPERS
# =========================
def convert_to_et(raw_time):
    if raw_time:
        try:
            dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            return dt.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")
        except:
            return None
    return None


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

    date = st.text_input("Enter date (YYYY-MM-DD)", "2026-04-22")

    if st.button("Load Games"):

        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
        data = requests.get(url).json()

        games = [
            {
                "gamePk": g["gamePk"],
                "matchup": f'{g["teams"]["away"]["team"]["name"]} @ {g["teams"]["home"]["team"]["name"]}',
                "time": convert_to_et(g.get("gameDate"))
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

    # =========================
    # INNING FILTER
    # =========================
    st.markdown("### 🧾 Inning Filter")

    inning_options = ["All"] + [str(i) for i in range(1, 10)] + ["Extra Innings"]
    selected_inning = st.selectbox("Select Inning", inning_options)

    if st.button("Load Game Feed"):

        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        data = requests.get(url).json()

        at_bats = []

        # =========================
        # BUILD PLAY DATA
        # =========================
        for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

            result_event = play.get("result", {}).get("event")
            result_desc = play.get("result", {}).get("description")

            away_score = play.get("result", {}).get("awayScore")
            home_score = play.get("result", {}).get("homeScore")

            start_time = convert_to_et(play.get("about", {}).get("startTime"))
            end_time = convert_to_et(play.get("about", {}).get("endTime"))

            inning = play.get("about", {}).get("inning")
            half_inning = play.get("about", {}).get("halfInning", "")

            inning_raw = inning if inning is not None else None

            if inning_raw is not None and inning_raw >= 10:
                inning_label = f"Extra Innings ({half_inning})"
            else:
                inning_label = f"{inning_raw} ({half_inning})" if inning_raw else "N/A"

            last_pitch_time = None
            for event in play.get("playEvents", []):
                if event.get("isPitch"):
                    last_pitch_time = convert_to_et(event.get("startTime"))

            # ✅ SCORE STORED PER PLAY (CORRECT STATE)
            play_info = {
                "atBatIndex": play.get("atBatIndex"),
                "batter": play.get("matchup", {}).get("batter", {}).get("fullName"),
                "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName"),
                "result": result_event,
                "desc": result_desc,
                "score": f"{away_score} - {home_score}",
                "startTime": start_time,
                "endTime": end_time,
                "lastPitchTime": last_pitch_time,
                "inning": inning_label,
                "inning_raw": inning_raw,
                "pitches": []
            }

            for event in play.get("playEvents", []):
                if event.get("isPitch"):
                    play_info["pitches"].append(
                        event.get("details", {}).get("description")
                    )

            at_bats.append(play_info)

        # =========================
        # FILTER LOGIC
        # =========================
        def inning_filter(ab):
            inning = ab.get("inning_raw")

            if selected_inning == "All":
                return True
            elif selected_inning == "Extra Innings":
                return inning is not None and inning >= 10
            else:
                return inning == int(selected_inning)

        filtered_at_bats = list(filter(inning_filter, at_bats))

        # =========================
        # OUTPUT
        # =========================
        for ab in filtered_at_bats:

            emoji = get_result_emoji(ab["result"], ab["desc"])

            st.subheader(f"{emoji} At Bat {ab['atBatIndex']}")

            # ✅ CORRECT SCORE (PER PLAY)
            st.write(f"🏟️ {ab['inning']} | 📊 {ab['score']}")

            st.write(f"👤 {ab['batter']} vs 🧢 {ab['pitcher']}")
            st.write(f"📌 Result: {ab['result']} - {ab['desc']}")

            st.write(f"🕒 At Bat Start Time: {ab['startTime']}")
            st.success(f"⚾ Last Pitch Thrown: {ab['lastPitchTime']}")
            st.write(f"🕒 At Bat End Time: {ab['endTime']}")

            st.markdown("### 🧩 Pitches")

            for i, p in enumerate(ab["pitches"], start=1):
                st.write(f"⚾ Pitch {i}: {p if p else '(no description)'}")

            st.divider()


# =========================
# FOOTER
# =========================
st.caption("⚾ MLB Dashboard – Accurate Game Feed View")
