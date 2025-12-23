import pandas as pd
from collections import defaultdict

# Cache for dataset and counter matrix
_dataset_cache = None
_counter_matrix_cache = None

def get_dataset():
    global _dataset_cache
    if _dataset_cache is None:
        file_path = "e7_data/drafts_dataset.csv"
        _dataset_cache = pd.read_csv(file_path)
    return _dataset_cache

def build_counter_matrix():
    """
    Build a matrix of win rates: counter_matrix[my_hero][enemy_hero] = win_rate
    This tells us how well each hero performs AGAINST each enemy hero.
    """
    global _counter_matrix_cache
    if _counter_matrix_cache is not None:
        return _counter_matrix_cache

    dataset = get_dataset()

    # Track wins and total games for each (my_hero, enemy_hero) pair
    # We consider a "win" when is_win == 0 (main player wins)
    matchup_wins = defaultdict(lambda: defaultdict(int))
    matchup_total = defaultdict(lambda: defaultdict(int))

    main_cols = ['main1', 'main2', 'main3', 'main4', 'main5']
    enemy_cols = ['enemy1', 'enemy2', 'enemy3', 'enemy4', 'enemy5']

    for index, row in dataset.iterrows():
        is_win = row['is_win'] == 0  # 0 means main player won

        # Get all heroes on each side
        my_heroes = [row[col] for col in main_cols if pd.notna(row[col]) and row[col] != '']
        enemy_heroes = [row[col] for col in enemy_cols if pd.notna(row[col]) and row[col] != '']

        # For each of my heroes, track their performance against each enemy hero
        for my_hero in my_heroes:
            for enemy_hero in enemy_heroes:
                matchup_total[my_hero][enemy_hero] += 1
                if is_win:
                    matchup_wins[my_hero][enemy_hero] += 1

    # Calculate win rates
    counter_matrix = {}
    for my_hero in matchup_total:
        counter_matrix[my_hero] = {}
        for enemy_hero in matchup_total[my_hero]:
            total = matchup_total[my_hero][enemy_hero]
            wins = matchup_wins[my_hero][enemy_hero]
            if total >= 5:  # Only count if we have enough data
                counter_matrix[my_hero][enemy_hero] = wins / total
            else:
                counter_matrix[my_hero][enemy_hero] = 0.5  # Default to 50% if not enough data

    _counter_matrix_cache = counter_matrix
    print(f"Built counter matrix with {len(counter_matrix)} heroes")
    return counter_matrix

def get_best_counters(enemy_heroes, cannot_draft, num_picks=2):
    """
    Find heroes with the highest win rates against the given enemy heroes.

    Args:
        enemy_heroes: List of enemy hero names currently picked
        cannot_draft: List of heroes that cannot be picked
        num_picks: Number of suggestions to return

    Returns:
        List of hero names with best counter scores
    """
    counter_matrix = build_counter_matrix()
    print(f"get_best_counters called: enemy_heroes={enemy_heroes}, num_picks={num_picks}")
    print(f"Counter matrix has {len(counter_matrix)} heroes")

    # Filter out empty strings and None
    enemy_heroes = [h for h in enemy_heroes if h and pd.notna(h)]
    print(f"Filtered enemy_heroes: {enemy_heroes}")

    if not enemy_heroes:
        print("No enemy heroes after filtering, returning empty")
        return []

    # Calculate aggregate counter score for each potential pick
    hero_scores = {}

    for my_hero in counter_matrix:
        if my_hero in cannot_draft or not my_hero or pd.isna(my_hero):
            continue

        # Calculate average win rate against all current enemy heroes
        win_rates = []
        for enemy_hero in enemy_heroes:
            if enemy_hero in counter_matrix.get(my_hero, {}):
                win_rates.append(counter_matrix[my_hero][enemy_hero])

        if win_rates:
            # Average win rate against all enemies
            hero_scores[my_hero] = sum(win_rates) / len(win_rates)

    # Sort by score (highest win rate first)
    sorted_heroes = sorted(hero_scores.items(), key=lambda x: x[1], reverse=True)

    # Return top picks
    return [hero for hero, score in sorted_heroes[:num_picks]]

def first_picks():
    dataset = get_dataset()

    first_picked_col_all = []
    for index, row in dataset.iterrows():
        if row['is_first'] == 1:
            val = row['main1']
            first_picked_col_all.append(val)
        else:
            val = row['enemy1']
            first_picked_col_all.append(val)

    dataset_copy = dataset.copy()
    dataset_copy['first_picked'] = first_picked_col_all

    recommended_fp = []
    for i in range(40):
        recommended_fp.append(dataset_copy['first_picked'].value_counts().index[i])

    return recommended_fp


def draft_response(e1, m1, e2, m2, e3, m3,
                   e4, m4, e5, m5, mpb1, mpb2, epb1, epb2):

    recommended_fp = first_picks()
    dataset = get_dataset()

    # list to keep track of heroes to not recommend to draft
    cannot_draft = []
    response = []

    copy_recommended_fp = list(recommended_fp)

    cannot_draft.append(mpb1)
    cannot_draft.append(mpb2)
    cannot_draft.append(epb1)
    cannot_draft.append(epb2)

    # Helper function to get suggestions from response data
    def get_suggestions_from_response(response, cannot_draft, num_picks=2):
        if len(response) == 0:
            return None
        responses_df = pd.DataFrame(response)
        choices = responses_df.value_counts()[:20]
        array = [pair for pair in choices.index]
        flattened_list = [item for sublist in array for item in sublist]
        data_singles = list(set(flattened_list))
        data_singles = [pick for pick in data_singles if pick not in cannot_draft]
        return data_singles[:num_picks] if data_singles else None

    # Debug: print what we received
    print(f"Draft input: e1={e1}, m1={m1}, e2={e2}, m2={m2}, e3={e3}, m3={m3}, e4={e4}, m4={m4}, e5={e5}, m5={m5}")

    # Determine who has first pick based on what's filled in
    # If m1 is filled but e1 is empty, or m1 is filled first -> main has first pick
    # If e1 is filled but m1 is empty -> enemy has first pick
    main_has_first_pick = (m1 != "" and e1 == "") or (m1 != "" and e1 != "")
    enemy_has_first_pick = (e1 != "" and m1 == "")

    # No picks yet - suggest first pick
    if m1 == "" and e1 == "":
        for pick in copy_recommended_fp:
            if pick in cannot_draft:
                copy_recommended_fp.remove(pick)
        return [copy_recommended_fp[0]]

    # Main picked first (m1 filled), waiting for enemy response (e1, e2 empty)
    if m1 != "" and e1 == "" and e2 == "":
        cannot_draft.append(m1)
        # Return popular meta picks as defensive options
        print(f"Main picked {m1} first, suggesting popular defensive follow-up picks")
        result = [pick for pick in copy_recommended_fp if pick not in cannot_draft][:2]
        return result if result else []

    # ========== ENEMY HAS FIRST PICK ==========
    # Draft order: e1 -> m1,m2 -> e2,e3 -> m3,m4 -> e4,e5 -> m5

    # m1, m2 needed (enemy picked e1 first)
    if enemy_has_first_pick and m1 == "" and m2 == "":
        cannot_draft.append(e1)
        enemy_heroes = [e1]

        for index, row in dataset.iterrows():
            if row['is_first'] == 0 and row['enemy1'] == e1:
                response.append([row['main1'], row['main2']])

        result = get_suggestions_from_response(response, cannot_draft)
        if result:
            return result

        # Fallback: use counter-pick system
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        if counters:
            print(f"Using counter-picks for m1/m2 against {enemy_heroes}: {counters}")
            return counters

        return []

    # m3, m4 needed (after e1 -> m1,m2 -> e2,e3)
    if m1 != "" and m2 != "" and m3 == "" and m4 == "" and e2 != "" and e3 != "":
        cannot_draft.extend([e1, e2, e3, m1, m2])
        enemy_heroes = [e1, e2, e3]

        for index, row in dataset.iterrows():
            if row['is_first'] == 0 and row['enemy2'] == e2 and row['enemy3'] == e3:
                response.append([row['main3'], row['main4']])

        result = get_suggestions_from_response(response, cannot_draft)
        if result:
            return result

        # Try partial match
        response = []
        for index, row in dataset.iterrows():
            if row['is_first'] == 0 and (row['enemy2'] == e2 or row['enemy3'] == e3):
                response.append([row['main3'], row['main4']])

        result = get_suggestions_from_response(response, cannot_draft)
        if result:
            return result

        # Fallback: use counter-pick system
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        if counters:
            print(f"Using counter-picks for m3/m4 against {enemy_heroes}: {counters}")
            return counters

        return []

    # m5 needed (last pick) - more flexible condition
    # Works when m1-m4 are filled and m5 is empty, regardless of enemy picks
    if m1 != "" and m2 != "" and m3 != "" and m4 != "" and m5 == "":
        print(f"Matched m5 condition: m1-m4 filled, m5 empty")
        all_picked = [e1, e2, e3, e4, e5, m1, m2, m3, m4]
        cannot_draft.extend([h for h in all_picked if h])
        enemy_heroes = [h for h in [e1, e2, e3, e4, e5] if h]

        if not enemy_heroes:
            print("No enemy heroes to counter, using general fallback")
            counters = get_best_counters(['Boss Arunka'], cannot_draft, num_picks=3)  # Use popular hero as baseline
            return counters if counters else []

        # Try exact match first (e4 AND e5) if both are filled
        if e4 != "" and e5 != "":
            for index, row in dataset.iterrows():
                if row['is_first'] == 0 and row['enemy4'] == e4 and row['enemy5'] == e5:
                    response.append([row['main5']])

            result = get_suggestions_from_response(response, cannot_draft, num_picks=3)
            if result:
                return result

            # Try partial match (e4 OR e5)
            response = []
            for index, row in dataset.iterrows():
                if row['is_first'] == 0 and (row['enemy4'] == e4 or row['enemy5'] == e5):
                    response.append([row['main5']])

            result = get_suggestions_from_response(response, cannot_draft, num_picks=3)
            if result:
                return result

        # Fallback: use counter-pick system against all known enemies
        print(f"Calling get_best_counters with enemies={enemy_heroes}, cannot_draft has {len(cannot_draft)} items")
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=3)
        print(f"Counter result: {counters}")
        if counters:
            print(f"Using counter-picks for m5 against {enemy_heroes}: {counters}")
            return counters

        print("No counters found, returning empty list")
        return []

    # ========== MAIN HAS FIRST PICK ==========
    # Draft order: m1 -> e1,e2 -> m2,m3 -> e3,e4 -> m4,m5 -> e5

    # m2, m3 needed (after m1 -> e1,e2)
    if m1 != "" and m2 == "" and m3 == "" and e1 != "" and e2 != "":
        cannot_draft.extend([m1, e1, e2])
        enemy_heroes = [e1, e2]

        # Try exact match first
        for index, row in dataset.iterrows():
            if row['is_first'] == 1 and row['enemy1'] == e1 and row['enemy2'] == e2:
                response.append([row['main2'], row['main3']])

        result = get_suggestions_from_response(response, cannot_draft)
        if result:
            return result

        # Try with is_first = 0 as well (similar patterns)
        for index, row in dataset.iterrows():
            if row['enemy1'] == e1 and row['enemy2'] == e2:
                response.append([row['main2'], row['main3']])

        result = get_suggestions_from_response(response, cannot_draft)
        if result:
            return result

        # Fallback: use counter-pick system
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        if counters:
            print(f"Using counter-picks for m2/m3 against {enemy_heroes}: {counters}")
            return counters

        return []

    # m4, m5 needed (after m1 -> e1,e2 -> m2,m3 -> e3,e4)
    if m1 != "" and m2 != "" and m3 != "" and m4 == "" and m5 == "" and e3 != "" and e4 != "":
        cannot_draft.extend([m1, e1, e2, m2, m3, e3, e4])
        enemy_heroes = [e1, e2, e3, e4]

        # Try exact match first (e3 AND e4)
        for index, row in dataset.iterrows():
            if row['is_first'] == 1 and row['enemy3'] == e3 and row['enemy4'] == e4:
                response.append([row['main4'], row['main5']])

        result = get_suggestions_from_response(response, cannot_draft)
        if result:
            return result

        # Try partial match (e3 OR e4)
        response = []
        for index, row in dataset.iterrows():
            if row['enemy3'] == e3 or row['enemy4'] == e4:
                response.append([row['main4'], row['main5']])

        result = get_suggestions_from_response(response, cannot_draft)
        if result:
            return result

        # Fallback: use counter-pick system
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        if counters:
            print(f"Using counter-picks for m4/m5 against {enemy_heroes}: {counters}")
            return counters

        return []

    # Fallback for any remaining case - use counter-picks against all known enemies
    all_enemies = [h for h in [e1, e2, e3, e4, e5] if h]
    all_mine = [h for h in [m1, m2, m3, m4, m5] if h]
    cannot_draft.extend(all_enemies + all_mine)

    if all_enemies:
        counters = get_best_counters(all_enemies, cannot_draft, num_picks=2)
        if counters:
            print(f"Using fallback counter-picks against {all_enemies}: {counters}")
            return counters

    return []
