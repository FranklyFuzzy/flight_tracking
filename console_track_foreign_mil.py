import requests
import json
import time 
import logging
import re
import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional, Any, Set

# Configuration
PIAWARE_URL = "http://<pi-ip>/skyaware/data/aircraft.json"

# OpenSky API with bounding box (customize for your location)
# Default is a ~25 square degree area (saves maximum credits)
# Update these coordinates to match your area of interest
LAT_MIN = 40.0  # Southern boundary - adjust for your location
LAT_MAX = 45.0  # Northern boundary - adjust for your location
LON_MIN = -74.0  # Western boundary - adjust for your location
LON_MAX = -69.0  # Eastern boundary - adjust for your location
OPENSKY_URL = f"https://opensky-network.org/api/states/all?lamin={LAT_MIN}&lamax={LAT_MAX}&lomin={LON_MIN}&lomax={LON_MAX}"

# API limitations settings
OPENSKY_RATE_LIMIT = 10  # OpenSky's minimum rate limit of 10 seconds
DAILY_CREDIT_LIMIT = 400  # Anonymous users get 400 credits per day
CREDIT_USAGE = 1  # Assuming we're using the smallest bounding box (1 credit per call)
MAX_CALLS_PER_DAY = DAILY_CREDIT_LIMIT // CREDIT_USAGE
CALLS_SPACING = 24 * 60 * 60 / MAX_CALLS_PER_DAY  # Space out calls evenly

# General settings
TIMEOUT = 10
POLLING_INTERVAL = max(30, OPENSKY_RATE_LIMIT)  # At least 10 seconds between OpenSky calls
OPENSKY_CACHE_DURATION = 300  # Cache OpenSky data for 5 minutes to reduce API calls

# Military identifiers
MILITARY_CALLSIGN_PATTERNS = [
    r'^RCH\d',    # Air Mobility Command (Reach)
    r'^DOOM\d',   # Various combat aircraft
    r'^RAGE\d',   # Combat aircraft
    r'^CYLON\d',  # Military flights
    r'^KING\d',   # Aerial refueling tankers
    r'^NAVY\w',   # Navy flights
    r'^AF\d',     # Air Force
    r'^USAF\d',   # US Air Force 
    r'^MARINE',   # Marine Corps
    r'^ZEUS\d',   # Military operations
    r'^THUG\d',   # Military operations
    r'^NINJA\d',  # Military operations
    r'^TREK\d',   # Transport flights
    r'^SNTRY',    # AWACS
    r'^ETHIC',    # Military flights
    r'^SLAM\d',   # Military operations
    r'^DERBY',    # Military operations
    r'^CAESAR',   # Military operations
    r'^UPSET',    # Military operations
    r'^WOLF\d',   # Combat aircraft
    r'^BISON\d',  # Military transport
    r'^CHAMP\d',  # Military operations
    r'^THUG\d',   # Military operations
    r'^WEASEL',   # Electronic warfare aircraft
    r'^HKR\d',    # Hawker (often military/governmental)
    r'^EAGLE\d',  # Military operations
    r'^FALCON',   # Combat aircraft
    r'^VIPER',    # Combat aircraft
    r'^COBRA',    # Attack helicopters or other aircraft
]

# Military ICAO hex ranges (examples)
MILITARY_ICAO_PREFIXES = [
    'ADF',  # US Air Force
    'ADC',  # US Army 
    'AE',   # US Naval and Marine Corps
    '3E',   # US Coast Guard
]

# Set up logging with colors for easier identification
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'WARNING': '\033[93m',  # Yellow
        'INFO': '\033[92m',     # Green
        'DEBUG': '\033[94m',    # Blue
        'CRITICAL': '\033[91m', # Red
        'ERROR': '\033[91m',    # Red
        'ENDC': '\033[0m',      # Reset color
    }

    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['ENDC']}"
        if "FOREIGN AIRCRAFT" in record.getMessage():
            record.msg = f"\033[93m{record.msg}\033[0m"  # Yellow for foreign
        elif "MILITARY AIRCRAFT" in record.getMessage():
            record.msg = f"\033[91m{record.msg}\033[0m"  # Red for military
        elif "API USAGE" in record.getMessage():
            record.msg = f"\033[96m{record.msg}\033[0m"  # Cyan for API tracking
        return super().format(record)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class APIRateLimiter:
    """Track and manage API usage to stay within limits"""
    def __init__(self, daily_limit, min_interval):
        self.daily_limit = daily_limit
        self.min_interval = min_interval
        self.call_count = 0
        self.last_call_time = 0
        self.reset_time = time.time() + 24*60*60  # Next reset in 24 hours
        
    def can_make_call(self):
        """Check if we can make an API call"""
        current_time = time.time()
        
        # Reset counter if a new day has started
        if current_time > self.reset_time:
            logger.info("API USAGE: Daily limit reset")
            self.call_count = 0
            self.reset_time = current_time + 24*60*60
        
        # Check rate limit
        if current_time - self.last_call_time < self.min_interval:
            return False
            
        # Check daily limit
        if self.call_count >= self.daily_limit:
            return False
            
        return True
        
    def record_call(self):
        """Record that a call was made"""
        self.call_count += 1
        self.last_call_time = time.time()
        remaining = self.daily_limit - self.call_count
        
        # Calculate when credits will reset
        reset_in_hours = (self.reset_time - time.time()) / 3600
        
        logger.info(f"API USAGE: Call made ({self.call_count}/{self.daily_limit}) - {remaining} credits remaining. Reset in {reset_in_hours:.1f} hours")

def fetch_data(url: str, timeout: int = TIMEOUT) -> Dict:
    """Generic function to fetch data from a URL."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return {}

def fetch_piaware_data() -> List[Dict]:
    """Fetch aircraft data from PiAware."""
    data = fetch_data(PIAWARE_URL)
    return data.get("aircraft", [])

def fetch_opensky_data(rate_limiter: APIRateLimiter) -> Optional[Dict[str, List]]:
    """Fetch aircraft registration data from OpenSky Network and index by ICAO."""
    # Check if we can make a call within rate limits
    if not rate_limiter.can_make_call():
        logger.warning("OpenSky API call skipped due to rate limiting")
        return None
        
    data = fetch_data(OPENSKY_URL)
    states = data.get("states", [])
    
    if not states and "states" in data:
        # API call succeeded but returned empty results
        rate_limiter.record_call()
    elif states:
        # API call succeeded with results
        rate_limiter.record_call()
        
        # Create a dictionary for O(1) lookups by ICAO hex
        indexed_data = {}
        for entry in states:
            if entry and entry[0]:  # Ensure the entry and ICAO hex exist
                indexed_data[entry[0].lower()] = entry
        
        logger.info(f"Refreshed OpenSky data, got {len(indexed_data)} aircraft records")
        return indexed_data
    
    return None

def is_military_aircraft(aircraft: Dict) -> bool:
    """Determine if an aircraft is likely military based on callsign or ICAO hex."""
    # Check callsign patterns
    callsign = aircraft.get("flight", "").strip()
    if callsign:
        for pattern in MILITARY_CALLSIGN_PATTERNS:
            if re.match(pattern, callsign):
                return True
    
    # Check ICAO hex prefixes
    icao_hex = aircraft.get("hex", "").upper()
    for prefix in MILITARY_ICAO_PREFIXES:
        if icao_hex.startswith(prefix):
            return True
            
    # Additional known military identifiers
    if aircraft.get("mil", False):  # Some feeds directly mark military aircraft
        return True
        
    # Check for common military squawk codes
    squawk = aircraft.get("squawk")
    if squawk in ["7777", "7400", "7401", "7402", "7500", "7600", "7700"]:
        return True
        
    return False

def check_aircraft_status(aircraft: Dict, opensky_data: Dict) -> Optional[Tuple[str, str, str]]:
    """
    Check if an aircraft is foreign or military.
    Returns (icao_hex, status_reason, category) where category is 'FOREIGN' or 'MILITARY'
    """
    icao_hex = aircraft.get("hex", "").lower()
    if not icao_hex:
        return None
        
    # First check if it's military (we can detect this even without OpenSky data)
    if is_military_aircraft(aircraft):
        return (icao_hex, "Military Aircraft", "MILITARY")
    
    # Then check if it's foreign (requires OpenSky data)
    if opensky_data and icao_hex in opensky_data:
        entry = opensky_data[icao_hex]
        country = entry[2].strip() if len(entry) > 2 and entry[2] else "Unknown"
        if country != "United States" and country != "Unknown":
            return (icao_hex, f"Foreign ({country})", "FOREIGN")
        
    return None

def format_aircraft_info(aircraft: Dict, status: str, category: str) -> str:
    """Format aircraft information for display."""
    icao_hex = aircraft.get("hex", "").upper()
    callsign = aircraft.get("flight", "").strip()
    altitude = aircraft.get("alt_baro", "unknown")
    speed = aircraft.get("gs", "unknown")
    heading = aircraft.get("track", "unknown")
    lat = aircraft.get("lat", "unknown")
    lon = aircraft.get("lon", "unknown")
    
    symbol = "🌐" if category == "FOREIGN" else "🪖"
    category_text = "FOREIGN AIRCRAFT" if category == "FOREIGN" else "MILITARY AIRCRAFT"
    
    return (f"{symbol} {category_text}: ICAO: {icao_hex} | "
           f"Callsign: {callsign} | "
           f"Status: {status} | "
           f"Alt: {altitude} ft | "
           f"Speed: {speed} kts | "
           f"Heading: {heading}° | "
           f"Position: {lat}, {lon}")

def main():
    logger.info(f"Starting aircraft monitoring with API optimization...")
    logger.info(f"Monitoring area: Lat {LAT_MIN}-{LAT_MAX}, Lon {LON_MIN}-{LON_MAX}")
    logger.info(f"API configuration: {MAX_CALLS_PER_DAY} calls per day, minimum {OPENSKY_RATE_LIMIT}s between calls")
    
    # Initialize API rate limiter
    rate_limiter = APIRateLimiter(MAX_CALLS_PER_DAY, OPENSKY_RATE_LIMIT)
    
    # Track already reported aircraft to avoid duplicates
    reported_aircraft: Dict[str, str] = {}  # Maps aircraft_id to category
    opensky_data = {}
    last_opensky_refresh = 0
    
    try:
        while True:
            current_time = time.time()
            
            # Try to refresh OpenSky data periodically (if rate limits allow)
            if (current_time - last_opensky_refresh > OPENSKY_CACHE_DURATION):
                new_data = fetch_opensky_data(rate_limiter)
                if new_data:  # Only update if we got new data
                    opensky_data = new_data
                    last_opensky_refresh = current_time

            # Fetch PiAware data on every cycle (this doesn't use the API)
            aircraft_list = fetch_piaware_data()
            logger.info(f"Checking {len(aircraft_list)} aircraft from PiAware")
            
            current_aircraft_ids = set()
            
            # Process all aircraft, even if OpenSky data is missing
            for aircraft in aircraft_list:
                result = check_aircraft_status(aircraft, opensky_data)
                if result:
                    icao_hex, status_reason, category = result
                    aircraft_id = f"{icao_hex}-{category}"
                    current_aircraft_ids.add(aircraft_id)
                    
                    # Only report if we haven't seen this aircraft recently or category changed
                    if aircraft_id not in reported_aircraft or reported_aircraft[aircraft_id] != category:
                        formatted_info = format_aircraft_info(aircraft, status_reason, category)
                        logger.info(formatted_info)
                        reported_aircraft[aircraft_id] = category
            
            # Remove aircraft that are no longer visible
            reported_aircraft = {k: v for k, v in reported_aircraft.items() if k in current_aircraft_ids}
            
            # Summary statistics
            military_count = sum(1 for cat in reported_aircraft.values() if cat == "MILITARY")
            foreign_count = sum(1 for cat in reported_aircraft.values() if cat == "FOREIGN")
            
            logger.info(f"Status update: Tracking {military_count} military and {foreign_count} foreign aircraft")
            
            # Calculate appropriate sleep time based on OpenSky data age
            time_since_refresh = time.time() - last_opensky_refresh
            if time_since_refresh >= OPENSKY_CACHE_DURATION:
                # We need fresh OpenSky data - use rate limit interval
                sleep_time = POLLING_INTERVAL
            else:
                # We still have valid OpenSky data - poll more frequently
                sleep_time = POLLING_INTERVAL
                
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        raise

if __name__ == "__main__":
    main()
