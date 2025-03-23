from django.shortcuts import render
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import League, Team, Match
from .serializers import LeagueSerializer, TeamSerializer, MatchSerializer, MatchListSerializer
from .api_client import APIFootballClient

logger = logging.getLogger(__name__)

class LeagueListView(APIView):
    """
    API endpoint to list and sync football leagues.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        """
        Get all leagues from MongoDB.
        """
        leagues = League.get_active_leagues()
        serializer = LeagueSerializer(leagues, many=True)
        return Response({
            'count': len(leagues),
            'leagues': serializer.data
        })
    
    def post(self, request):
        """
        Sync leagues from APIFootball to MongoDB.
        """
        try:
            # Get parameters from request
            country = request.data.get('country')
            season = request.data.get('season', datetime.now().year)
            
            # Initialize API client
            api_client = APIFootballClient()
            
            # Get leagues from APIFootball
            leagues_response = api_client.get_leagues(country=country, season=season)
            
            # Check if response is None (API error)
            if leagues_response is None:
                return Response({
                    'message': 'Error fetching leagues from APIFootball',
                    'error': 'API request failed'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Process leagues data
            synced_leagues = []
            
            for league_data in leagues_response:  # leagues_response is already the list of leagues
                try:
                    league = {
                        'id': league_data.get('league', {}).get('id'),
                        'name': league_data.get('league', {}).get('name'),
                        'country': league_data.get('country', {}).get('name'),
                        'logo': league_data.get('league', {}).get('logo'),
                        'type': league_data.get('league', {}).get('type'),
                        'season': season
                    }
                    
                    # Save to MongoDB using your League model
                    saved_league = League.create_or_update(league)
                    if saved_league:
                        synced_leagues.append(saved_league)
                except Exception as e:
                    logger.error(f"Error processing league: {str(e)}")
                    continue
            
            return Response({
                'message': f'Successfully synced {len(synced_leagues)} leagues',
                'count': len(synced_leagues),
                'leagues': LeagueSerializer(synced_leagues, many=True).data
            })
            
        except Exception as e:
            logger.error(f"Error in LeagueListView.post: {str(e)}")
            return Response({
                'message': 'Internal server error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TeamListView(APIView):
    """
    API endpoint to list and sync football teams.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        """
        Get teams from MongoDB, optionally filtered by league.
        """
        league_id = request.query_params.get('league_id')
        
        # Get teams from MongoDB
        teams_collection = Team.get_collection()
        query = {}
        
        if league_id:
            query['league_id'] = int(league_id)
            
        teams = list(teams_collection.find(query))
        
        return Response({
            'count': len(teams),
            'teams': TeamSerializer(teams, many=True).data
        })
    
    def post(self, request):
        """
        Sync teams from APIFootball to MongoDB.
        """
        # Get parameters from request
        league_id = request.data.get('league_id')
        season = request.data.get('season', datetime.now().year)
        
        if not league_id:
            return Response({
                'message': 'league_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize API client
        api_client = APIFootballClient()
        
        # Get teams from APIFootball
        teams_response = api_client.get_teams(league_id=league_id, season=season)
        
        if 'errors' in teams_response:
            return Response({
                'message': 'Error fetching teams from APIFootball',
                'errors': teams_response['errors']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Process teams data
        teams_data = teams_response.get('response', [])
        synced_teams = []
        
        for team_data in teams_data:
            team = Team.create_or_update(team_data)
            if team:
                synced_teams.append(team)
        
        return Response({
            'message': f'Successfully synced {len(synced_teams)} teams',
            'count': len(synced_teams),
            'teams': TeamSerializer(synced_teams, many=True).data
        })


class MatchListView(APIView):
    """
    API endpoint to list and sync football matches.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        """
        Get matches from MongoDB with various filters.
        """
        league_id = request.query_params.get('league_id')
        jornada = request.query_params.get('jornada')
        is_active = request.query_params.get('is_active', 'true').lower() == 'true'
        
        # Determine which method to use based on parameters
        if league_id:
            matches = Match.get_matches_by_league(int(league_id), jornada)
        elif jornada:
            # Get matches for a specific jornada
            matches_collection = Match.get_collection()
            query = {'jornada': jornada}
            if is_active is not None:
                query['is_active'] = is_active
            matches = list(matches_collection.find(query))
        else:
            # Get all active matches
            matches = Match.get_active_matches(jornada)
        
        # Get active jornadas for filtering
        active_jornadas = Match.get_active_jornadas()
        
        return Response({
            'count': len(matches),
            'matches': MatchSerializer(matches, many=True).data,
            'active_jornadas': active_jornadas
        })
    
    def post(self, request):
        """
        Sync matches from APIFootball to MongoDB.
        """
        # Get parameters from request
        league_id = request.data.get('league_id')
        date = request.data.get('date')
        days_range = int(request.data.get('days_range', 7))
        
        if not league_id:
            return Response({
                'message': 'league_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize API client
        api_client = APIFootballClient()
        
        # Get matches with odds from APIFootball
        matches_data = api_client.get_fixtures_with_odds(
            league_id=league_id, 
            date=date, 
            days_range=days_range
        )
        
        if not matches_data:
            return Response({
                'message': 'No matches found or error fetching matches from APIFootball'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Process matches data
        synced_matches = []
        
        for match_data in matches_data:
            match = Match.create_or_update(match_data)
            if match:
                synced_matches.append(match)
        
        # Get active jornadas after sync
        active_jornadas = Match.get_active_jornadas()
        
        return Response({
            'message': f'Successfully synced {len(synced_matches)} matches',
            'count': len(synced_matches),
            'matches': MatchSerializer(synced_matches, many=True).data,
            'active_jornadas': active_jornadas
        })


class MatchDetailView(APIView):
    """
    API endpoint to get, update, or delete a specific match.
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request, fixture_id):
        """
        Get a specific match by fixture_id.
        """
        match = Match.get_match_by_id(int(fixture_id))
        
        if not match:
            return Response({
                'message': f'Match with fixture_id {fixture_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(MatchSerializer(match).data)
    
    def put(self, request, fixture_id):
        """
        Update a specific match.
        """
        match = Match.get_match_by_id(int(fixture_id))
        
        if not match:
            return Response({
                'message': f'Match with fixture_id {fixture_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update match status
        status_value = request.data.get('status')
        score = request.data.get('score')
        
        if status_value:
            success = Match.update_match_status(int(fixture_id), status_value, score)
            
            if success:
                updated_match = Match.get_match_by_id(int(fixture_id))
                return Response({
                    'message': 'Match updated successfully',
                    'match': MatchSerializer(updated_match).data
                })
            else:
                return Response({
                    'message': 'Failed to update match'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': 'No updates provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, fixture_id):
        """
        Deactivate a specific match.
        """
        match = Match.get_match_by_id(int(fixture_id))
        
        if not match:
            return Response({
                'message': f'Match with fixture_id {fixture_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Deactivate the match
        count = Match.deactivate_matches([int(fixture_id)])
        
        if count > 0:
            return Response({
                'message': 'Match deactivated successfully'
            })
        else:
            return Response({
                'message': 'Failed to deactivate match'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JornadaManagementView(APIView):
    """
    API endpoint to manage jornadas (match days/rounds).
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        """
        Get all active jornadas.
        """
        active_jornadas = Match.get_active_jornadas()
        
        return Response({
            'active_jornadas': active_jornadas
        })
    
    def post(self, request):
        """
        Create a new jornada by syncing matches for a specific date range.
        """
        # Get parameters from request
        league_id = request.data.get('league_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        jornada_name = request.data.get('jornada_name')
        
        if not all([league_id, start_date, end_date, jornada_name]):
            return Response({
                'message': 'league_id, start_date, end_date, and jornada_name are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize API client
        api_client = APIFootballClient()
        
        # Get matches for the date range
        fixtures_response = api_client.get_fixtures(
            league_id=league_id,
            from_date=start_date,
            to_date=end_date
        )
        
        if 'errors' in fixtures_response or not fixtures_response.get('response'):
            return Response({
                'message': 'Error fetching fixtures from APIFootball',
                'errors': fixtures_response.get('errors', ['Unknown error'])
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Process matches data
        fixtures = fixtures_response['response']
        synced_matches = []
        
        for fixture in fixtures:
            # Add jornada name to the fixture data
            fixture['jornada'] = jornada_name
            
            # Get odds for the fixture
            fixture_id = fixture['fixture']['id']
            odds_response = api_client.get_odds(fixture_id=fixture_id)
            
            if 'errors' not in odds_response and odds_response.get('response'):
                odds_data = odds_response['response']
                
                # Extract 1X2 odds from the first bookmaker
                odds = {"home": 2.0, "draw": 3.0, "away": 4.0}  # Default odds
                
                for odds_item in odds_data:
                    bookmaker = odds_item.get('bookmakers', [])[0] if odds_item.get('bookmakers') else None
                    if bookmaker:
                        bets = bookmaker.get('bets', [])[0] if bookmaker.get('bets') else None
                        if bets and bets.get('name') == 'Match Winner':
                            for value in bets.get('values', []):
                                if value.get('value') == 'Home':
                                    odds['home'] = float(value.get('odd', 2.0))
                                elif value.get('value') == 'Draw':
                                    odds['draw'] = float(value.get('odd', 3.0))
                                elif value.get('value') == 'Away':
                                    odds['away'] = float(value.get('odd', 4.0))
                            break
                
                fixture['odds'] = odds
            
            # Create or update the match in MongoDB
            match = Match.create_or_update(fixture)
            if match:
                synced_matches.append(match)
        
        return Response({
            'message': f'Successfully created jornada "{jornada_name}" with {len(synced_matches)} matches',
            'count': len(synced_matches),
            'matches': MatchSerializer(synced_matches, many=True).data
        })
    
    def put(self, request):
        """
        Update matches for a specific jornada.
        """
        jornada_name = request.data.get('jornada_name')
        is_active = request.data.get('is_active')
        
        if not jornada_name:
            return Response({
                'message': 'jornada_name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get matches for the jornada
        matches_collection = Match.get_collection()
        query = {'jornada': jornada_name}
        
        # Update matches
        update_doc = {'last_updated': timezone.now()}
        
        if is_active is not None:
            update_doc['is_active'] = is_active
        
        result = matches_collection.update_many(
            query,
            {'$set': update_doc}
        )
        
        if result.modified_count > 0:
            return Response({
                'message': f'Successfully updated {result.modified_count} matches for jornada "{jornada_name}"'
            })
        else:
            return Response({
                'message': f'No matches found for jornada "{jornada_name}" or no updates needed'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request):
        """
        Delete (deactivate) all matches for a specific jornada.
        """
        jornada_name = request.query_params.get('jornada_name')
        
        if not jornada_name:
            return Response({
                'message': 'jornada_name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get matches for the jornada
        matches_collection = Match.get_collection()
        query = {'jornada': jornada_name}
        
        # Deactivate matches
        result = matches_collection.update_many(
            query,
            {'$set': {'is_active': False, 'last_updated': timezone.now()}}
        )
        
        if result.modified_count > 0:
            return Response({
                'message': f'Successfully deactivated {result.modified_count} matches for jornada "{jornada_name}"'
            })
        else:
            return Response({
                'message': f'No matches found for jornada "{jornada_name}" or they are already deactivated'
            }, status=status.HTTP_404_NOT_FOUND)


class AssignCoinsView(APIView):
    """
    API endpoint to assign coins to users for a specific jornada.
    """
    permission_classes = [permissions.IsAdminUser]
    authentication_classes = [JWTAuthentication]
    
    def post(self, request):
        """
        Assign coins to all users for a specific jornada.
        """
        from users.models import User
        from django.db.models import F
        from decimal import Decimal
        
        jornada_name = request.data.get('jornada_name', 'current')
        coins_amount = Decimal(str(request.data.get('coins_amount', 100.00)))
        
        # Get all active users
        users = User.objects.filter(is_active=True)
        
        # Assign coins to each user
        assigned_count = 0
        
        for user in users:
            user.virtual_coins = F('virtual_coins') + coins_amount
            user.last_coins_assignment = timezone.now()
            user.save(update_fields=['virtual_coins', 'last_coins_assignment'])
            user.sync_to_mongodb()
            assigned_count += 1
        
        return Response({
            'message': f'Successfully assigned {coins_amount} coins to {assigned_count} users for jornada "{jornada_name}"',
            'assigned_count': assigned_count,
            'coins_amount': float(coins_amount)
        })
