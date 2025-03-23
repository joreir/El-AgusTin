from django.urls import path
from . import views

urlpatterns = [
    # League endpoints
    path('leagues/', views.LeagueListView.as_view(), name='league-list'),
    
    # Team endpoints
    path('teams/', views.TeamListView.as_view(), name='team-list'),
    
    # Match endpoints
    path('matches/', views.MatchListView.as_view(), name='match-list'),
    path('matches/<int:fixture_id>/', views.MatchDetailView.as_view(), name='match-detail'),
    
    # Jornada management endpoints
    path('jornadas/', views.JornadaManagementView.as_view(), name='jornada-management'),
    
    # Assign coins endpoint
    path('assign-coins/', views.AssignCoinsView.as_view(), name='assign-coins'),
]
