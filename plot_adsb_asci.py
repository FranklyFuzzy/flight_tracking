#!/usr/bin/env python3
import requests
import json
import time
import math
import sys
import argparse
import os

def fetch_aircraft_data(ip_address, port=80):
    """Fetch aircraft data from the SkyAware JSON API"""
    url = f"http://{ip_address}:{port}/skyaware/data/aircraft.json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def simple_ascii_plot(aircraft_list, width=80, height=20, antenna_lat=None, antenna_lon=None):
    """
    Create a simple ASCII plot of aircraft positions
    
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
    
    # Include antenna position in bounds if provided
    if antenna_lat is not None and antenna_lon is not None:
        min_lat = min(min_lat, antenna_lat)
        max_lat = max(max_lat, antenna_lat)
        min_lon = min(min_lon, antenna_lon)
        max_lon = max(max_lon, antenna_lon)
    
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
    
    # Colors for terminal output
    RED = '\033[91m' if os.name != 'nt' else ''  # Red for antenna
    RESET = '\033[0m' if os.name != 'nt' else ''  # Reset color
    
    # Plot antenna position if provided
    if antenna_lat is not None and antenna_lon is not None:
        antenna_x = int((antenna_lon - min_lon) / (max_lon - min_lon) * (width - 1)) if max_lon > min_lon else width // 2
        antenna_y = int((max_lat - antenna_lat) / (max_lat - min_lat) * (height - 1)) if max_lat > min_lat else height // 2
        
        # Ensure coordinates are within grid bounds
        antenna_x = max(0, min(antenna_x, width - 1))
        antenna_y = max(0, min(antenna_y, height - 1))
        
        # Mark the antenna position with a red 'O'
        grid[antenna_y][antenna_x] = f"{RED}O{RESET}"
    
    # Plot each aircraft on the grid
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
        
        # Use different symbols based on aircraft data
        symbol = 'X'  # Default
        if flight_id:
            symbol = '#'  # Aircraft with flight number
            label = flight_id
        elif 'alt_baro' in aircraft:
            symbol = '+'  # Aircraft with altitude
            label = icao
        else:
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
    print(f"Legend: # = Flight with ID, + = Aircraft with altitude, X = Other, {RED}O{RESET} = Antenna location")

def print_aircraft_table(aircraft_list, limit=10):
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
        "ICAO", "Flight", "Squawk", "Altitude", "Speed", "Heading", "Dist"
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
        distance = f"{aircraft.get('distance', 'N/A')}" if 'distance' in aircraft else 'N/A'
        
        row = "| {:^8} | {:^8} | {:^7} | {:^8} | {:^6} | {:^7} | {:^6} |".format(
            icao, flight, squawk, alt, speed, heading, distance
        )
        print(row)
    
    print("-" * len(header))
    
    if len(sorted_aircraft) > limit:
        print(f"Displaying {limit} of {len(sorted_aircraft)} aircraft.")

def main():
    parser = argparse.ArgumentParser(description='Plot aircraft data from SkyAware/dump1090')
    parser.add_argument('ip', help='IP address or hostname of the SkyAware server')
    parser.add_argument('--port', type=int, default=80, help='Port (default: 80)')
    parser.add_argument('--refresh', type=int, default=5, help='Refresh interval in seconds (default: 5)')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of aircraft in table (default: 10)')
    parser.add_argument('--width', type=int, default=80, help='ASCII plot width (default: 80)')
    parser.add_argument('--height', type=int, default=20, help='ASCII plot height (default: 20)')
    parser.add_argument('--antenna-lat', type=float, help='Antenna latitude')
    parser.add_argument('--antenna-lon', type=float, help='Antenna longitude')
    
    args = parser.parse_args()
    
    print(f"Fetching aircraft data from: http://{args.ip}:{args.port}/skyaware/data/aircraft.json")
    print(f"Press Ctrl+C to exit.")
    
    # Initialize antenna coordinates
    antenna_lat = args.antenna_lat
    antenna_lon = args.antenna_lon
    
    try:
        while True:
            # Fetch and parse the data
            data = fetch_aircraft_data(args.ip, args.port)
            
            if data and 'aircraft' in data:
                aircraft_list = data['aircraft']
                
                # If antenna coordinates were not provided, try to get them from the data
                if antenna_lat is None and antenna_lon is None and 'lat' in data and 'lon' in data:
                    antenna_lat = data['lat']
                    antenna_lon = data['lon']
                    print(f"Using antenna coordinates from data: {antenna_lat}, {antenna_lon}")
                
                # Clear the screen (works on most terminals)
                print("\033c", end="")
                
                # Display timestamp
                if 'now' in data:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['now']))
                    print(f"Last update: {timestamp}")
                
                # Print aircraft table
                print_aircraft_table(aircraft_list, limit=args.limit)
                
                # Plot the data
                simple_ascii_plot(aircraft_list, width=args.width, height=args.height, 
                                 antenna_lat=antenna_lat, antenna_lon=antenna_lon)
            else:
                print("No valid data received.")
            
            # Wait before refreshing
            time.sleep(args.refresh)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
