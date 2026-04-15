"""
configs/constants.py
---------------------
Define global constants for the whole project
"""

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Tolerance for matching lines of the same street
# 1e-4 degrees ~ 10 meters
TOLERANCE   = 5e-5