AI Tool for Mobile Game Epic Seven
Overview

This project is a web-based AI drafting assistant for the turn-based mobile strategy game Epic Seven.
It predicts match outcomes and recommends optimal hero picks during the Real-Time Arena (RTA) drafting phase by analyzing high-level competitive play data from the game’s official match history API.

Unlike most game prediction tools that focus solely on in-game variables, this project emphasizes out-of-game drafting decisions—a critical factor in turn-based games like Epic Seven, where the draft has a disproportionately large impact on the match outcome.

Features

Draft Phase Hero Recommendations
Suggests heroes based on the current draft state, including bans and pick order, using historical data from the top-ranked players.

Match Outcome Prediction
Uses a trained machine learning model (Linear Regression) to predict win/loss probability after draft completion.

Interactive Web UI
Built with Flask, allowing players to input draft progress via dropdown menus and receive real-time recommendations and predictions.

Data-Driven Insights
Recommendations are based on a curated dataset of ~5,400 matches scraped from 50 top-ranked players.

Technical Approach
1. Data Collection

Scraped official Epic Seven match history API for player draft data (heroes picked/banned, pick order, pre/post bans).

Collected ~100 matches per player from 50 high-ranked players.

Manually gathered player IDs due to lack of API listing functionality.

2. Data Preprocessing

Removed identifiable player data (names, region).

Extracted draft sequence into a structured CSV dataset.

Mapped hero codes to hero names for use in the UI.

3. Recommendation System

“Pseudo” recommendation system based on frequency of hero picks in the dataset.

Considers both pre-bans and already drafted heroes to filter suggestions.

Adjusts recommendations dynamically after each draft step.

4. Machine Learning Model

Model: Linear Regression

Input: Encoded categorical data representing the full draft state.

Output: Win or loss prediction.

Accuracy: ~60% on curated dataset.

Installation
Requirements

Python 3.9+

Virtual environment (recommended)

requirements.txt provided

Setup
# Clone the repository
git clone https://github.com/Dtham14/AI-Tool-for-Mobile-Game-Epic-Seven.git
cd AI-Tool-for-Mobile-Game-Epic-Seven

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

Usage

Run the Flask server:

python app.py


Open the web UI:
Visit http://127.0.0.1:5000 in your browser.

Simulate a draft:

Select pre-bans for both sides.

Input heroes as they are picked.

View recommended next picks.

Get outcome prediction:

After all heroes are picked and post-bans selected, click Get Win Prediction.
