from flask import Flask, render_template, send_file, request, jsonify
import json
import pandas as pd
from model import getModel
from draft_logic import draft_response

app = Flask(__name__)

# Load hero code mappings
with open('e7_data/herocodes.json', 'r') as f:
    herocodes_data = json.load(f)
    code_to_name = {h['code']: h['name'] for h in herocodes_data}
    name_to_code = {h['name']: h['code'] for h in herocodes_data}

print(f"Loaded {len(name_to_code)} hero mappings. Boss Arunka -> {name_to_code.get('Boss Arunka', 'NOT FOUND')}", flush=True)

# PRE-LOAD STATISTICS AT STARTUP
print("Pre-loading draft statistics...", flush=True)
from draft_logic import get_hero_matchups, get_hero_synergies, get_draft_patterns

matchups = get_hero_matchups()  # Triggers pickle load + cache
synergies = get_hero_synergies()  # Triggers pickle load + cache
patterns = get_draft_patterns()  # Triggers pickle load + cache

if matchups and synergies and patterns:
    print(f"Loaded matchup data for {len(matchups)} heroes", flush=True)
    print(f"Loaded synergy data for {len(synergies)} heroes", flush=True)
    print(f"Loaded draft patterns: {len(patterns)} pattern types", flush=True)
else:
    print("WARNING: Statistics files not found! Run build_statistics.py first.", flush=True)
    print("Application will run but recommendations will be limited.", flush=True)

@app.route('/test')
def test_route():
    test_names = ['Boss Arunka', 'Frieren']
    test_codes = [name_to_code.get(name, name) for name in test_names]
    return jsonify({'names': test_names, 'codes': test_codes})

@app.route('/')
def homepage():
    with open('e7_data/herocodes.json', 'r') as file:
        data = json.load(file)
    return render_template('homepage.html', hero_list =data)

@app.route('/image')
def get_vs():
    filename = 'VS.png'  # Name of the image file
    return send_file('images/' + filename)
 
@app.route('/updateDraftPick', methods=['POST'])
def updateDraftPick():
    data = request.json  # Read JSON data sent from client

    # Convert codes to names for the draft logic
    draft_list = []
    for key in ['enPick1', 'myPick1', 'enPick2', 'myPick2', 'enPick3', 'myPick3',
                'enPick4', 'myPick4', 'enPick5', 'myPick5', 'myPre1', 'myPre2', 'enPre1', 'enPre2']:
        code = data.get(key, '')
        name = code_to_name.get(code, '') if code else ''
        draft_list.append(name)

    print(f"Draft list (names): {draft_list}")

    res = draft_response(draft_list[0], draft_list[1], draft_list[2], draft_list[3], draft_list[4],
                   draft_list[5], draft_list[6], draft_list[7], draft_list[8], draft_list[9],
                   draft_list[10], draft_list[11], draft_list[12], draft_list[13])

    # Convert response names back to codes for the frontend
    if isinstance(res, list):
        res_codes = [name_to_code.get(name, name) for name in res]
        print(f"Response names: {res}", flush=True)
        print(f"Response codes: {res_codes}", flush=True)
        return jsonify(res_codes)
    else:
        print(f"Response: {res}", flush=True)
        return jsonify(res)

@app.route('/calculateWin', methods=['POST'])
def calculateWin():
    data = request.json  # Read JSON data sent from client

    # Convert codes to names for the model
    draft_list = []
    for key in ['enPick1', 'myPick1', 'enPick2', 'myPick2', 'enPick3', 'myPick3',
                'enPick4', 'myPick4', 'enPick5', 'myPick5', 'myPre1', 'enPre1',
                'myPre2', 'enPre2', 'myPost', 'enPost']:
        code = data.get(key, '')
        name = code_to_name.get(code, '') if code else ''
        draft_list.append(name)

    print(f"Win calc draft list: {draft_list}")
    pred = getModel(draft_list)
    print(pred[0])
    return {'res':int(pred[0])}

if __name__ == '__main__':
    app.run(port=5003)