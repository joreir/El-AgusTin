from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import F
from decimal import Decimal
import logging

from users.models import User
from matches.models import Match

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Assigns coins to users for the current or specified jornada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--jornada',
            type=str,
            help='Jornada name to assign coins for (default: current active jornada)',
        )
        parser.add_argument(
            '--amount',
            type=float,
            default=100.0,
            help='Amount of coins to assign to each user (default: 100.0)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force assignment even if users already have coins for this jornada',
        )

    def handle(self, *args, **options):
        jornada_name = options.get('jornada')
        coins_amount = Decimal(str(options.get('amount')))
        force = options.get('force', False)
        
        # If no jornada specified, get the current active jornada
        if not jornada_name:
            active_jornadas = Match.get_active_jornadas()
            if not active_jornadas:
                self.stdout.write(self.style.ERROR('No active jornadas found'))
                return
            jornada_name = active_jornadas[0]
        
        # Get all matches for the jornada
        matches_collection = Match.get_collection()
        matches = list(matches_collection.find({'jornada': jornada_name, 'is_active': True}))
        
        if not matches:
            self.stdout.write(self.style.ERROR(f'No active matches found for jornada "{jornada_name}"'))
            return
        
        # Check if all matches have not started yet
        all_not_started = all(match.get('status') not in ['1H', '2H', 'HT', 'FT', 'AET', 'PEN'] for match in matches)
        
        if not all_not_started and not force:
            self.stdout.write(self.style.ERROR(
                f'Some matches for jornada "{jornada_name}" have already started. '
                f'Use --force to assign coins anyway.'
            ))
            return
        
        # Get all active users
        users = User.objects.filter(is_active=True)
        
        # Assign coins to each user
        assigned_count = 0
        
        for user in users:
            # Check if the user already has coins for this jornada
            if not force and user.last_coins_assignment:
                # Get the most recent match date for the jornada
                match_dates = [match.get('date') for match in matches if match.get('date')]
                if match_dates:
                    earliest_match_date = min(match_dates)
                    # If the user's last coins assignment is after the earliest match date,
                    # they already have coins for this jornada
                    if user.last_coins_assignment.isoformat() > earliest_match_date:
                        self.stdout.write(
                            f'User {user.username} already has coins for jornada "{jornada_name}". Skipping.'
                        )
                        continue
            
            # Assign coins to the user
            previous_coins = user.virtual_coins
            user.virtual_coins = F('virtual_coins') + coins_amount
            user.last_coins_assignment = timezone.now()
            user.save(update_fields=['virtual_coins', 'last_coins_assignment'])
            user.refresh_from_db()  # Refresh to get the updated value
            
            # Sync to MongoDB
            user.sync_to_mongodb()
            
            self.stdout.write(
                f'Assigned {coins_amount} coins to {user.username}. '
                f'Previous: {previous_coins}, New: {user.virtual_coins}'
            )
            assigned_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully assigned {coins_amount} coins to {assigned_count} users '
                f'for jornada "{jornada_name}"'
            )
        )
