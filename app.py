import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# TITLE
# =========================
st.title("⚾ MLB Dashboard")

# =========================
# REAL TIME CLOCK (ET)
# =========================
def get_now_et():
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S %Z")

st.sidebar.markdown("### 🕒 Current Eastern Time")
st.sidebar.write(get_now_et())

st.sidebar.markdown("---")
st.sidebar.write("Auto-refresh updates timestamp")

# =========================
# MODE SELECTOR
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

    if "home run" in text or "homer" in text or "home_run" in text or "homerun" in text:
        return "💥"

    if "strikeout" in text or "struck out" in text:
        return "❌"

    if "walk" in text:
        return "🚶"

    if "single" in text:
        return "🟢"
    if "double" in text and "double play" not in text:
        return "🟢"
    if "triple" in text:
        return "🟢"

    if "double play" in text or "grounded into dp" in text or "dp:" in text:
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

    if st.button("Load Game Feed"):

        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        data = requests.get(url).json()

        at_bats = []

        for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

            result_event = play.get("result", {}).get("event")
            result_desc = play.get("result", {}).get("description")

            away_score = play.get("result", {}).get("awayScore")
            home_score = play.get("result", {}).get("homeScore")

            start_time = convert_to_et(play.get("about", {}).get("startTime"))

            # =========================
            # 1. OFFICIAL AT-BAT END TIME
            # =========================
            end_time = convert_to_et(play.get("about", {}).get("endTime"))

            inning = play.get("about", {}).get("inning")
            half_inning = play.get("about", {}).get("halfInning", "")
            inning_display = f"{inning} ({half_inning})" if inning else "N/A"

            # =========================
            # 2. LAST PITCH START TIME
            # =========================
            last_pitch_start_time = None

            for event in play.get("playEvents", []):
                if event.get("isPitch"):
                    last_pitch_start_time = convert_to_et(event.get("startTime"))

            play_info = {
                "atBatIndex": play.get("atBatIndex"),
                "batter": play.get("matchup", {}).get("batter", {}).get("fullName"),
                "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName"),
                "result": result_event,
                "desc": result_desc,
                "score": f"{away_score} - {home_score}",
                "startTime": start_time,
                "endTime": end_time,
                "lastPitchTime": last_pitch_start_time,
                "inning": inning_display,
                "pitches": []
            }

            for event in play.get("playEvents", []):
                if event.get("isPitch"):
                    play_info["pitches"].append(
                        event.get("details", {}).get("description")
                    )

            at_bats.append(play_info)

        # =========================
        # OUTPUT
        # =========================
        prev_score = None

        for ab in at_bats:

            current_score = ab["score"]
            score_changed = current_score != prev_score and prev_score is not None

            emoji = get_result_emoji(ab["result"], ab["desc"])

            st.subheader(f"{emoji} At Bat {ab['atBatIndex']}")

            if score_changed:
                st.write(f"🏟️ {ab['inning']} | 📊 {current_score} 🔥 SCORING PLAY 🔥")
            else:
                st.write(f"🏟️ {ab['inning']} | 📊 {current_score}")

            st.write(f"👤 {ab['batter']} vs 🧢 {ab['pitcher']}")
            st.write(f"📌 Result: {ab['result']} - {ab['desc']}")

            st.write(f"🕒 Start (ET): {ab['startTime']}")

            # =========================
            # BOTH TIMES (KEY FIX)
            # =========================
            st.write(f"🕒 At-Bat End (ET): {ab['endTime']}")
            st.write(f"⚾ Last Pitch Thrown (ET): {ab['lastPitchTime']}")

            st.success(f"⚾ Ball last in play at: {ab['lastPitchTime']}")

            st.markdown("### 🧩 Pitches")

            for i, p in enumerate(ab["pitches"], start=1):
                if p:
                    st.write(f"⚾ Pitch {i}: {p}")
                else:
                    st.write(f"⚾ Pitch {i}: (no description)")

            st.divider()

            prev_score = current_score
        # =========================
        # OUTPUT
        # =========================
        prev_score = None

        for ab in at_bats:

            current_score = ab["score"]
            score_changed = current_score != prev_score and prev_score is not None

            emoji = get_result_emoji(ab["result"], ab["desc"])

            st.subheader(f"{emoji} At Bat {ab['atBatIndex']}")

            if score_changed:
                st.write(f"🏟️ {ab['inning']} | 📊 {current_score} 🔥 SCORING PLAY 🔥")
            else:
                st.write(f"🏟️ {ab['inning']} | 📊 {current_score}")

            st.write(f"👤 {ab['batter']} vs 🧢 {ab['pitcher']}")
            st.write(f"📌 Result: {ab['result']} - {ab['desc']}")

            st.write(f"🕒 Start (ET): {ab['startTime']}")

            # =========================
            # ✅ FINAL FIX OUTPUT
            # =========================
            st.write(f"⚾ Last Pitch Thrown (ET): {ab['lastPitchTime']}")
            st.success(f"⚾ Ball last in play at: {ab['lastPitchTime']}")

            st.markdown("### 🧩 Pitches")

            for i, p in enumerate(ab["pitches"], start=1):
                if p:
                    st.write(f"⚾ Pitch {i}: {p}")
                else:
                    st.write(f"⚾ Pitch {i}: (no description)")

            st.divider()

            prev_score = current_score


# =========================
# FOOTER
# =========================
st.caption("Tip: refresh page to update live timestamps ⚾")
