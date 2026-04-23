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
st.sidebar.write("Tip: Refresh for latest plays")

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
# MODE 2 — GAME FEED (ESPN STYLE)
# =========================
if mode == "Game Feed":

    game_pk = st.text_input("Enter Game ID", "823878")

    if st.button("Load Game Feed"):

        url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
        data = requests.get(url).json()

        at_bats = []

        for play in data.get("liveData", {}).get("plays", {}).get("allPlays", []):

            result_event = play.get("result", {}).get("event", "")
            result_desc = play.get("result", {}).get("description", "")

            away_score = play.get("result", {}).get("awayScore")
            home_score = play.get("result", {}).get("homeScore")

            inning = play.get("about", {}).get("inning")
            half_inning = play.get("about", {}).get("halfInning", "")
            inning_display = f"{inning} {half_inning.upper()}" if inning else "N/A"

            play_info = {
                "atBatIndex": play.get("atBatIndex"),
                "batter": play.get("matchup", {}).get("batter", {}).get("fullName"),
                "pitcher": play.get("matchup", {}).get("pitcher", {}).get("fullName"),
                "result": result_event,
                "desc": result_desc,
                "score": f"{away_score} - {home_score}",
                "inning": inning_display,
                "pitches": []
            }

            for event in play.get("playEvents", []):
                if event.get("isPitch"):
                    play_info["pitches"].append({
                        "desc": event.get("details", {}).get("description"),
                        "in_play": event.get("details", {}).get("isInPlay", False)
                    })

            at_bats.append(play_info)

        # =========================
        # OUTPUT
        # =========================
        prev_score = None

        for ab in at_bats:
            current_score = ab["score"]
            score_changed = current_score != prev_score and prev_score is not None

            result = (ab["result"] or "").lower()

            # ===== RESULT EMOJI =====
            if "home run" in result:
                result_emoji = "💥"
            elif "triple" in result or "double" in result:
                result_emoji = "🚀"
            elif "single" in result:
                result_emoji = "🟢"
            elif "strikeout" in result:
                result_emoji = "⚡"
            elif "walk" in result:
                result_emoji = "🚶"
            elif "out" in result:
                result_emoji = "🔴"
            else:
                result_emoji = "⚾"

            # ===== PLAY HEADER =====
            if score_changed:
                st.markdown(
                    f"### 🔥 {ab['inning']} | {current_score}  \n"
                    f"**{result_emoji} {ab['batter']} — {ab['result']}**  \n"
                    f"{ab['desc']}"
                )
                st.success("SCORING PLAY")
            else:
                st.markdown(
                    f"### {ab['inning']} | {current_score}  \n"
                    f"**{result_emoji} {ab['batter']} — {ab['result']}**  \n"
                    f"{ab['desc']}"
                )

            st.caption(f"vs {ab['pitcher']}")

            # ===== PITCH TIMELINE =====
            pitch_line = ""
            is_out = "out" in result

            for pitch in ab["pitches"]:
                desc = (pitch["desc"] or "").lower()

                if pitch["in_play"]:
                    pitch_line += "❌ " if is_out else "✅ "
                elif "strike" in desc:
                    pitch_line += "• "
                elif "ball" in desc:
                    pitch_line += "◦ "
                else:
                    pitch_line += "· "

            if pitch_line:
                st.write(f"**Pitches:** {pitch_line.strip()}")

            st.divider()

            prev_score = current_score


# =========================
# FOOTER
# =========================
st.caption("⚾ ESPN-style MLB tracker • Data from MLB Stats API")
