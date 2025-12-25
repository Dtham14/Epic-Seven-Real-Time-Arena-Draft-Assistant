import pandas as pd
from collections import defaultdict
import pickle
from pathlib import Path
import os
from functools import lru_cache

# Cache for dataset and counter matrix
_dataset_cache = None
_counter_matrix_cache = None

# Cache for pre-computed statistics
_hero_winrates = None
_hero_pickrates = None
_hero_matchups = None
_hero_synergies = None
_draft_patterns = None

# Use absolute path relative to this file's location
DATA_DIR = Path(__file__).parent / "e7_data"

def get_dataset():
    global _dataset_cache
    if _dataset_cache is None:
        file_path = DATA_DIR / "drafts_dataset.csv"
        _dataset_cache = pd.read_csv(file_path)
    return _dataset_cache

def load_pickle_stats(filename):
    """Load pre-computed statistics from pickle file"""
    pkl_path = DATA_DIR / f"{filename}.pkl"
    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)
            print(f"Successfully loaded {filename}.pkl ({len(data)} entries)", flush=True)
            return data
    except FileNotFoundError:
        print(f"ERROR: {pkl_path} not found. Run build_statistics.py first.", flush=True)
        print(f"  Current working directory: {os.getcwd()}", flush=True)
        print(f"  Expected path: {pkl_path.absolute()}", flush=True)
        return None
    except Exception as e:
        print(f"ERROR loading {filename}.pkl: {e}", flush=True)
        return None

def get_hero_winrates():
    """Load overall hero winrates (cached)"""
    global _hero_winrates
    if _hero_winrates is None:
        _hero_winrates = load_pickle_stats("hero_winrates") or {}
    return _hero_winrates

def get_hero_pickrates():
    """Load hero pickrates (cached)"""
    global _hero_pickrates
    if _hero_pickrates is None:
        _hero_pickrates = load_pickle_stats("hero_pickrates") or {}
    return _hero_pickrates

def get_hero_matchups():
    """Load hero matchup matrix (cached)"""
    global _hero_matchups
    if _hero_matchups is None:
        _hero_matchups = load_pickle_stats("hero_matchups") or {}
    return _hero_matchups

def get_hero_synergies():
    """Load hero synergy matrix (cached)"""
    global _hero_synergies
    if _hero_synergies is None:
        _hero_synergies = load_pickle_stats("hero_synergies") or {}
    return _hero_synergies

def get_draft_patterns():
    """Load pre-computed draft patterns (cached)"""
    global _draft_patterns
    if _draft_patterns is None:
        _draft_patterns = load_pickle_stats("draft_patterns") or {}
    return _draft_patterns

def get_pattern_recommendations(pattern_key, lookup_key, cannot_draft, num_picks=2):
    """
    Get recommendations from pre-computed patterns.

    Args:
        pattern_key: Pattern type (e.g., 'enemy_m1m2', 'main_m4m5')
        lookup_key: Lookup value (e.g., 'Belian' or ('Rinak', 'Empyrean Ilynav'))
        cannot_draft: List of heroes that cannot be picked
        num_picks: Number of suggestions to return

    Returns:
        List of recommended hero names, or empty list if no pattern found
    """
    patterns = get_draft_patterns()

    if not patterns or pattern_key not in patterns:
        return []

    pattern_dict = patterns[pattern_key]

    # Convert tuple lookup_key to string format "hero1|hero2" for JSON compatibility
    if isinstance(lookup_key, tuple):
        lookup_key = "|".join(lookup_key)

    # Get the pattern list for this lookup key
    if lookup_key not in pattern_dict:
        return []

    pattern_list = pattern_dict[lookup_key]

    # Filter out banned heroes and flatten tuples
    recommendations = []
    for item in pattern_list:
        # item might be a tuple (e.g., ('Lua', 'Aramintha')) or a single hero
        if isinstance(item, tuple):
            # It's a combination like ('Lua', 'Aramintha')
            heroes = [h for h in item if h and pd.notna(h) and h not in cannot_draft]
            if len(heroes) >= num_picks:
                recommendations.extend(heroes[:num_picks])
                if len(recommendations) >= num_picks:
                    break
        else:
            # It's a single hero
            if item and pd.notna(item) and item not in cannot_draft:
                recommendations.append(item)
                if len(recommendations) >= num_picks:
                    break

    return recommendations[:num_picks]

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
    matchups = get_hero_matchups()

    if not matchups:
        print("Warning: No matchup data available")
        return []

    print(f"get_best_counters called: enemy_heroes={enemy_heroes}, num_picks={num_picks}")
    print(f"Matchup matrix has {len(matchups)} heroes")

    # Filter out empty strings and None
    enemy_heroes = [h for h in enemy_heroes if h and pd.notna(h)]
    print(f"Filtered enemy_heroes: {enemy_heroes}")

    if not enemy_heroes:
        print("No enemy heroes after filtering, returning empty")
        return []

    # Calculate aggregate counter score for each potential pick
    hero_scores = {}

    for my_hero in matchups:
        if my_hero in cannot_draft or not my_hero or pd.isna(my_hero):
            continue

        # Calculate average win rate against all current enemy heroes
        win_rates = []
        for enemy_hero in enemy_heroes:
            if enemy_hero in matchups.get(my_hero, {}):
                win_rates.append(matchups[my_hero][enemy_hero])

        if win_rates:
            # Average win rate against all enemies
            hero_scores[my_hero] = sum(win_rates) / len(win_rates)

    # Sort by score (highest win rate first)
    sorted_heroes = sorted(hero_scores.items(), key=lambda x: x[1], reverse=True)

    # Return top picks
    return [hero for hero, score in sorted_heroes[:num_picks]]

def get_best_synergies(my_heroes, cannot_draft, num_picks=2):
    """
    Find heroes that synergize best with current team composition.

    Args:
        my_heroes: List of already-picked heroes on my team
        cannot_draft: List of heroes that cannot be picked
        num_picks: Number of suggestions to return

    Returns:
        List of hero names with best synergy scores
    """
    synergies = get_hero_synergies()

    if not synergies:
        print("Warning: No synergy data available")
        return []

    # Filter out empty heroes
    my_heroes = [h for h in my_heroes if h and pd.notna(h)]

    if not my_heroes:
        return []

    print(f"get_best_synergies called: my_heroes={my_heroes}, num_picks={num_picks}")

    # Calculate aggregate synergy score
    hero_scores = {}

    for candidate_hero in synergies:
        if candidate_hero in cannot_draft or not candidate_hero or pd.isna(candidate_hero):
            continue

        # Average synergy with existing team
        synergy_rates = []
        for my_hero in my_heroes:
            if my_hero in synergies.get(candidate_hero, {}):
                synergy_rates.append(synergies[candidate_hero][my_hero])

        if synergy_rates:
            hero_scores[candidate_hero] = sum(synergy_rates) / len(synergy_rates)

    # Sort by score (highest synergy first)
    sorted_heroes = sorted(hero_scores.items(), key=lambda x: x[1], reverse=True)

    return [hero for hero, score in sorted_heroes[:num_picks]]

def first_picks():
    """Get most common first picks from dataset (optimized)"""
    dataset = get_dataset()

    # Vectorized approach
    is_main_first = dataset['is_first'] == 1

    # Create series of first picks
    first_picked = pd.Series(index=dataset.index, dtype=str)
    first_picked[is_main_first] = dataset.loc[is_main_first, 'main1']
    first_picked[~is_main_first] = dataset.loc[~is_main_first, 'enemy1']

    # Get top 40 most common
    recommended_fp = first_picked.value_counts().head(40).index.tolist()

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

        # Try pre-computed patterns first (FAST)
        result = get_pattern_recommendations('enemy_m1m2', e1, cannot_draft, num_picks=2)
        if result:
            print(f"Using pre-computed pattern for m1/m2 after {e1}: {result}")
            return result

        # Fallback: use counter-pick system
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        if counters:
            print(f"Using counter-picks for m1/m2 against {enemy_heroes}: {counters}")
            return counters

        return []

    # m2 only needed (m1 filled, enemy responded with e2)
    if enemy_has_first_pick and m1 != "" and m2 == "" and e2 != "":
        cannot_draft.extend([e1, m1, e2])
        enemy_heroes = [e1, e2]
        my_heroes = [m1]

        # Use hybrid counter-pick + synergy
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Combine: prioritize synergies with m1, then counters
        combined = []
        for hero in synergies:
            if hero not in combined:
                combined.append(hero)
        for hero in counters:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        if combined:
            print(f"Using synergy+counter pick for m2 (complement {m1}): {combined[:1]}")
            return combined[:1]

        return []

    # m3, m4 needed (after e1 -> m1,m2 -> e2,e3)
    if m1 != "" and m2 != "" and m3 == "" and m4 == "" and e2 != "" and e3 != "":
        cannot_draft.extend([e1, e2, e3, m1, m2])
        enemy_heroes = [e1, e2, e3]

        # Try pre-computed patterns first (FAST)
        result = get_pattern_recommendations('enemy_m3m4', (e2, e3), cannot_draft, num_picks=2)
        if result:
            print(f"Using pre-computed pattern for m3/m4 after {e2}, {e3}: {result}")
            return result

        # Fallback: use hybrid counter-pick + synergy system
        my_heroes = [m1, m2]

        # Get counter suggestions
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=3)
        # Get synergy suggestions
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=3)

        # Combine: prioritize counters, add synergies as backup
        combined = []
        for hero in counters:
            if hero not in combined:
                combined.append(hero)
        for hero in synergies:
            if hero not in combined and len(combined) < 2:
                combined.append(hero)

        if combined:
            print(f"Using combined counter+synergy picks for m3/m4: {combined[:2]}")
            return combined[:2]

        return []

    # m3 only needed (m1,m2 filled, enemy responded with e3)
    if m1 != "" and m2 != "" and m3 == "" and e2 != "" and e3 != "":
        cannot_draft.extend([e1, e2, e3, m1, m2])
        enemy_heroes = [e1, e2, e3]
        my_heroes = [m1, m2]

        # Use hybrid counter-pick + synergy
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Combine: balance synergies with team and counters to enemies
        combined = []
        for hero in synergies:
            if hero not in combined:
                combined.append(hero)
        for hero in counters:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        if combined:
            print(f"Using synergy+counter pick for m3: {combined[:1]}")
            return combined[:1]

        return []

    # m4 only needed (m1,m2,m3 filled, enemy responded with e4)
    if m1 != "" and m2 != "" and m3 != "" and m4 == "" and e4 != "":
        all_picked = [e1, e2, e3, e4, m1, m2, m3]
        cannot_draft.extend([h for h in all_picked if h])
        enemy_heroes = [h for h in [e1, e2, e3, e4] if h]
        my_heroes = [m1, m2, m3]

        # Use hybrid counter-pick + synergy
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Combine: balance synergies with team and counters to enemies
        combined = []
        for hero in synergies:
            if hero not in combined:
                combined.append(hero)
        for hero in counters:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        if combined:
            print(f"Using synergy+counter pick for m4: {combined[:1]}")
            return combined[:1]

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
            counters = get_best_counters(['Boss Arunka'], cannot_draft, num_picks=1)  # Use popular hero as baseline
            return counters if counters else []

        # Try pre-computed pattern first (FAST) if e4 and e5 are filled
        if e4 != "" and e5 != "":
            result = get_pattern_recommendations('enemy_m5', (e4, e5), cannot_draft, num_picks=1)
            if result:
                print(f"Using pre-computed pattern for m5 after {e4}, {e5}: {result}")
                return result

        # Fallback: use hybrid counter-pick + synergy system
        my_heroes = [m1, m2, m3, m4]

        print(f"Calling get_best_counters with enemies={enemy_heroes}, cannot_draft has {len(cannot_draft)} items")
        # Prioritize counters for last pick, use synergies as tiebreaker
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Merge lists: prioritize counters
        combined = []
        for hero in counters:
            if hero not in combined:
                combined.append(hero)
        for hero in synergies:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        print(f"Counter+synergy result for m5: {combined}")
        if combined:
            print(f"Using combined counter+synergy pick for m5: {combined[0]}")
            return [combined[0]]

        print("No counters or synergies found, returning empty list")
        return []

    # ========== MAIN HAS FIRST PICK ==========
    # Draft order: m1 -> e1,e2 -> m2,m3 -> e3,e4 -> m4,m5 -> e5

    # m2, m3 needed (after m1 -> e1,e2)
    if m1 != "" and m2 == "" and m3 == "" and e1 != "" and e2 != "":
        cannot_draft.extend([m1, e1, e2])
        enemy_heroes = [e1, e2]

        # Try pre-computed pattern first (FAST)
        result = get_pattern_recommendations('main_m2m3', (e1, e2), cannot_draft, num_picks=2)
        if result:
            print(f"Using pre-computed pattern for m2/m3 after {e1}, {e2}: {result}")
            return result

        # Fallback: use hybrid counter-pick + synergy system
        my_heroes = [m1]

        # Get counter suggestions
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=3)
        # Get synergy suggestions
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=3)

        # Combine: prioritize counters, add synergies as backup
        combined = []
        for hero in counters:
            if hero not in combined:
                combined.append(hero)
        for hero in synergies:
            if hero not in combined and len(combined) < 2:
                combined.append(hero)

        if combined:
            print(f"Using combined counter+synergy picks for m2/m3: {combined[:2]}")
            return combined[:2]

        return []

    # m2 only needed (main-first: after m1 -> e1,e2, need m2)
    if m1 != "" and m2 == "" and e1 != "" and e2 != "":
        cannot_draft.extend([m1, e1, e2])
        enemy_heroes = [e1, e2]
        my_heroes = [m1]

        # Use hybrid counter-pick + synergy
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Combine: prioritize synergies with m1, then counters
        combined = []
        for hero in synergies:
            if hero not in combined:
                combined.append(hero)
        for hero in counters:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        if combined:
            print(f"Using synergy+counter pick for m2 (main-first, complement {m1}): {combined[:1]}")
            return combined[:1]

        return []

    # m3 only needed (main-first: after m1 -> e1,e2 -> m2, need m3)
    if m1 != "" and m2 != "" and m3 == "" and e1 != "" and e2 != "":
        cannot_draft.extend([m1, m2, e1, e2])
        enemy_heroes = [e1, e2]
        my_heroes = [m1, m2]

        # Use hybrid counter-pick + synergy
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Combine: balance synergies with team and counters to enemies
        combined = []
        for hero in synergies:
            if hero not in combined:
                combined.append(hero)
        for hero in counters:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        if combined:
            print(f"Using synergy+counter pick for m3 (main-first): {combined[:1]}")
            return combined[:1]

        return []

    # m4, m5 needed (after m1 -> e1,e2 -> m2,m3 -> e3,e4)
    if m1 != "" and m2 != "" and m3 != "" and m4 == "" and m5 == "" and e3 != "" and e4 != "":
        cannot_draft.extend([m1, e1, e2, m2, m3, e3, e4])
        enemy_heroes = [e1, e2, e3, e4]

        # Try pre-computed pattern first (FAST)
        result = get_pattern_recommendations('main_m4m5', (e3, e4), cannot_draft, num_picks=2)
        if result:
            print(f"Using pre-computed pattern for m4/m5 after {e3}, {e4}: {result}")
            return result

        # Fallback: use hybrid counter-pick + synergy system
        my_heroes = [m1, m2, m3]

        # Get counter suggestions
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=3)
        # Get synergy suggestions
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=3)

        # Combine: prioritize counters, add synergies as backup
        combined = []
        for hero in counters:
            if hero not in combined:
                combined.append(hero)
        for hero in synergies:
            if hero not in combined and len(combined) < 2:
                combined.append(hero)

        if combined:
            print(f"Using combined counter+synergy picks for m4/m5: {combined[:2]}")
            return combined[:2]

        return []

    # m4 only needed (main-first: after m1,e1,e2,m2,m3,e3,e4)
    if m1 != "" and m2 != "" and m3 != "" and m4 == "" and e3 != "" and e4 != "":
        cannot_draft.extend([m1, m2, m3, e1, e2, e3, e4])
        enemy_heroes = [e1, e2, e3, e4]
        my_heroes = [m1, m2, m3]

        # Use hybrid counter-pick + synergy
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Combine: balance synergies with team and counters to enemies
        combined = []
        for hero in synergies:
            if hero not in combined:
                combined.append(hero)
        for hero in counters:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        if combined:
            print(f"Using synergy+counter pick for m4 (main-first): {combined[:1]}")
            return combined[:1]

        return []

    # m5 only needed (main-first: after m1,e1,e2,m2,m3,e3,e4,m4)
    if m1 != "" and m2 != "" and m3 != "" and m4 != "" and m5 == "" and e4 != "":
        all_picked = [m1, m2, m3, m4, e1, e2, e3, e4]
        if e5:
            all_picked.append(e5)
        cannot_draft.extend([h for h in all_picked if h])
        enemy_heroes = [h for h in [e1, e2, e3, e4, e5] if h]
        my_heroes = [m1, m2, m3, m4]

        # Use hybrid counter-pick + synergy
        counters = get_best_counters(enemy_heroes, cannot_draft, num_picks=2)
        synergies = get_best_synergies(my_heroes, cannot_draft, num_picks=2)

        # Combine: prioritize synergies with team, then counters
        combined = []
        for hero in synergies:
            if hero not in combined:
                combined.append(hero)
        for hero in counters:
            if hero not in combined and len(combined) < 1:
                combined.append(hero)

        if combined:
            print(f"Using synergy+counter pick for m5 (main-first): {combined[:1]}")
            return combined[:1]

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
