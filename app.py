# =========================
# GAME FEED VIEW
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

    st.markdown(f"## 🎮 {away_team} @ {home_team}")

    # =========================
    # FILTER UI
    # =========================
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
    # APPLY FILTER BUTTON (FIX)
    # =========================
    apply_filters = st.button("🔄 Apply Filters")

    if apply_filters or "filtered_cache" not in st.session_state:

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
        # FILTER FUNCTION
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

            if USE_TIME_FILTER and START_DT and END_DT:
                raw_time = ab.get("startTime")
                ab_dt = convert_to_et(raw_time)

                if not ab_dt or not (START_DT <= ab_dt <= END_DT):
                    continue

            if not inning_filter(ab):
                continue

            filtered_at_bats.append(ab)

        st.session_state.filtered_cache = filtered_at_bats

    else:
        filtered_at_bats = st.session_state.get("filtered_cache", [])
