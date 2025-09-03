"""
Configuration file for TAO Stats Visualizer
API key is loaded from environment variables or .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# TAO Stats API Configuration
TAO_STATS_API_KEY = os.getenv('TAO_STATS_API_KEY')

# API Settings
API_BASE_URL = "https://api.taostats.io/api/stats/history/v1"
REQUEST_DELAY = 3  # seconds between requests
MAX_RETRIES = 3
RATE_LIMIT_BACKOFF = 5  # base seconds for rate limit backoff
