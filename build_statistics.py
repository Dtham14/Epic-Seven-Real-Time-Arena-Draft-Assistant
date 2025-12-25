"""
Epic Seven Draft Statistics Builder

Pre-computes all draft statistics from the dataset using vectorized pandas operations.
Generates both JSON (human-readable) and pickle (fast loading) formats.

Usage:
    python build_statistics.py

Output Files:
    e7_data/hero_winrates.json / .pkl
    e7_data/hero_pickrates.json / .pkl
    e7_data/hero_matchups.json / .pkl
    e7_data/hero_synergies.json / .pkl
"""

import pandas as pd
import pickle
import json
from pathlib import Path
from tqdm import tqdm

# Constants
DATA_DIR = Path("e7_data")
DATASET_PATH = DATA_DIR / "drafts_dataset.csv"
MIN_SAMPLES = 5  # Minimum matchups for statistical significance
DEFAULT_WINRATE = 0.5

def load_dataset():
    """Load and validate dataset"""
    print("Loading dataset...")
    df = pd.read_csv(DATASET_PATH)
    print(f"Loaded {len(df):,} matches")
    return df

def compute_hero_winrates(df):
    """
    Compute overall winrate for each hero across all matches.
    Returns: dict {hero_name: winrate}
    """
    print("\n[1/4] Computing hero winrates...")

    # Unpivot all hero columns (main + enemy)
    main_cols = ['main1', 'main2', 'main3', 'main4', 'main5']
    enemy_cols = ['enemy1', 'enemy2', 'enemy3', 'enemy4', 'enemy5']

    # Main heroes: is_win=0 means they won
    main_heroes = pd.melt(df, id_vars=['is_win'], value_vars=main_cols, value_name='hero')
    main_heroes['won'] = (main_heroes['is_win'] == 0).astype(int)

    # Enemy heroes: is_win=1 means they won
    enemy_heroes = pd.melt(df, id_vars=['is_win'], value_vars=enemy_cols, value_name='hero')
    enemy_heroes['won'] = (enemy_heroes['is_win'] == 1).astype(int)

    # Combine
    all_heroes = pd.concat([main_heroes, enemy_heroes])
    all_heroes = all_heroes[all_heroes['hero'].notna() & (all_heroes['hero'] != '')]

    # Aggregate
    winrates = all_heroes.groupby('hero').agg(
        total_games=('won', 'count'),
        total_wins=('won', 'sum')
    ).reset_index()

    winrates['winrate'] = winrates['total_wins'] / winrates['total_games']

    # Convert to dict
    result = dict(zip(winrates['hero'], winrates['winrate']))
    print(f"  Computed winrates for {len(result)} heroes")
    return result

def compute_hero_pickrates(df):
    """
    Compute pick frequency for each hero.
    Returns: dict {hero_name: pick_rate}
    """
    print("\n[2/4] Computing hero pickrates...")

    total_matches = len(df)
    all_cols = ['main1', 'main2', 'main3', 'main4', 'main5',
                'enemy1', 'enemy2', 'enemy3', 'enemy4', 'enemy5']

    # Unpivot all picks
    all_picks = pd.melt(df, value_vars=all_cols, value_name='hero')
    all_picks = all_picks[all_picks['hero'].notna() & (all_picks['hero'] != '')]

    # Count appearances
    pick_counts = all_picks['hero'].value_counts()
    pick_rates = (pick_counts / total_matches).to_dict()

    print(f"  Computed pickrates for {len(pick_rates)} heroes")
    return pick_rates

def compute_hero_matchups(df):
    """
    Compute winrate matrix: my_hero vs enemy_hero.
    Returns: nested dict {my_hero: {enemy_hero: winrate}}
    """
    print("\n[3/4] Computing hero matchups (counter matrix)...")

    # Unpivot main heroes
    main_melted = pd.melt(
        df.reset_index(),
        id_vars=['index', 'is_win'],
        value_vars=['main1', 'main2', 'main3', 'main4', 'main5'],
        value_name='my_hero'
    )

    # Unpivot enemy heroes
    enemy_melted = pd.melt(
        df.reset_index(),
        id_vars=['index', 'is_win'],
        value_vars=['enemy1', 'enemy2', 'enemy3', 'enemy4', 'enemy5'],
        value_name='enemy_hero'
    )

    # Create matchup pairs (cross join on match index)
    matchups = main_melted.merge(enemy_melted, on=['index', 'is_win'], suffixes=('', '_y'))
    matchups = matchups[matchups['my_hero'].notna() & matchups['enemy_hero'].notna()]
    matchups = matchups[matchups['my_hero'] != '']
    matchups = matchups[matchups['enemy_hero'] != '']

    # Aggregate
    print("  Aggregating matchup statistics...")
    matchup_stats = matchups.groupby(['my_hero', 'enemy_hero']).agg(
        total=('is_win', 'count'),
        wins=('is_win', lambda x: (x == 0).sum())
    ).reset_index()

    matchup_stats['winrate'] = matchup_stats['wins'] / matchup_stats['total']

    # Apply minimum sample filter
    matchup_stats.loc[matchup_stats['total'] < MIN_SAMPLES, 'winrate'] = DEFAULT_WINRATE

    # Convert to nested dict
    result = {}
    for _, row in tqdm(matchup_stats.iterrows(), total=len(matchup_stats), desc="  Building matrix"):
        my_hero = row['my_hero']
        enemy_hero = row['enemy_hero']
        if my_hero not in result:
            result[my_hero] = {}
        result[my_hero][enemy_hero] = float(row['winrate'])

    print(f"  Computed {len(result)} heroes with matchup data")
    return result

def compute_historical_patterns(df):
    """
    Pre-compute common draft patterns for instant lookups.
    Returns: dict with pattern lookups for different draft stages
    """
    print("\n[4/5] Computing historical draft patterns...")

    patterns = {}

    # Enemy first pick patterns (is_first=0)
    print("  Computing enemy-first-pick patterns...")

    # Pattern 1: m1m2 after e1
    # Group by e1, get top m1,m2 combinations
    enemy_first = df[df['is_first'] == 0].copy()
    pattern_m1m2 = enemy_first.groupby('enemy1').apply(
        lambda g: g[['main1', 'main2']].value_counts().head(10).index.tolist()
    ).to_dict()
    patterns['enemy_m1m2'] = pattern_m1m2

    # Pattern 2: m3m4 after e1,e2,e3
    # Group by (e2, e3), get top m3,m4 combinations
    pattern_m3m4_raw = enemy_first.groupby(['enemy2', 'enemy3']).apply(
        lambda g: g[['main3', 'main4']].value_counts().head(10).index.tolist()
    ).to_dict()
    # Convert tuple keys to strings for JSON serialization
    pattern_m3m4 = {f"{k[0]}|{k[1]}": v for k, v in pattern_m3m4_raw.items()}
    patterns['enemy_m3m4'] = pattern_m3m4

    # Pattern 3: m5 after e1,e2,e3,e4,e5
    # Group by (e4, e5), get top m5 picks
    pattern_m5_raw = enemy_first.groupby(['enemy4', 'enemy5']).apply(
        lambda g: g['main5'].value_counts().head(10).index.tolist()
    ).to_dict()
    # Convert tuple keys to strings for JSON serialization
    pattern_m5 = {f"{k[0]}|{k[1]}": v for k, v in pattern_m5_raw.items()}
    patterns['enemy_m5'] = pattern_m5

    # Main first pick patterns (is_first=1)
    print("  Computing main-first-pick patterns...")

    main_first = df[df['is_first'] == 1].copy()

    # Pattern 4: m2m3 after m1,e1,e2
    # Group by (e1, e2), get top m2,m3 combinations
    pattern_m2m3_raw = main_first.groupby(['enemy1', 'enemy2']).apply(
        lambda g: g[['main2', 'main3']].value_counts().head(10).index.tolist()
    ).to_dict()
    # Convert tuple keys to strings for JSON serialization
    pattern_m2m3 = {f"{k[0]}|{k[1]}": v for k, v in pattern_m2m3_raw.items()}
    patterns['main_m2m3'] = pattern_m2m3

    # Pattern 5: m4m5 after m1,e1,e2,m2,m3,e3,e4
    # Group by (e3, e4), get top m4,m5 combinations
    pattern_m4m5_raw = main_first.groupby(['enemy3', 'enemy4']).apply(
        lambda g: g[['main4', 'main5']].value_counts().head(10).index.tolist()
    ).to_dict()
    # Convert tuple keys to strings for JSON serialization
    pattern_m4m5 = {f"{k[0]}|{k[1]}": v for k, v in pattern_m4m5_raw.items()}
    patterns['main_m4m5'] = pattern_m4m5

    # Count total patterns
    total_patterns = sum(len(p) for p in patterns.values())
    print(f"  Computed {total_patterns} total pattern lookups")

    return patterns

def compute_hero_synergies(df):
    """
    Compute synergy matrix: winrate when hero_1 and hero_2 are on same team.
    Returns: nested dict {hero_1: {hero_2: winrate}}
    """
    print("\n[5/5] Computing hero synergies (NEW)...")

    # Unpivot main team heroes
    main_heroes = pd.melt(
        df.reset_index(),
        id_vars=['index', 'is_win'],
        value_vars=['main1', 'main2', 'main3', 'main4', 'main5'],
        value_name='hero'
    )
    main_heroes = main_heroes[main_heroes['hero'].notna() & (main_heroes['hero'] != '')]

    # Self-join to get all pairs on same team
    print("  Creating hero pair combinations...")
    synergies = main_heroes.merge(main_heroes, on=['index', 'is_win'], suffixes=('_1', '_2'))

    # Only keep unique pairs (alphabetically sorted to avoid duplicates)
    synergies = synergies[synergies['hero_1'] < synergies['hero_2']]

    # Aggregate
    print("  Aggregating synergy statistics...")
    synergy_stats = synergies.groupby(['hero_1', 'hero_2']).agg(
        total=('is_win', 'count'),
        wins=('is_win', lambda x: (x == 0).sum())
    ).reset_index()

    synergy_stats['winrate'] = synergy_stats['wins'] / synergy_stats['total']
    synergy_stats.loc[synergy_stats['total'] < MIN_SAMPLES, 'winrate'] = DEFAULT_WINRATE

    # Convert to nested dict (symmetric: store both hero_1->hero_2 and hero_2->hero_1)
    result = {}
    for _, row in tqdm(synergy_stats.iterrows(), total=len(synergy_stats), desc="  Building synergy matrix"):
        h1, h2 = row['hero_1'], row['hero_2']
        winrate = float(row['winrate'])

        if h1 not in result:
            result[h1] = {}
        if h2 not in result:
            result[h2] = {}

        result[h1][h2] = winrate
        result[h2][h1] = winrate  # Symmetric

    print(f"  Computed synergies for {len(result)} heroes")
    return result

def save_statistics(stats_dict, base_name):
    """
    Save statistics to both JSON and pickle formats.

    Args:
        stats_dict: Dictionary containing statistics
        base_name: Base filename (without extension)
    """
    json_path = DATA_DIR / f"{base_name}.json"
    pkl_path = DATA_DIR / f"{base_name}.pkl"

    # Save JSON (human-readable, for inspection)
    with open(json_path, 'w') as f:
        json.dump(stats_dict, f, indent=2)
    print(f"  Saved {json_path}")

    # Save pickle (fast loading)
    with open(pkl_path, 'wb') as f:
        pickle.dump(stats_dict, f)
    print(f"  Saved {pkl_path}")

def main():
    """Main execution"""
    print("="*60)
    print("Epic Seven Draft Statistics Builder")
    print("="*60)

    # Load dataset
    df = load_dataset()

    # Compute all statistics
    winrates = compute_hero_winrates(df)
    pickrates = compute_hero_pickrates(df)
    matchups = compute_hero_matchups(df)
    patterns = compute_historical_patterns(df)
    synergies = compute_hero_synergies(df)

    # Save all results
    print("\n" + "="*60)
    print("Saving statistics to disk...")
    print("="*60)

    save_statistics(winrates, "hero_winrates")
    save_statistics(pickrates, "hero_pickrates")
    save_statistics(matchups, "hero_matchups")
    save_statistics(patterns, "draft_patterns")
    save_statistics(synergies, "hero_synergies")

    print("\n" + "="*60)
    print("Statistics generation complete!")
    print("="*60)
    print("\nGenerated files:")
    print(f"  - {DATA_DIR}/hero_winrates.json / .pkl")
    print(f"  - {DATA_DIR}/hero_pickrates.json / .pkl")
    print(f"  - {DATA_DIR}/hero_matchups.json / .pkl")
    print(f"  - {DATA_DIR}/draft_patterns.json / .pkl (NEW)")
    print(f"  - {DATA_DIR}/hero_synergies.json / .pkl")
    print("\nYou can now run the Flask app with pre-computed statistics.")

if __name__ == "__main__":
    main()
