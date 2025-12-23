"""
Epic Seven RTA Data Fetcher
Fetches player battle data from the official Epic Seven API.

API Endpoints:
- Rankings: https://e7api.onstove.com/gameApi/getWorldUserRankingDetail
- Battle List: https://e7api.onstove.com/gameApi/getBattleList
"""

import json
import os
import requests
import time
from datetime import datetime

# Configuration
OUTPUT_DIR = "e7_data/rta_player_data"
API_BASE = "https://e7api.onstove.com"
CURRENT_SEASON = "pvp_rta_ss18"

SERVERS = {
    "global": "world_global",
    "asia": "world_asia",
    "kor": "world_kor",
    "jpn": "world_jpn",
    "eu": "world_eu"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'Origin': 'https://epic7.onstove.com',
    'Referer': 'https://epic7.onstove.com/en/gg'
}


class E7DataFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.top_players = {}  # Cache for top players by server

    def get_top_players(self, server="global", count=100, season_code=None):
        """Fetch top players from the ranking leaderboard"""
        if season_code is None:
            season_code = CURRENT_SEASON

        world_code = SERVERS.get(server, f"world_{server}")
        url = f"{API_BASE}/gameApi/getWorldUserRankingDetail"
        params = {
            "season_code": season_code,
            "world_code": world_code,
            "lang": "en",
            "page": 1,
            "per_page": count
        }

        try:
            response = self.session.post(url, params=params, json={}, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("return_code") == 0:
                players = data.get("result_body", [])
                return players
            else:
                print(f"  API returned error code: {data.get('return_code')}")
                return []
        except requests.RequestException as e:
            print(f"  Error fetching rankings: {e}")
            return []

    def get_battle_list(self, player_id, server="global", season_code=""):
        """Fetch battle list for a player"""
        world_code = SERVERS.get(server, f"world_{server}")
        url = f"{API_BASE}/gameApi/getBattleList"
        params = {
            "nick_no": player_id,
            "world_code": world_code,
            "lang": "en",
            "season_code": season_code
        }

        try:
            response = self.session.post(url, params=params, json={}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  Error fetching data: {e}")
            return None

    def get_user_info(self, player_id, server="global"):
        """Fetch user info for a player"""
        world_code = SERVERS.get(server, f"world_{server}")
        url = f"{API_BASE}/gameApi/getUserInfo"
        params = {
            "nick_no": player_id,
            "world_code": world_code,
            "lang": "en"
        }

        try:
            response = self.session.post(url, params=params, json={}, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"  Error fetching user info: {e}")
            return None

    def fetch_and_save_player(self, player_id, server="global"):
        """Fetch and save all data for a player"""
        print(f"Fetching data for player {player_id} ({server})...")

        data = self.get_battle_list(player_id, server)

        if data and data.get("return_code") == 0:
            body = data.get("result_body", {})
            battle_count = len(body.get("battle_list", []))
            print(f"  Found {battle_count} battles")

            # Save to file
            output_file = os.path.join(OUTPUT_DIR, f"{player_id}.json")
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"  Saved to: {output_file}")

            return data
        else:
            print(f"  Failed to fetch data (return_code: {data.get('return_code') if data else 'None'})")
            return None

    def fetch_top_100_all_servers(self, servers=None, delay=0.5):
        """Fetch battle data for top 100 players from all servers"""
        if servers is None:
            servers = list(SERVERS.keys())

        total_fetched = 0
        total_battles = 0
        all_rankings = {}

        print(f"\n{'='*60}")
        print(f"EPIC SEVEN TOP 100 DATA FETCHER")
        print(f"Season: {CURRENT_SEASON}")
        print(f"Servers: {', '.join(servers)}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        for server in servers:
            if server not in SERVERS:
                print(f"Unknown server: {server}")
                continue

            print(f"\n{'='*60}")
            print(f"SERVER: {server.upper()}")
            print(f"{'='*60}")

            # Get top 100 players for this server
            print(f"Fetching top 100 rankings...")
            top_players = self.get_top_players(server, count=100)

            if not top_players:
                print(f"  Failed to get rankings for {server}")
                continue

            print(f"  Found {len(top_players)} top players")

            # Save rankings
            all_rankings[server] = top_players
            rankings_file = os.path.join(OUTPUT_DIR, f"rankings_{server}.json")
            with open(rankings_file, 'w') as f:
                json.dump(top_players, f, indent=2)
            print(f"  Saved rankings to: {rankings_file}")

            # Fetch battle data for each player
            server_fetched = 0
            server_battles = 0

            for i, player in enumerate(top_players):
                player_id = player.get("nick_no")
                player_name = player.get("nickname", "Unknown")
                rank = player.get("season_rank", i + 1)

                if not player_id:
                    continue

                # Handle Unicode characters in player names
                try:
                    safe_name = player_name.encode('ascii', 'replace').decode('ascii')
                except:
                    safe_name = f"Player_{player_id}"
                print(f"\n  [{i+1}/100] Rank #{rank}: {safe_name} (ID: {player_id})")

                data = self.fetch_and_save_player(player_id, server)

                if data:
                    server_fetched += 1
                    body = data.get("result_body", {})
                    battles = len(body.get("battle_list", []))
                    server_battles += battles
                    print(f"    Battles: {battles}")

                # Rate limiting to avoid overloading the API
                time.sleep(delay)

            print(f"\n  {server.upper()} COMPLETE: {server_fetched} players, {server_battles} battles")
            total_fetched += server_fetched
            total_battles += server_battles

        # Save summary
        summary = {
            "fetch_date": datetime.now().isoformat(),
            "season": CURRENT_SEASON,
            "servers": servers,
            "total_players": total_fetched,
            "total_battles": total_battles,
            "rankings": {s: len(r) for s, r in all_rankings.items()}
        }
        summary_file = os.path.join(OUTPUT_DIR, "fetch_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n{'='*60}")
        print(f"ALL SERVERS COMPLETE")
        print(f"Total Players: {total_fetched}")
        print(f"Total Battles: {total_battles}")
        print(f"Summary saved to: {summary_file}")
        print(f"{'='*60}")

        return total_fetched, total_battles, all_rankings


def main():
    """Main function - fetch top 100 from all servers"""
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fetcher = E7DataFetcher()

    # Fetch top 100 from all servers
    fetcher.fetch_top_100_all_servers()


if __name__ == "__main__":
    main()
