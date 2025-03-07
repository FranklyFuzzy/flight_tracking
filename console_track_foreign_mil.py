import requests
import json
import time 
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional, Any, Set

# Configuration
PIAWARE_URL = "http://<ip>/skyaware/data/aircraft.json"
OPENSKY_URL = "https://opensky-network.org/api/states/all"
TIMEOUT = 10
POLLING_INTERVAL = 30  # Seconds between each check
OPENSKY_REFRESH_INTERVAL = 300  # Refresh OpenSky data every 5 minutes (300 seconds)

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
        return super().format(record)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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

def fetch_opensky_data() -> Dict[str, List]:
    """Fetch aircraft registration data from OpenSky Network and index by ICAO."""
    data = fetch_data(OPENSKY_URL)
    states = data.get("states", [])
    
    # Create a dictionary for O(1) lookups by ICAO hex
    indexed_data = {}
    for entry in states:
        if entry and entry[0]:  # Ensure the entry and ICAO hex exist
            indexed_data[entry[0].lower()] = entry
    
    logger.info(f"Refreshed OpenSky data, got {len(indexed_data)} aircraft records")
    return indexed_data

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
        
    # Check for common military squawk codes (7777, 7400-7500, etc.)
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
        
    # First check if it's military
    if is_military_aircraft(aircraft):
        return (icao_hex, "Military Aircraft", "MILITARY")
    
    # Then check if it's foreign
    entry = opensky_data.get(icao_hex)
    if not entry:
        # Could be unregistered or military not in the database
        return None
    
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
    logger.info("Starting enhanced aircraft monitoring (tracking foreign and military aircraft)...")
    
    # Track already reported aircraft to avoid duplicates
    reported_aircraft: Dict[str, str] = {}  # Maps aircraft_id to category
    last_opensky_refresh = 0
    opensky_data = {}
    
    try:
        while True:
            current_time = time.time()
            
            # Refresh OpenSky data periodically
            if current_time - last_opensky_refresh > OPENSKY_REFRESH_INTERVAL or not opensky_data:
                opensky_data = fetch_opensky_data()
                last_opensky_refresh = current_time
                # Keep reported aircraft to maintain consistency
            
            # Fetch PiAware data on every cycle
            aircraft_list = fetch_piaware_data()
            logger.info(f"Checking {len(aircraft_list)} aircraft from PiAware")
            
            current_aircraft_ids = set()
            
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
            time.sleep(POLLING_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        raise

if __name__ == "__main__":
    main()