IGWE: Football Predictor


IGWE is a Python-based application that uses a machine learning model to predict the outcomes of English Premier League football matches. It fetches real-world match and team'
statistics, trains a predictive model, and presents the results through a simple web interface.

This project is built with a hybrid data model, giving you the best of both worlds:

Match-by-Match Data: Used to train a powerful Poisson regression model that learns the specific attack and defense strengths of each team, leading to accurate score and win/draw/loss predictions.

Aggregate Season Stats: Used to provide valuable context on the web interface, showing per-game averages for stats like shots and cards.

Features
Data Collection: Automatically fetches match results and detailed team statistics for multiple seasons from the https://fbrapi.com/ API.

Intelligent Model: Trains a Poisson regression model that learns team-specific strengths and weaknesses, as well as home-field advantage.

Detailed Predictions: For any given matchup, it predicts:

Expected goals for each team.

Win, draw, and loss percentages.

The top 5 most likely final scores.

Average shots and cards per game for context.

Simple Web Interface: A clean, user-friendly front-end built with Flask to select teams and view predictions.

Dockerized: The entire application is containerized with Docker for easy setup and consistent performance across any machine.

Getting Started
Follow these steps to get the IGWE application running on your local machine.

Prerequisites
Python 3.9 or higher installed on your system.

Docker Desktop installed and running.

Step 1: Get Your API Key
The application requires an API key from https://fbrapi.com to fetch the football data.

on your terminal
curl -X POST https://fbrapi.com/generate_api_key

A key will be generated for you instantly. Copy this key.

Open the app/data_collector.py file in your project and paste your key into the API_KEY variable:

API_KEY = "YOUR_FBRef_API_KEY" # Paste your key here

Step 2: Build the Database and Train the Model
Before you can run the web app, you need to populate the database and train the predictive model. Run these scripts from the root directory of your igwe-project folder.

Delete any old database file: If you have an igwe_database.db file in your app folder, delete it to start fresh.

Run the Data Collector: This script will fetch all the match and team stats and create your SQLite database.

python3 app/data_collector.py

(This will take a few minutes as it has to make many API calls and respects the rate limit.)

Run the Model Trainer: This script will use the data you just collected to train the prediction model and save it to a file.

python3 app/model_trainer.py

Step 3: Build and Run the Docker Container
With your data and model ready, you can now launch the application.

Build the Docker Image: This command packages your entire application into a self-contained image named igwe-app.

docker build -t igwe-app .

(Don't forget the . at the end!)

Run the Docker Container: This command starts your application and makes it accessible on your machine.

docker run -p 5001:5001 igwe-app

Step 4: View Your App
Open your web browser and navigate to:

http://localhost:5001

You should now see the IGWE Vibe Predictor interface. You can select two teams, get a prediction, and see the most likely scores! To stop the application, go to your terminal and press Ctrl + C.
