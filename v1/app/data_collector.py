# This script fetches data from the FBRef API and populates our SQLite database.
# Run this script first to get the necessary data.
import requests
import pandas as pd
import sqlite3
import time
import os

# --- Configuration ---
API_KEY = "Add your FBR API Here"  # IMPORTANT: Replace with your actual API key from fbrapi.com
LEAGUE_ID = "9"  # Premier League
# UPDATED: List of seasons to fetch data for
SEASONS = ["2022-2023", "2023-2024", "2024-2025", "2025-2026"] # Add and remove seasons as needed
DB_PATH = os.path.join(os.path.dirname(__file__), 'igwe_database.db')

def get_team_id_map(season):
    """Gets a mapping of team_id to team_name for a given season."""
    print(f"Fetching team ID map for {season}...")
    url = "https://fbrapi.com/matches"
    params = {"league_id": LEAGUE_ID, "season_id": season}
    headers = {"X-API-Key": API_KEY}
    team_map = {}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'data' in data and data['data']:
            for match in data['data']:
                if match.get('home_team_id') and match.get('home'):
                    team_map[match['home_team_id']] = match['home']
                if match.get('away_team_id') and match.get('away'):
                    team_map[match['away_team_id']] = match['away']
            print(f"Created map with {len(team_map)} teams for {season}.")
            return team_map
    except requests.exceptions.RequestException as e:
        print(f"Error fetching team map for {season}: {e}")
    return {}

def get_team_match_data(team_id, team_name, season):
    """Fetches match-by-match stats for a single team in a season."""
    print(f"Fetching match data for {team_name} ({team_id}, {season})...")
    url = "https://fbrapi.com/matches"
    params = {"team_id": team_id, "season_id": season}
    headers = {"X-API-Key": API_KEY}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'data' in data and data['data']:
            df = pd.DataFrame(data['data'])
            # Filter for Premier League matches only
            df = df[df['league_id'].astype(str) == str(LEAGUE_ID)]
            df['primary_team_name'] = team_name
            df['season'] = season
            return df
    except requests.exceptions.RequestException as e:
        print(f"Error fetching match data for {team_name}: {e}")
    return pd.DataFrame()

def get_season_stats(season):
    """Fetches aggregate season stats for all teams."""
    print(f"Fetching aggregate season stats for {season}...")
    url = "https://fbrapi.com/team-season-stats"
    params = {"league_id": LEAGUE_ID, "season_id": season, "stat_type": "standard"}
    headers = {"X-API-Key": API_KEY}
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'data' in data and data['data']:
            flattened_data = []
            for team_data in data['data']:
                flat_record = {
                    'teamName': team_data.get('meta_data', {}).get('team_name'),
                    **team_data.get('stats', {}).get('stats', {}),
                    **team_data.get('stats', {}).get('shooting', {}),
                    **team_data.get('stats', {}).get('keepers', {})
                }
                flattened_data.append(flat_record)
            df = pd.DataFrame(flattened_data)
            df['season'] = season
            return df
    except requests.exceptions.RequestException as e:
        print(f"Error fetching season stats for {season}: {e}")
    return pd.DataFrame()

def create_database(matches_df, stats_df):
    """Creates or replaces tables for matches and season stats."""
    print(f"Connecting to database at: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        
        if not matches_df.empty:
            matches_df.to_sql('matches', conn, if_exists='append', index=False)
            print("'matches' table created successfully.")

        if not stats_df.empty:
            stats_df.rename(columns={
                'teamName': 'team_name', 'ttl_sh': 'shots', 
                'ttl_yellow_cards': 'yellow_cards', 'ttl_red_cards': 'red_cards', 
                'ttl_xg': 'xg', 'sot_ag': 'shots_on_target_against', 
                'save_pct': 'save_percentage', 'clean_sheets': 'clean_sheets'
            }, inplace=True)
            stats_cols = ['season', 'team_name', 'shots', 'yellow_cards', 'red_cards', 'xg', 
                          'shots_on_target_against', 'save_percentage', 'clean_sheets']
            existing_stats_cols = [col for col in stats_cols if col in stats_df.columns]
            stats_df[existing_stats_cols].to_sql('season_stats', conn, if_exists='append', index=False)
            print("'season_stats' table created successfully.")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

def main():
    """Main function to run the new data collection process."""
    print("--- Starting IGWE Advanced Data Collector ---")
    all_matches_raw = pd.DataFrame()
    all_stats = pd.DataFrame()

    for season in SEASONS:
        team_map = get_team_id_map(season)
        time.sleep(10)
        
        for team_id, team_name in team_map.items():
            team_matches = get_team_match_data(team_id, team_name, season)
            all_matches_raw = pd.concat([all_matches_raw, team_matches], ignore_index=True)
            time.sleep(10)
            
        season_stats = get_season_stats(season)
        all_stats = pd.concat([all_stats, season_stats], ignore_index=True)
        time.sleep(10)

    # --- Reconstruct full match data ---
    reconstructed_matches = []
    processed_match_ids = set()

    for _, row in all_matches_raw.iterrows():
        if row['match_id'] in processed_match_ids:
            continue
        
        if pd.isna(row['gf']) or pd.isna(row['ga']):
            continue

        if row['home_away'] == 'Home':
            home_team, away_team = row['primary_team_name'], row['opponent']
            home_goals, away_goals = int(row['gf']), int(row['ga'])
        else: # Away game
            home_team, away_team = row['opponent'], row['primary_team_name']
            home_goals, away_goals = int(row['ga']), int(row['gf'])
            
        reconstructed_matches.append({
            'season': row['season'],
            'date': row['date'],
            'home_team': home_team,
            'away_team': away_team,
            'home_goals': home_goals,
            'away_goals': away_goals
        })
        processed_match_ids.add(row['match_id'])
        
    final_matches_df = pd.DataFrame(reconstructed_matches)

    create_database(final_matches_df, all_stats)
    print("--- Data collection process finished. ---")

if __name__ == "__main__":
    main()
