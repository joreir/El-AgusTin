from django.shortcuts import render
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import authenticate
from .serializers import UserSerializer, UserRegistrationSerializer, UserLoginSerializer
from django.utils import timezone

# Create your views here.

class RegisterView(generics.CreateAPIView):
    """
    API endpoint that allows users to register.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        # Return the user data and tokens
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    API endpoint that allows users to login and get tokens.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response({
                'message': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate tokens for the authenticated user
        refresh = RefreshToken.for_user(user)
        
        # Check if user needs coins assignment based on active matches
        self.assign_coins_if_needed(user)
        
        # Return the user data and tokens
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Login exitoso'
        })
    
    def assign_coins_if_needed(self, user):
        """
        Check if the user needs coins assignment based on active matches.
        This is a simplified version, in a real implementation you would check
        if there are active matches in the current "jornada".
        """
        # For now, let's check if the user has never received coins 
        # or if the last assignment was more than 24 hours ago
        if (user.last_coins_assignment is None or 
            (timezone.now() - user.last_coins_assignment).days >= 1):
            user.assign_initial_coins()


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint that allows users to view and update their profile.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get_object(self):
        return self.request.user
