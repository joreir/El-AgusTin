from rest_framework import serializers

class LeagueSerializer(serializers.Serializer):
    """
    Serializer for League data.
    """
    league_id = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100)
    logo = serializers.URLField(allow_null=True, required=False)
    season = serializers.IntegerField(allow_null=True, required=False)
    last_updated = serializers.DateTimeField(read_only=True)

class TeamSerializer(serializers.Serializer):
    """
    Serializer for Team data.
    """
    team_id = serializers.IntegerField()
    name = serializers.CharField(max_length=100)
    logo = serializers.URLField(allow_null=True, required=False)
    country = serializers.CharField(max_length=100, allow_null=True, required=False)
    founded = serializers.IntegerField(allow_null=True, required=False)
    last_updated = serializers.DateTimeField(read_only=True)

class ScoreSerializer(serializers.Serializer):
    """
    Serializer for match score data.
    """
    home = serializers.IntegerField(allow_null=True, required=False)
    away = serializers.IntegerField(allow_null=True, required=False)

class OddsSerializer(serializers.Serializer):
    """
    Serializer for match odds data.
    """
    home = serializers.FloatField(default=2.0)
    draw = serializers.FloatField(default=3.0)
    away = serializers.FloatField(default=4.0)

class MatchSerializer(serializers.Serializer):
    """
    Serializer for Match data.
    """
    fixture_id = serializers.IntegerField()
    league_id = serializers.IntegerField()
    league_name = serializers.CharField(max_length=100)
    league_country = serializers.CharField(max_length=100, allow_null=True, required=False)
    league_logo = serializers.URLField(allow_null=True, required=False)
    season = serializers.IntegerField(allow_null=True, required=False)
    round = serializers.CharField(max_length=50, allow_null=True, required=False)
    home_team_id = serializers.IntegerField()
    home_team_name = serializers.CharField(max_length=100)
    home_team_logo = serializers.URLField(allow_null=True, required=False)
    away_team_id = serializers.IntegerField()
    away_team_name = serializers.CharField(max_length=100)
    away_team_logo = serializers.URLField(allow_null=True, required=False)
    date = serializers.CharField(max_length=50)
    timestamp = serializers.IntegerField(allow_null=True, required=False)
    venue = serializers.CharField(max_length=100, allow_null=True, required=False)
    status = serializers.CharField(max_length=20, allow_null=True, required=False)
    elapsed = serializers.IntegerField(allow_null=True, required=False)
    score = ScoreSerializer(allow_null=True, required=False)
    odds = OddsSerializer(required=False)
    is_active = serializers.BooleanField(default=True)
    jornada = serializers.CharField(max_length=50, default="current")
    last_updated = serializers.DateTimeField(read_only=True)

class MatchListSerializer(serializers.Serializer):
    """
    Serializer for a list of matches with pagination info.
    """
    count = serializers.IntegerField()
    matches = MatchSerializer(many=True)
    active_jornadas = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
