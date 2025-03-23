from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from pymongo import MongoClient
from django.conf import settings
from decimal import Decimal

# Create your models here.

class User(AbstractUser):
    """
    Custom user model for Apuestin platform.
    Extends Django's AbstractUser to include virtual coins and tracking of coin assignments.
    """
    virtual_coins = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Amount of virtual coins the user currently has"
    )
    last_coins_assignment = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date and time when coins were last assigned to this user"
    )
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.username
    
    def assign_initial_coins(self, amount=Decimal('100.00')):
        """
        Assign initial coins to the user if they haven't received any for the current active match period.
        Returns True if coins were assigned, False otherwise.
        """
        self.virtual_coins += Decimal(str(amount))
        self.last_coins_assignment = timezone.now()
        self.save(update_fields=['virtual_coins', 'last_coins_assignment'])
        
        # Also update the MongoDB record if it exists
        self.sync_to_mongodb()
        return True
        
    def sync_to_mongodb(self):
        """
        Synchronize user data to MongoDB for betting operations.
        """
        try:
            client = MongoClient(settings.MONGODB_HOST, settings.MONGODB_PORT)
            db = client[settings.MONGODB_DB_NAME]
            users_collection = db[settings.MONGODB_COLLECTIONS['users']]
            
            # Update or create the user document in MongoDB
            users_collection.update_one(
                {'username': self.username},
                {
                    '$set': {
                        'username': self.username,
                        'email': self.email,
                        'virtual_coins': float(self.virtual_coins),
                        'last_coins_assignment': self.last_coins_assignment,
                        'first_name': self.first_name,
                        'last_name': self.last_name,
                        'is_active': self.is_active,
                        'last_updated': timezone.now()
                    }
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"MongoDB sync error: {e}")
            return False
