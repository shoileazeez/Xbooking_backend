# UUID JWT Authentication Fix - Documentation

## Problem

The Xbooking API uses UUID primary keys for the User model, but Django REST Framework's JWT authentication was failing with:

```
ValueError: Field 'id' expected a number but got 'fb0cfd1c-b9c5-4e45-94c2-76e6ce4858e5'.
```

This error occurred because:
1. The User model has `id = models.UUIDField(primary_key=True, ...)`
2. JWT tokens store `user_id` as a string representation of the UUID
3. The default `JWTAuthentication` class tried to look up users by the string UUID directly, not converting it to a UUID object first
4. Django's database query expected a UUID object, not a string, causing type mismatch

## Solution

Created a custom `UUIDJWTAuthentication` class that:
1. Extracts the `user_id` claim from the JWT token (which is a string like `"28366bae-13c7-402a-8099-1b233ad0bd1d"`)
2. Converts the string to a proper `uuid.UUID` object
3. Uses the UUID object to query the User model
4. Returns the authenticated user

## Files Changed

### 1. `user/authentication.py` (NEW)

Custom JWT authentication class that handles UUID conversion:

```python
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
import uuid

class UUIDJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that converts UUID strings to UUID objects
    for user lookup with UUID primary keys
    """
    
    def get_user(self, validated_token):
        # Extract user_id from token
        user_id = validated_token['user_id']
        
        # Convert string UUID to UUID object
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        
        # Query user with UUID object
        user = User.objects.get(id=user_id)
        return user
```

### 2. `Xbooking/settings.py` (UPDATED)

Updated the REST Framework authentication configuration to use the custom class:

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'user.authentication.UUIDJWTAuthentication',  # Changed from default
    ],
    # ... other settings
}
```

## Testing

The fix has been verified to work correctly:

1. **Token Generation**: JWT tokens are properly generated with UUID user_id
   - Token claims include: `"user_id": "28366bae-13c7-402a-8099-1b233ad0bd1d"`

2. **Authentication**: Custom authentication properly converts and looks up users
   - UUID string is converted to UUID object
   - User is found in database
   - Authenticated user is returned

3. **Manual Test**: Created `test_jwt_auth.py` to verify the flow

## How It Works

### JWT Token Structure

```json
{
  "token_type": "access",
  "exp": 1761038536,
  "iat": 1761036736,
  "jti": "3916dc6000254678...",
  "user_id": "28366bae-13c7-402a-8099-1b233ad0bd1d"  // String UUID
}
```

### Authentication Flow

```
1. Request arrives with Bearer token
   ↓
2. DRF calls JWTAuthentication.authenticate()
   ↓
3. Token is validated and decoded (user_id is a string)
   ↓
4. Our custom get_user() method is called with validated_token
   ↓
5. Convert user_id string to UUID object: uuid.UUID("28366bae-...")
   ↓
6. Query User: User.objects.get(id=<UUID object>)
   ↓
7. User found and returned
   ↓
8. Request proceeds with authenticated user
```

## Backwards Compatibility

The implementation includes fallback logic for non-UUID IDs:

```python
if isinstance(user_id, str):
    try:
        user_id = uuid.UUID(user_id)
    except (ValueError, TypeError):
        # Use as-is if not a valid UUID (e.g., integer ID as string)
        pass
```

This ensures compatibility if you later migrate to or from UUID primary keys.

## Performance Considerations

- **Minimal overhead**: Single UUID conversion operation per request
- **No caching issues**: Uses Django's ORM normally
- **Database agnostic**: Works with any database backend (SQLite, PostgreSQL, etc.)

## Troubleshooting

### Issue: "User not found" error

**Cause**: Custom authentication is working but user doesn't exist in database

**Solution**: 
- Verify user exists: `User.objects.filter(email='user@example.com')`
- Check UUID format in database: `User.objects.first().id`

### Issue: "Token missing claim: user_id"

**Cause**: Token was generated with different claims configuration

**Solution**:
- Regenerate tokens after deployment
- Check JWT settings in `settings.py`

### Issue: Still getting "expected a number" error

**Cause**: Old JWT authentication is still being used

**Solution**:
- Verify `settings.py` has `'user.authentication.UUIDJWTAuthentication'`
- Restart Django server
- Clear browser cookies/tokens

## Related Files

- `user/models.py` - User model with UUID primary key
- `Xbooking/settings.py` - JWT and authentication configuration
- `test_jwt_auth.py` - Test script to verify authentication

## Additional Notes

- This fix is specific to UUID primary keys
- If using integer primary keys, the default authentication works fine
- The conversion happens only at authentication time, not on every request
- Logging is enabled for debugging authentication issues

## Future Improvements

1. Add token refresh token handling with UUID conversion
2. Add unit tests for authentication
3. Consider custom JWT token serializer to always convert UUIDs
4. Add metrics/monitoring for authentication performance
