"""
Generate VAPID keys for web push notifications
"""
from py_vapid import Vapid
import base64
from cryptography.hazmat.primitives import serialization

vapid = Vapid()
vapid.generate_keys()

# Save keys to file
vapid.save_key('private_key.pem')
vapid.save_public_key('public_key.pem')

# Get the keys in base64url format (required for web push)
# Use proper cryptography library methods
public_key_bytes = vapid.public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)
public_key_b64 = base64.urlsafe_b64encode(public_key_bytes).decode('utf-8').rstrip('=')

private_key_bytes = vapid.private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
private_key_b64 = base64.urlsafe_b64encode(private_key_bytes).decode('utf-8').rstrip('=')

# Print keys in the format needed
print("\n" + "="*60)
print("VAPID Keys Generated Successfully!")
print("="*60)
print("\nAdd these to your backend .env file:\n")
print(f"VAPID_PUBLIC_KEY={public_key_b64}")
print(f"VAPID_PRIVATE_KEY={private_key_b64}")
print("VAPID_ADMIN_EMAIL=admin@xbooking.dev")
print("\n" + "="*60)
print("\nAdd to frontend .env.local file:\n")
print(f"NEXT_PUBLIC_VAPID_PUBLIC_KEY={public_key_b64}")
print("\n" + "="*60)
print("\nKeys also saved to:")
print("  - private_key.pem")
print("  - public_key.pem")
print("="*60 + "\n")
