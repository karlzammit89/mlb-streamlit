import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# =========================
# TITLE
# =========================
st.title("⚾ MLB Dashboard")

# =========================
# CLOCK
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


def get_result_emoji(result_text: str):
    """Simple ESPN-style outcome mapping"""
    if not result_text:
        return "⚾"

    r = result_text.lower()

    if "home run" in r:
        return "💥"
    elif "strikeout" in r:
        return "⚡"
    elif "walk" in r or "base on balls" in r:
        return "🚶"
    elif "single" in r or "double" in r or "triple" in r or "hit" in r:
        return "🟢"
    elif "out" in r:
        return "❌"
    else:
        return "⚾"


# =========================
# SCHEDULE
# =========================
if mode == "Schedule":

    date = st.text_input("Enter date (YYYY-MM-DD)", "2026-04-22")

    if st.button("Load Games"):

        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
        data = requests.get(url).json()

        for d in data.get("dates", []):
            for g in d.get("games", []):

                time = convert_to_et(g.get("gameDate"))
                time_only = time.split(" ")[1][:5] if time else "N/A"

                matchup = f'{g["teams"]["away"]["team"]["name"]} @ {g["teams"]["home"]["team"]["name"]}'

                st.write(f"{g['gamePk']} | ⚾ {matchup} | 🕒 {time_only} (ET)")


# =========================
# GAME FEED (ESPN STYLE SIMPLE)
# =========================
if mode == "Game Feed":

    game_pk = st.text_input("Enter Game ID", "823878")

    if st.button("Load Game Feed"):

        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        data = requests.get(url).json()

        prev_score = None

        for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

            result = play.get("result", {}).get("event", "")
            desc = play.get("result", {}).get("description", "")

            away = play.get("result", {}).get("awayScore")
            home = play.get("result", {}).get("homeScore")
            score = f"{away} - {home}"

            inning = play.get("about", {}).get("inning")
            half = play.get("about", {}).get("halfInning", "")
            inning_display = f"{inning} {half.upper()}"

            batter = play.get("matchup", {}).get("batter", {}).get("fullName")
            pitcher = play.get("matchup", {}).get("pitcher", {}).get("fullName")

            # 🔥 score change detection
            score_changed = score != prev_score and prev_score is not None

            emoji = get_result_emoji(result)

            st.subheader(f"⚾ At Bat {play.get('atBatIndex')}")

            if score_changed:
                st.write(f"🏟️ {inning_display} | 📊 {score} 🔥")
            else:
                st.write(f"🏟️ {inning_display} | 📊 {score}")

            st.write(f"{emoji} **{batter}** vs 🧢 {pitcher}")
            st.write(f"📌 {result} - {desc}")

            # =========================
            # SIMPLE PITCH LINE (OUTCOME ONLY)
            # =========================
            pitch_line = ""

            for event in play.get("playEvents", []):
                if not event.get("isPitch"):
                    continue

                d = event.get("details", {})
                text = (d.get("description") or "").lower()

                if "strikeout" in text:
                    pitch_line += "⚡ "
                elif "home run" in text:
                    pitch_line += "💥 "
                elif "single" in text or "double" in text or "triple" in text or "hit" in text:
                    pitch_line += "🟢 "
                elif "out" in text:
                    pitch_line += "❌ "
                elif "walk" in text:
                    pitch_line += "🚶 "
                else:
                    pitch_line += "⚾ "

            if pitch_line:
                st.write(f"**Result Flow:** {pitch_line.strip()}")

            st.divider()

            prev_score = score


# =========================
# FOOTER
# =========================
st.caption("⚾ Simple ESPN-style MLB tracker")
