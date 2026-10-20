import requests

from .config import SLEEPER_API_BASE_URL


class SleeperClient:
    """Client for interacting with the Sleeper API."""

    def __init__(self):
        self.base_url = SLEEPER_API_BASE_URL

    def _get(self, endpoint):
        """Send a GET request to the Sleeper API."""

        url = f"{self.base_url}/{endpoint}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        return response.json()

    def get_league(self, league_id):
        """Get information about a league."""

        return self._get(f"league/{league_id}")

    def get_users(self, league_id):
        """Get the users/managers in a league."""

        return self._get(f"league/{league_id}/users")

    def get_rosters(self, league_id):
        """Get the rosters in a league."""

        return self._get(f"league/{league_id}/rosters")

    def get_matchups(self, league_id, week):
        """Get all matchups for a particular week."""

        return self._get(f"league/{league_id}/matchups/{week}")

    def get_nfl_state(self):
        return self._get("state/nfl")

    def get_playoff_bracket(self, league_id, bracket="winners"):
        """Official bracket results; winners and consolation stay separate."""
        if bracket not in ("winners", "losers"):
            raise ValueError("Expected winners or losers bracket")
        return self._get(f"league/{league_id}/{bracket}_bracket")

    def get_league_history(self, league_id):
        """
        Retrieve every season in a league's history by following
        Sleeper's previous_league_id chain.
        """

        leagues = []
        current_league_id = league_id

        seen = set()
        while current_league_id and str(current_league_id) != "0":
            if current_league_id in seen:
                raise ValueError("Cycle in league history")
            seen.add(current_league_id)
            league = self.get_league(current_league_id)

            leagues.append(league)

            current_league_id = league.get("previous_league_id")

        return leagues
