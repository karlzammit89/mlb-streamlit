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
# TIME HELPERS (ET)
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
            "inning": raw_inning,   # ✅ KEEP REAL INNING NUMBER (IMPORTANT FIX)
            "half_inning": play.get("about", {}).get("halfInning"),
            "start_dt": start_dt,
            "end_dt": end_dt,
            "last_pitch_dt": last_pitch_dt,
        })

    # =========================
    # FILTER UI
    # =========================
    USE_INNING_FILTER = st.checkbox("Filter by Inning", value=False)

    def inning_group_label(inning):
        if inning is None:
            return None
        return "Extra Innings" if inning >= 10 else str(inning)

    all_innings = sorted(
        {inning_group_label(ab["inning"]) for ab in at_bats if ab["inning"] is not None},
        key=lambda x: (x == "Extra Innings", int(x) if x.isdigit() else 999)
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
    def inning_match(ab):
        if not USE_INNING_FILTER:
            return True
        if not selected_innings:
            return False

        label = "Extra Innings" if ab["inning"] >= 10 else str(ab["inning"])
        return label in selected_innings

    run_filters = st.button("🚀 Apply Filters")

    filtered = at_bats

    if run_filters:
        filtered = [ab for ab in at_bats if inning_match(ab)]

    # =========================
    # OUTPUT
    # =========================
    prev_score = None

    for ab in filtered:

        emoji = get_result_emoji(ab["result"], ab["desc"])
        inning_label = f"{ab['inning']} ({ab['half_inning']})"  # ✅ REAL INNING ALWAYS SHOWN

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
                "time": convert_to_et(g.get("gameDate")),
                "status": g.get("status", {}).get("detailedState", "Scheduled"),
                "away_score": g["teams"]["away"].get("score", 0),
                "home_score": g["teams"]["home"].get("score", 0),
            })

    cols = st.columns(2)

    for i, game in enumerate(games):

        with cols[i % 2]:
            st.markdown(
                f"**{game['away_name']} @ {game['home_name']}**  \n"
                f"🏷️ {game['status']} | 📊 {game['away_score']} - {game['home_score']}"
            )

            if st.button("▶ GO", key=f"go_{game['gamePk']}"):
                st.session_state.selected_game_pk = game["gamePk"]
                st.rerun()
