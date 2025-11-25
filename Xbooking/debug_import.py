import os
import django
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Xbooking.settings')
django.setup()

try:
    print("Importing Xbooking.urls...")
    import Xbooking.urls
    print("Successfully imported Xbooking.urls")

except Exception as e:
    import traceback
    traceback.print_exc()
