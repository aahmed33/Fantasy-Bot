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