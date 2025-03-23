import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class APIFootballClient:
   # En api_client.py
    def __init__(self):
        self.base_url = f"https://{settings.API_FOOTBALL_HOST}/v3"  
        self.headers = {
            "X-RapidAPI-Key": settings.API_FOOTBALL_KEY,  
            "X-RapidAPI-Host": settings.API_FOOTBALL_HOST
        }
                                                        

    def _make_request(self, endpoint, params=None):
        """
        Realiza una petición a la API de Football
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data and data["errors"]:
                logger.error(f"Error from API Football: {data['errors']}")
                return None
                
            return data.get("response", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making request to API Football: {str(e)}")
            return None

    def get_leagues(self, country=None, season=None):
        """
        Obtiene las ligas disponibles
        """
        params = {}
        if country:
            params["country"] = country
        if season:
            params["season"] = season
            
        return self._make_request("leagues", params)

    def get_teams(self, league_id, season):
        """
        Obtiene los equipos de una liga específica
        """
        params = {
            "league": league_id,
            "season": season
        }
        return self._make_request("teams", params)

    def get_fixtures(self, league_id=None, season=None, team_id=None, date=None):
        """
        Obtiene los partidos según los filtros proporcionados
        """
        params = {}
        if league_id:
            params["league"] = league_id
        if season:
            params["season"] = season
        if team_id:
            params["team"] = team_id
        if date:
            params["date"] = date
            
        return self._make_request("fixtures", params)

    def get_fixture_by_id(self, fixture_id):
        """
        Obtiene un partido específico por su ID
        """
        params = {
            "id": fixture_id
        }
        return self._make_request("fixtures", params)

    def get_odds(self, fixture_id=None):
        """
        Obtiene las cuotas de un partido específico
        """
        params = {}
        if fixture_id:
            params["fixture"] = fixture_id
            
        return self._make_request("odds", params)

    def get_fixtures_with_odds(self, league_id=None, date=None):
        """
        Obtiene partidos con sus cuotas
        """
        fixtures = self.get_fixtures(league_id=league_id, date=date)
        if not fixtures:
            return []
            
        result = []
        for fixture in fixtures:
            fixture_id = fixture.get("fixture", {}).get("id")
            if fixture_id:
                odds = self.get_odds(fixture_id)
                if odds:
                    fixture["odds"] = odds
                result.append(fixture)
                
        return result
