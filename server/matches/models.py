from django.db import models
from django.utils import timezone
from pymongo import MongoClient
from django.conf import settings
from decimal import Decimal
import json
from bson import ObjectId

class League:
    """
    Model representing a football league.
    This is a MongoDB model, not a Django ORM model.
    """
    @staticmethod
    def get_collection():
        client = MongoClient(settings.MONGODB_HOST, settings.MONGODB_PORT)
        db = client[settings.MONGODB_DB_NAME]
        return db.leagues
    
    @classmethod
    def create_or_update(cls, league_data):
        """
        Create or update a league in MongoDB based on data from APIFootball.
        """
        collection = cls.get_collection()
        
        # Extract relevant data
        league_id = league_data.get('id')
        if not league_id:
            return None
            
        league_doc = {
            'league_id': league_id,
            'name': league_data.get('name'),
            'country': league_data.get('country'),
            'logo': league_data.get('logo'),
            'type': league_data.get('type'),
            'season': league_data.get('season'),
            'is_active': True,
            'last_updated': timezone.now()
        }
        
        # Update or insert the league document
        try:
            result = collection.update_one(
                {'league_id': league_id},
                {'$set': league_doc},
                upsert=True
            )
            league_doc['_id'] = str(result.upserted_id) if result.upserted_id else None
            return league_doc
        except Exception as e:
            print(f"Error saving league to MongoDB: {str(e)}")
            return None
    
    @classmethod
    def get_active_leagues(cls):
        """
        Get all active leagues from MongoDB.
        """
        collection = cls.get_collection()
        return list(collection.find({'is_active': True}))


class Team:
    """
    Model representing a football team.
    This is a MongoDB model, not a Django ORM model.
    """
    @staticmethod
    def get_collection():
        client = MongoClient(settings.MONGODB_HOST, settings.MONGODB_PORT)
        db = client[settings.MONGODB_DB_NAME]
        return db.teams
    
    @classmethod
    def create_or_update(cls, team_data):
        """
        Create or update a team in MongoDB based on data from APIFootball.
        """
        collection = cls.get_collection()
        
        # Extract relevant data from API response
        team_id = team_data.get('team', {}).get('id')
        if not team_id:
            return None
            
        team_doc = {
            'team_id': team_id,
            'name': team_data.get('team', {}).get('name'),
            'logo': team_data.get('team', {}).get('logo'),
            'country': team_data.get('team', {}).get('country'),
            'founded': team_data.get('team', {}).get('founded'),
            'last_updated': timezone.now()
        }
        
        # Update or insert the team document
        result = collection.update_one(
            {'team_id': team_id},
            {'$set': team_doc},
            upsert=True
        )
        
        return team_doc


class Match:
    """
    Model representing a football match.
    This is a MongoDB model, not a Django ORM model.
    """
    @staticmethod
    def get_collection():
        client = MongoClient(settings.MONGODB_HOST, settings.MONGODB_PORT)
        db = client[settings.MONGODB_DB_NAME]
        return db.matches
    
    @classmethod
    def create_or_update(cls, match_data):
        """
        Create or update a match in MongoDB based on data from APIFootball.
        """
        collection = cls.get_collection()
        
        # Extract relevant data from API response
        fixture_id = match_data.get('fixture', {}).get('id')
        if not fixture_id:
            return None
        
        # Create odds data with default values
        odds = {
            'home': Decimal('2.0'),  # Default odds for home team win
            'draw': Decimal('3.0'),  # Default odds for draw
            'away': Decimal('4.0')   # Default odds for away team win
        }
        
        # If odds data is provided in the match_data, update the default values
        if 'odds' in match_data and isinstance(match_data['odds'], dict):
            for bet_type, bet_value in match_data['odds'].items():
                if bet_type in odds and isinstance(bet_value, (int, float, str, Decimal)):
                    odds[bet_type] = Decimal(str(bet_value))
        
        match_doc = {
            'fixture_id': fixture_id,
            'league_id': match_data.get('league', {}).get('id'),
            'league_name': match_data.get('league', {}).get('name'),
            'league_country': match_data.get('league', {}).get('country'),
            'league_logo': match_data.get('league', {}).get('logo'),
            'season': match_data.get('league', {}).get('season'),
            'round': match_data.get('league', {}).get('round'),
            'home_team_id': match_data.get('teams', {}).get('home', {}).get('id'),
            'home_team_name': match_data.get('teams', {}).get('home', {}).get('name'),
            'home_team_logo': match_data.get('teams', {}).get('home', {}).get('logo'),
            'away_team_id': match_data.get('teams', {}).get('away', {}).get('id'),
            'away_team_name': match_data.get('teams', {}).get('away', {}).get('name'),
            'away_team_logo': match_data.get('teams', {}).get('away', {}).get('logo'),
            'date': match_data.get('fixture', {}).get('date'),
            'timestamp': match_data.get('fixture', {}).get('timestamp'),
            'venue': match_data.get('fixture', {}).get('venue', {}).get('name'),
            'status': match_data.get('fixture', {}).get('status', {}).get('short'),
            'elapsed': match_data.get('fixture', {}).get('status', {}).get('elapsed'),
            'score': {
                'home': match_data.get('goals', {}).get('home'),
                'away': match_data.get('goals', {}).get('away')
            },
            'odds': {
                'home': float(odds['home']),
                'draw': float(odds['draw']),
                'away': float(odds['away'])
            },
            'is_active': True,  # By default, all matches are active
            'jornada': match_data.get('jornada', 'current'),  # Jornada identifier
            'last_updated': timezone.now()
        }
        
        # Update or insert the match document
        result = collection.update_one(
            {'fixture_id': fixture_id},
            {'$set': match_doc},
            upsert=True
        )
        
        return match_doc
    
    @classmethod
    def get_active_matches(cls, jornada=None):
        """
        Get all active matches from MongoDB, optionally filtered by jornada.
        """
        collection = cls.get_collection()
        query = {'is_active': True}
        
        if jornada:
            query['jornada'] = jornada
            
        return list(collection.find(query))
    
    @classmethod
    def get_matches_by_league(cls, league_id, jornada=None):
        """
        Get all matches for a specific league, optionally filtered by jornada.
        """
        collection = cls.get_collection()
        query = {'league_id': league_id}
        
        if jornada:
            query['jornada'] = jornada
            
        return list(collection.find(query))
    
    @classmethod
    def get_match_by_id(cls, fixture_id):
        """
        Get a specific match by its fixture_id.
        """
        collection = cls.get_collection()
        return collection.find_one({'fixture_id': fixture_id})
    
    @classmethod
    def update_match_status(cls, fixture_id, status, score=None):
        """
        Update the status and score of a match.
        """
        collection = cls.get_collection()
        update_doc = {
            'status': status,
            'last_updated': timezone.now()
        }
        
        if score:
            update_doc['score'] = score
            
        result = collection.update_one(
            {'fixture_id': fixture_id},
            {'$set': update_doc}
        )
        
        return result.modified_count > 0
    
    @classmethod
    def deactivate_matches(cls, fixture_ids=None):
        """
        Deactivate matches, either specific ones or all.
        """
        collection = cls.get_collection()
        query = {}
        
        if fixture_ids:
            query = {'fixture_id': {'$in': fixture_ids}}
            
        result = collection.update_many(
            query,
            {'$set': {'is_active': False, 'last_updated': timezone.now()}}
        )
        
        return result.modified_count
    
    @classmethod
    def get_matches_by_date_range(cls, start_date, end_date):
        """
        Get matches within a specific date range.
        Dates should be in ISO format strings.
        """
        collection = cls.get_collection()
        query = {
            'date': {
                '$gte': start_date,
                '$lte': end_date
            }
        }
        
        return list(collection.find(query))
    
    @classmethod
    def get_matches_aggregation(cls, pipeline):
        """
        Run a custom aggregation pipeline on the matches collection.
        """
        collection = cls.get_collection()
        return list(collection.aggregate(pipeline))
    
    @classmethod
    def get_active_jornadas(cls):
        """
        Get all active jornadas (match days/rounds).
        """
        collection = cls.get_collection()
        pipeline = [
            {'$match': {'is_active': True}},
            {'$group': {'_id': '$jornada'}},
            {'$project': {'jornada': '$_id', '_id': 0}}
        ]
        
        result = list(collection.aggregate(pipeline))
        return [doc['jornada'] for doc in result]
