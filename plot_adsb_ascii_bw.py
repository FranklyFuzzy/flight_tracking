#!/usr/bin/env python3
import requests
import json
import time
import math
import sys
import os

# Configuration
# Replace these values with your own coordinates from calculate_coords.py
PIAWARE_IP = "<pi-ip>"  # Replace with your PiAware IP address
PIAWARE_PORT = 80
REFRESH_INTERVAL = 5  # Seconds between updates
TABLE_LIMIT = 10  # Number of aircraft to show in the table
PLOT_WIDTH = 80  # ASCII plot width
PLOT_HEIGHT = 20  # ASCII plot height

# Antenna coordinates - replace with your actual location
ANTENNA_LAT = 40.7128  # Replace with your latitude
ANTENNA_LON = -74.0060  # Replace with your longitude

def fetch_aircraft_data():
    """Fetch aircraft data from the SkyAware JSON API"""
    url = f"http://{PIAWARE_IP}:{PIAWARE_PORT}/skyaware/data/aircraft.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def simple_ascii_plot(aircraft_list, width=PLOT_WIDTH, height=PLOT_HEIGHT):
    """
    Create a simple ASCII plot of aircraft positions in black and white
    
    This function creates a simple 2D plot where:
    - Latitude is represented on the Y-axis
    - Longitude is represented on the X-axis
    - Aircraft flight IDs are displayed next to their symbols
    - Antenna location shown with a red circle
    """
    if not aircraft_list:
        print("No aircraft data to plot.")
        return
    
    # Filter aircraft with valid lat/lon
    valid_aircraft = [a for a in aircraft_list if 'lat' in a and 'lon' in a]
    
    if not valid_aircraft:
        print("No aircraft with position data to plot.")
        return
    
    # Find the bounds of the data
    min_lat = min(a['lat'] for a in valid_aircraft)
    max_lat = max(a['lat'] for a in valid_aircraft)
    min_lon = min(a['lon'] for a in valid_aircraft)
    max_lon = max(a['lon'] for a in valid_aircraft)
    
    # Include antenna position in bounds
    min_lat = min(min_lat, ANTENNA_LAT)
    max_lat = max(max_lat, ANTENNA_LAT)
    min_lon = min(min_lon, ANTENNA_LON)
    max_lon = max(max_lon, ANTENNA_LON)
    
    # Add a small margin
    lat_margin = (max_lat - min_lat) * 0.1 if max_lat != min_lat else 0.1
    lon_margin = (max_lon - min_lon) * 0.1 if max_lon != min_lon else 0.1
    min_lat -= lat_margin
    max_lat += lat_margin
    min_lon -= lon_margin
    max_lon += lon_margin
    
    # Create a grid and a separate grid for labels
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    label_positions = {}  # To store where to put labels
    
    # Colors for terminal output - only using red for antenna
    RED = '\033[91m' if os.name != 'nt' else ''  # Red for antenna
    RESET = '\033[0m' if os.name != 'nt' else ''  # Reset color
    
    # Plot antenna position
    antenna_x = int((ANTENNA_LON - min_lon) / (max_lon - min_lon) * (width - 1)) if max_lon > min_lon else width // 2
    antenna_y = int((max_lat - ANTENNA_LAT) / (max_lat - min_lat) * (height - 1)) if max_lat > min_lat else height // 2
    
    # Ensure coordinates are within grid bounds
    antenna_x = max(0, min(antenna_x, width - 1))
    antenna_y = max(0, min(antenna_y, height - 1))
    
    # Mark the antenna position with a red 'O'
    grid[antenna_y][antenna_x] = f"{RED}O{RESET}"
    
    # Plot each aircraft on the grid - use different symbols but no colors
    for aircraft in valid_aircraft:
        lat = aircraft['lat']
        lon = aircraft['lon']
        
        # Convert lat/lon to grid coordinates
        x = int((lon - min_lon) / (max_lon - min_lon) * (width - 1)) if max_lon > min_lon else width // 2
        y = int((max_lat - lat) / (max_lat - min_lat) * (height - 1)) if max_lat > min_lat else height // 2
        
        # Ensure coordinates are within grid bounds
        x = max(0, min(x, width - 1))
        y = max(0, min(y, height - 1))
        
        # Get aircraft identifier (flight ID or ICAO)
        flight_id = aircraft.get('flight', '').strip()
        icao = aircraft.get('hex', '').upper()
        altitude = aircraft.get('alt_baro', 0)
        
        # Use different symbols based on aircraft data, but no colors
        if flight_id:
            symbol = '#'  # Aircraft with flight number
            label = flight_id
        elif altitude and altitude > 20000:
            symbol = '^'  # High altitude aircraft
            label = icao
        elif altitude:
            symbol = '+'  # Low altitude aircraft
            label = icao
        else:
            symbol = 'X'  # Unknown aircraft
            label = icao
        
        # Add the symbol to the grid
        grid[y][x] = symbol
        
        # Store the label position (prioritize right side, but can go to left if near edge)
        label_x = x + 1 if x < width - 10 else x - len(label) - 1
        if 0 <= label_x < width - len(label):
            # Avoid overwriting existing labels
            if (y, label_x) not in label_positions:
                label_positions[(y, label_x)] = label
    
    # Print the grid with aircraft and labels
    print(f"\nAircraft Plot ({len(valid_aircraft)} aircraft found):")
    print(f"Latitude range: {min_lat:.4f} to {max_lat:.4f}")
    print(f"Longitude range: {min_lon:.4f} to {max_lon:.4f}")
    print("+" + "-" * width + "+")
    
    for y in range(height):
        line = "|"
        for x in range(width):
            line += grid[y][x]
        line += "|"
        print(line)
        
        # Print labels for this row
        labels_in_row = [(x, label) for (row, x), label in label_positions.items() if row == y]
        if labels_in_row:
            labels_line = " " * (width + 2)
            for x, label in sorted(labels_in_row):
                # Make sure we don't write outside our buffer
                if x + len(label) < width + 2:
                    labels_line = labels_line[:x+1] + label + labels_line[x+1+len(label):]
            print(labels_line)
    
    print("+" + "-" * width + "+")
    print(f"Legend: # = Flight with ID, ^ = High altitude, + = Low altitude, X = Other, {RED}O{RESET} = Antenna location")

def print_aircraft_table(aircraft_list, limit=TABLE_LIMIT):
    """Print a table of aircraft data"""
    if not aircraft_list:
        print("No aircraft data available.")
        return
    
    # Sort by distance if available, otherwise by signal strength
    if 'distance' in aircraft_list[0]:
        sorted_aircraft = sorted(aircraft_list, key=lambda a: a.get('distance', float('inf')))
    else:
        sorted_aircraft = sorted(aircraft_list, key=lambda a: a.get('rssi', float('-inf')), reverse=True)
    
    # Limit the number of aircraft to display
    display_list = sorted_aircraft[:limit]
    
    # Print header
    print("\nAircraft Data:")
    header = "| {:^8} | {:^8} | {:^7} | {:^8} | {:^6} | {:^7} | {:^6} |".format(
        "ICAO", "Flight", "Squawk", "Altitude", "Speed", "Heading", "Signal"
    )
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    
    # Print each aircraft
    for aircraft in display_list:
        icao = aircraft.get('hex', '').upper() or 'N/A'
        flight = aircraft.get('flight', '').strip() or 'N/A'
        squawk = aircraft.get('squawk', '') or 'N/A'
        alt = f"{aircraft.get('alt_baro', 'N/A')}" if 'alt_baro' in aircraft else 'N/A'
        speed = f"{aircraft.get('gs', 'N/A')}" if 'gs' in aircraft else 'N/A'
        heading = f"{aircraft.get('track', 'N/A')}" if 'track' in aircraft else 'N/A'
        signal = f"{aircraft.get('rssi', 'N/A')}" if 'rssi' in aircraft else 'N/A'
        
        row = "| {:^8} | {:^8} | {:^7} | {:^8} | {:^6} | {:^7} | {:^6} |".format(
            icao, flight, squawk, alt, speed, heading, signal
        )
        print(row)
    
    print("-" * len(header))
    
    if len(sorted_aircraft) > limit:
        print(f"Displaying {limit} of {len(sorted_aircraft)} aircraft.")

def main():
    print(f"ADS-B Aircraft Plotter (B&W Version)")
    print(f"===================================")
    print(f"Fetching aircraft data from: http://{PIAWARE_IP}:{PIAWARE_PORT}/skyaware/data/aircraft.json")
    print(f"Antenna coordinates: {ANTENNA_LAT}, {ANTENNA_LON}")
    print(f"Press Ctrl+C to exit.")
    
    try:
        while True:
            # Fetch and parse the data
            data = fetch_aircraft_data()
            
            if data and 'aircraft' in data:
                aircraft_list = data['aircraft']
                
                # Clear the screen (works on most terminals)
                print("\033c", end="")
                
                # Display timestamp
                if 'now' in data:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['now']))
                    print(f"Last update: {timestamp}")
                
                # Print aircraft table
                print_aircraft_table(aircraft_list)
                
                # Plot the data
                simple_ascii_plot(aircraft_list)
            else:
                print("No valid data received.")
            
            # Wait before refreshing
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
