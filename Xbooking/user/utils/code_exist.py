from user.models import VerificationCode
from datetime import timedelta
from django.utils import timezone

CODE_EXPIRY_MINUTES = 10
def check_existing_code(user):
        """
        Check if user has an existing valid verification code.
        
        Args:
            user: User instance
            
        Returns:
            dict: Contains 'exists' boolean and 'remaining_time' if exists
        """
        expiry_time = timezone.now() - timedelta(minutes=CODE_EXPIRY_MINUTES)
        
        existing_code = VerificationCode.objects.filter(
            user=user,
            is_used=False,
            created_at__gte=expiry_time
        ).first()
        
        if existing_code:
            time_elapsed = timezone.now() - existing_code.created_at
            remaining_time = timedelta(minutes=CODE_EXPIRY_MINUTES) - time_elapsed
            remaining_minutes = int(remaining_time.total_seconds() // 60)
            remaining_seconds = int(remaining_time.total_seconds() % 60)
            
            return {
                'exists': True,
                'remaining_time': {
                    'minutes': remaining_minutes,
                    'seconds': remaining_seconds,
                    'total_seconds': int(remaining_time.total_seconds())
                },
                'code_record': existing_code
            }
        
        return {'exists': False}