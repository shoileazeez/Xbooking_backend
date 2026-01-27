"""
Business Email Validator
Validates that email is from a business domain (not free email providers)
"""
from django.core.exceptions import ValidationError


# List of free email providers to reject for business accounts
FREE_EMAIL_PROVIDERS = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'aol.com', 'icloud.com', 'mail.com', 'protonmail.com',
    'zoho.com', 'yandex.com', 'gmx.com', 'inbox.com',
    'live.com', 'msn.com', 'yahoo.co.uk', 'googlemail.com',
    'me.com', 'mac.com', 'aim.com', 'fastmail.com',
]


def validate_business_email(email):
    """
    Validate that email is from a business domain.
    
    Args:
        email: Email address to validate
        
    Raises:
        ValidationError: If email is from a free provider
        
    Returns:
        tuple: (is_business, domain)
    """
    if not email:
        raise ValidationError("Email is required")
    
    domain = email.split('@')[-1].lower()
    
    if domain in FREE_EMAIL_PROVIDERS:
        raise ValidationError(
            f"Please use a business email address. {domain} is not allowed for workspace admin accounts."
        )
    
    return True, domain


def is_business_email(email):
    """
    Check if email is a business email without raising exception.
    
    Args:
        email: Email address to check
        
    Returns:
        bool: True if business email, False otherwise
    """
    if not email:
        return False
    
    domain = email.split('@')[-1].lower()
    return domain not in FREE_EMAIL_PROVIDERS


def get_email_domain(email):
    """
    Extract domain from email address.
    
    Args:
        email: Email address
        
    Returns:
        str: Email domain or None
    """
    if not email or '@' not in email:
        return None
    
    return email.split('@')[-1].lower()
