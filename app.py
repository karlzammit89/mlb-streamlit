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
        # OUTPUT (ESPN STYLE)
        # =========================
        prev_score = None

        for ab in at_bats:
            current_score = ab["score"]
            score_changed = current_score != prev_score and prev_score is not None

            result = (ab["result"] or "").lower()

            # ===== RESULT EMOJI LOGIC =====
            if "home run" in result:
                result_emoji = "💥"
            elif "double" in result or "triple" in result:
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

            # ===== HEADER (LIKE ESPN PLAY) =====
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
                if not pitch["desc"]:
                    continue

                if pitch["in_play"]:
                    if is_out:
                        pitch_line += "❌ "
                    else:
                        pitch_line += "✅ "
                elif "strike" in pitch["desc"].lower():
                    pitch_line += "• "
                elif "ball" in pitch["desc"].lower():
                    pitch_line += "◦ "
                else:
                    pitch_line += "· "

            if pitch_line:
                st.write(f"**Pitches:** {pitch_line.strip()}")

            st.divider()

            prev_score = current_score
