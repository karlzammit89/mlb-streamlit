import streamlit as st
import requests

st.title("⚾ MLB Schedule Viewer")

date = st.text_input("Enter date (YYYY-MM-DD)", "2026-04-22")

if st.button("Get Games"):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    data = requests.get(url, headers=headers).json()

    games = [
        f'{g["gamePk"]}: {g["teams"]["away"]["team"]["name"]} @ {g["teams"]["home"]["team"]["name"]}'
        for d in data.get("dates", [])
        for g in d.get("games", [])
    ]

    if games:
        for game in games:
            st.write(game)
    else:
        st.warning("No games found")
