import pandas as pd
import sqlite3
import statsmodels.api as sm
import statsmodels.formula.api as smf
import pickle
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'igwe_database.db')
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'trained_model.pkl')
COLUMNS_PATH = os.path.join(os.path.dirname(__file__), 'model_columns.pkl')

def load_data():
    """Loads match data from the SQLite database."""
    print("Loading match data from SQLite database...")
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM matches", conn)
        df.dropna(subset=['home_goals', 'away_goals'], inplace=True)
        print(f"Data loaded successfully with {len(df)} total matches.")
        return df
    except (sqlite3.Error, pd.io.sql.DatabaseError) as e:
        print(f"Database error: {e}. Please run data_collector.py first.")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def train_model(df):
    """Trains a Poisson model that learns team-specific attack and defense strengths."""
    if df.empty:
        print("DataFrame is empty. Cannot train model.")
        return None

    print("Training Poisson model on historical scores...")
    
    goal_model_data = pd.concat([
        df[['home_team','away_team','home_goals']].assign(home=1).rename(
            columns={'home_team':'team', 'away_team':'opponent','home_goals':'goals'}),
        df[['away_team','home_team','away_goals']].assign(home=0).rename(
            columns={'away_team':'team', 'home_team':'opponent','away_goals':'goals'})
    ])

    try:
        # REVERTED: Simpler formula using only team names and home advantage
        poisson_model = smf.glm(
            formula="goals ~ home + team + opponent",
            data=goal_model_data,
            family=sm.families.Poisson()
        ).fit()

        print("Model training complete.")
        print(poisson_model.summary())
        
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(poisson_model, f)
        print(f"Model saved to {MODEL_PATH}")

        model_columns = goal_model_data.drop('goals', axis=1).columns.tolist()
        with open(COLUMNS_PATH, 'wb') as f:
            pickle.dump(model_columns, f)
        print(f"Model columns saved to {COLUMNS_PATH}")

        return poisson_model
        
    except Exception as e:
        print(f"An error occurred during model training: {e}")
        return None


def main():
    """Main function to run the model training process."""
    print("--- Starting IGWE Model Trainer ---")
    match_df = load_data()
    train_model(match_df)
    print("--- Model training process finished. ---")

if __name__ == "__main__":
    main()


