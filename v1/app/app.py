from flask import Flask, render_template, request
import pandas as pd
import sqlite3
import pickle
import os
import numpy as np
from scipy.stats import poisson

app = Flask(__name__)

# --- Paths ---
DB_PATH = os.path.join(os.path.dirname(__file__), 'igwe_database.db')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'trained_model.pkl')
COLUMNS_PATH = os.path.join(os.path.dirname(__file__), 'model_columns.pkl')


# --- Load Model and Data ---
def load_model():
    """Loads the pre-trained model and columns."""
    try:
        with open(MODEL_PATH, 'rb') as f: model = pickle.load(f)
        with open(COLUMNS_PATH, 'rb') as f: model_cols = pickle.load(f)
        return model, model_cols
    except FileNotFoundError:
        return None, None

def get_teams():
    """Gets a list of all unique team names from the matches table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        teams_df = pd.read_sql_query("SELECT DISTINCT team_name FROM season_stats ORDER BY team_name", conn)
        return teams_df['team_name'].tolist()
    except Exception:
        return []
    finally:
        if conn: conn.close()

def get_latest_season_stats(team_name):
    """Gets the most recent season's aggregate stats for a single team."""
    try:
        conn = sqlite3.connect(DB_PATH)
        query = f"SELECT * FROM season_stats WHERE team_name = '{team_name}' AND shots IS NOT NULL AND shots > 0 ORDER BY season DESC LIMIT 1"
        df = pd.read_sql_query(query, conn)
        return df.iloc[0] if not df.empty else None
    except Exception as e:
        print(f"Error getting season stats: {e}")
        return None
    finally:
        if conn: conn.close()

model, model_columns = load_model()
TEAMS = get_teams()

@app.route('/', methods=['GET'])
def index():
    if not TEAMS:
        return "Database not found or is empty. Run data_collector.py and model_trainer.py first.", 500
    return render_template('index.html', teams=TEAMS)

@app.route('/predict', methods=['POST'])
def predict():
    home_team_name = request.form['home_team']
    away_team_name = request.form['away_team']

    if not model:
        return "Model not loaded. Please run model_trainer.py first.", 500
    
    if home_team_name == away_team_name:
        return render_template('index.html', teams=TEAMS, error="Home and Away teams cannot be the same.")

    home_stats = get_latest_season_stats(home_team_name)
    away_stats = get_latest_season_stats(away_team_name)

    if home_stats is None or away_stats is None:
         return render_template('result.html', home_team=home_team_name, away_team=away_team_name,
                               error="No available data for one or both teams. Please wait for them to play a match in the new season.")

    # --- Predict Goals using the simpler model ---
    home_pred_df = pd.DataFrame(data={'team': [home_team_name], 'opponent': [away_team_name], 'home': [1]})
    home_goals_avg = model.predict(home_pred_df).iloc[0]

    away_pred_df = pd.DataFrame(data={'team': [away_team_name], 'opponent': [home_team_name], 'home': [0]})
    away_goals_avg = model.predict(away_pred_df).iloc[0]

    # --- Simulate Match for Win/Draw/Loss Percentages ---
    simulations = 10000
    home_wins, away_wins, draws = 0, 0, 0
    for _ in range(simulations):
        home_score, away_score = np.random.poisson(home_goals_avg), np.random.poisson(away_goals_avg)
        if home_score > away_score: home_wins += 1
        elif away_score > home_score: away_wins += 1
        else: draws += 1
    
    # --- Calculate Most Likely Score ---
    max_goals = 7
    score_probabilities = []
    for i in range(max_goals):
        for j in range(max_goals):
            prob = poisson.pmf(i, home_goals_avg) * poisson.pmf(j, away_goals_avg)
            score_probabilities.append({'score': f"{i} - {j}", 'prob': prob})

    most_likely_score = sorted(score_probabilities, key=lambda x: x['prob'], reverse=True)[0]
    most_likely_score['prob_pct'] = f"{round(most_likely_score['prob'] * 100, 1)}%"

    
    predictions = {
        'home_goals': round(home_goals_avg, 2),
        'away_goals': round(away_goals_avg, 2),
        'home_win_pct': round((home_wins / simulations) * 100, 1),
        'away_win_pct': round((away_wins / simulations) * 100, 1),
        'draw_pct': round((draws / simulations) * 100, 1),
        'home_shots': round(home_stats['shots'] / 38, 2),
        'away_shots': round(away_stats['shots'] / 38, 2),
        'home_cards': round((home_stats['yellow_cards'] + home_stats['red_cards']) / 38, 2),
        'away_cards': round((away_stats['yellow_cards'] + away_stats['red_cards']) / 38, 2),
        'most_likely_score': most_likely_score
    }

    return render_template('result.html', home_team=home_team_name, away_team=away_team_name, predictions=predictions)

if __name__ == '__main__':
    if not os.path.exists(DB_PATH) or not os.path.exists(MODEL_PATH):
        print("="*50)
        print("ERROR: Database or Model not found!")
        print("Please run the following scripts in order:")
        print("1. python app/data_collector.py")
        print("2. python app/model_trainer.py")
        print("="*50)
    else:
        app.run(host='0.0.0.0', port=5001, debug=True)
