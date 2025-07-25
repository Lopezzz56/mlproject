import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none" 

import streamlit as st
# Setup
st.set_page_config(page_title="⚽ Football Analytics Dashboard", layout="wide")
st.title("📊 Football Analytics Dashboard")

import sqlite3
import pandas as pd
import plotly.express as px
import urllib.request




db_url = "https://storage.googleapis.com/mlproject_56/database.sqlite/database.sqlite"
local_path = "database.sqlite"

# Download if not already present
if not os.path.exists(local_path):
    urllib.request.urlretrieve(db_url, local_path)

# Connect to the downloaded database
conn = sqlite3.connect(local_path)


# Load Data
teams_df = pd.read_sql("SELECT team_long_name, team_api_id FROM Team", conn)
matches_df = pd.read_sql("SELECT * FROM Match", conn)
players_df = pd.read_sql("SELECT * FROM Player", conn)
player_attrs_df = pd.read_sql("SELECT * FROM Player_Attributes", conn)
league_df = pd.read_sql("SELECT * FROM League", conn)

# Tabs
tab1, tab2, tab3 = st.tabs(["🏟️ Team Analysis", "🌍 League Comparison", "🧍 Player Analysis"])

# -------------------- TAB 1: TEAM ANALYSIS --------------------
with tab1:
    st.header("🏟️ Team-Level Analysis")

    selected_team = st.selectbox("Select a Team", teams_df["team_long_name"].unique())

    team_id = teams_df[teams_df["team_long_name"] == selected_team]["team_api_id"].values[0]
    team_matches = matches_df[(matches_df["home_team_api_id"] == team_id) | (matches_df["away_team_api_id"] == team_id)].copy()

    # Label Results
    def get_result(row):
        if row["home_team_api_id"] == team_id:
            if row["home_team_goal"] > row["away_team_goal"]: return "Win"
            elif row["home_team_goal"] < row["away_team_goal"]: return "Loss"
            else: return "Draw"
        else:
            if row["away_team_goal"] > row["home_team_goal"]: return "Win"
            elif row["away_team_goal"] < row["home_team_goal"]: return "Loss"
            else: return "Draw"

    team_matches["result"] = team_matches.apply(get_result, axis=1)

    # Stats
    wins = team_matches[team_matches["result"] == "Win"].shape[0]
    draws = team_matches[team_matches["result"] == "Draw"].shape[0]
    losses = team_matches[team_matches["result"] == "Loss"].shape[0]

    home_wins = team_matches[(team_matches["home_team_api_id"] == team_id) & 
                             (team_matches["home_team_goal"] > team_matches["away_team_goal"])].shape[0]

    away_wins = team_matches[(team_matches["away_team_api_id"] == team_id) & 
                             (team_matches["away_team_goal"] > team_matches["home_team_goal"])].shape[0]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🏆 Wins", wins)
    col2.metric("🤝 Draws", draws)
    col3.metric("💔 Losses", losses)
    col4.metric("🏠 Home Wins", home_wins)
    col5.metric("✈️ Away Wins", away_wins)

    st.markdown("### 📈 Match Result Distribution")
    result_counts = team_matches["result"].value_counts()
    fig = px.pie(values=result_counts.values, names=result_counts.index, title="Match Results")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🎯 Goals per Match")
    team_matches["team_goals"] = team_matches.apply(
        lambda row: row["home_team_goal"] if row["home_team_api_id"] == team_id else row["away_team_goal"], axis=1)
    st.line_chart(team_matches["team_goals"])

# -------------------- TAB 2: LEAGUE COMPARISON --------------------
with tab2:
    st.header("🌍 League-wide Analysis")

    # Merge matches with league info
    matches_with_league = matches_df.merge(league_df, left_on="league_id", right_on="id", how="left")

    # Total goals per match
    matches_with_league["total_goals"] = matches_with_league["home_team_goal"] + matches_with_league["away_team_goal"]

    # Average goals per league
    league_avg_goals = matches_with_league.groupby("name")["total_goals"].mean().reset_index()
    league_avg_goals.columns = ["League", "Avg Goals per Match"]

    # Plot average goals
    st.markdown("### ⚽ Average Goals per Match by League")
    fig = px.bar(league_avg_goals, x="League", y="Avg Goals per Match", color="Avg Goals per Match", title="League Goal Averages")
    st.plotly_chart(fig, use_container_width=True)

    # Home win percentage
    matches_with_league["home_win"] = matches_with_league["home_team_goal"] > matches_with_league["away_team_goal"]
    league_win_pct = matches_with_league.groupby("name")["home_win"].mean().reset_index()
    league_win_pct.columns = ["League", "Home Win %"]
    league_win_pct["Home Win %"] = league_win_pct["Home Win %"] * 100

    st.markdown("### 🏅 Home Win Percentages by League")
    fig2 = px.bar(league_win_pct, x="League", y="Home Win %", color="Home Win %", title="Home Win % by League")
    st.plotly_chart(fig2, use_container_width=True)
    # Add more league comparisons:
    
    # Merge match and league
    matches_df = matches_df.merge(league_df, on="id")
    # Total matches per league
    total_matches = matches_df.groupby("name")["id"].count().reset_index(name="Total Matches")

    # Average goals per match
    matches_df["Total Goals"] = matches_df["home_team_goal"] + matches_df["away_team_goal"]
    avg_goals = matches_df.groupby("name")["Total Goals"].mean().reset_index(name="Avg Goals per Match")

    # Win percentage of home team
    home_wins = (matches_df["home_team_goal"] > matches_df["away_team_goal"]).groupby(matches_df["name"]).mean().reset_index(name="Home Win %")

    # Goals scored vs conceded per league
    matches_df["Goals Scored"] = matches_df["home_team_goal"] + matches_df["away_team_goal"]
    matches_df["Goals Conceded"] = matches_df["away_team_goal"] + matches_df["home_team_goal"]
    goals_summary = matches_df.groupby("name")[["Goals Scored", "Goals Conceded"]].mean().reset_index()

    # Top team per league (by average goals scored per match)
    top_teams = matches_df.copy()
    top_teams["team"] = top_teams["home_team_api_id"]
    top_teams = top_teams.groupby(["name", "team"])["Total Goals"].mean().reset_index()
    top_teams = top_teams.sort_values(["name", "Total Goals"], ascending=[True, False])
    top_teams = top_teams.merge(teams_df, left_on="team", right_on="team_api_id").drop_duplicates("name")
    top_teams = top_teams[["name", "team_long_name", "Total Goals"]].rename(columns={"team_long_name": "Top Team", "Total Goals": "Avg Goals"})

    # Combine all metrics
    league_stats = total_matches.merge(avg_goals, on="name")
    league_stats = league_stats.merge(home_wins, on="name")
    league_stats = league_stats.merge(goals_summary, on="name")
    league_stats = league_stats.merge(top_teams, on="name")

    # Streamlit UI
    st.title("📊 League Comparison Dashboard")
    st.subheader("🏆 League Metrics Overview")
    st.dataframe(league_stats)

    st.subheader("📈 Avg Goals & Win Percentage")
    st.bar_chart(league_stats.set_index("name")[["Avg Goals per Match", "Home Win %"]])

    st.subheader("🥅 Goals Scored vs Conceded")
    st.bar_chart(league_stats.set_index("name")[["Goals Scored", "Goals Conceded"]])

    st.subheader("👑 Top Team per League")
    fig = px.bar(league_stats, x="name", y="Avg Goals", color="Top Team", title="Top Team by Avg Goals per Match")
    st.plotly_chart(fig)



# -------------------- TAB 3: PLAYER ANALYSIS --------------------
with tab3:
    st.header("🧍 Player Statistics & Comparison")

    player_names = players_df["player_name"].unique()
    player1 = st.selectbox("Select Player 1", player_names)
    player2 = st.selectbox("Select Player 2", player_names)

    p1_attrs = player_attrs_df[player_attrs_df["player_api_id"] == 
                               players_df[players_df["player_name"] == player1]["player_api_id"].values[0]].sort_values("date").tail(1)

    p2_attrs = player_attrs_df[player_attrs_df["player_api_id"] == 
                               players_df[players_df["player_name"] == player2]["player_api_id"].values[0]].sort_values("date").tail(1)

    if not p1_attrs.empty and not p2_attrs.empty:
        skills = ['overall_rating', 'finishing', 'passing', 'dribbling', 'long_passing', 'short_passing', 
                  'volleys', 'shot_power', 'aggression', 'stamina']
        radar_df = pd.DataFrame({
            "Skill": skills,
            player1: [p1_attrs.iloc[0].get(skill, 0) for skill in skills],
            player2: [p2_attrs.iloc[0].get(skill, 0) for skill in skills],
        })

        st.markdown("### 🧠 Player Comparison Radar Chart")
        radar_long = radar_df.melt(id_vars="Skill", var_name="Player", value_name="Value")

        # Plot using line_polar
        fig = px.line_polar(
            radar_long,
            r="Value",
            theta="Skill",
            color="Player",
            line_close=True,
            title=f"{player1} vs {player2} Skill Comparison"
        )
        st.plotly_chart(fig, use_container_width=True)
   