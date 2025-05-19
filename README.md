# Aircraft Tracking System

A Python-based system for tracking and visualizing aircraft using ADS-B data from a local PiAware receiver. This toolkit includes utilities for monitoring, visualizing, and specifically identifying foreign and military aircraft.

## Contents

This repository contains four main Python scripts for aircraft tracking and visualization:

1. **calculate_coords.py** - A utility to calculate monitoring area coordinates based on your location
2. **console_track_foreign_mil.py** - Specialized tracker for identifying foreign and military aircraft
3. **plot_adsb_ascii_hc.py** - Color-coded ASCII visualization of aircraft in your monitoring area
4. **plot_adsb_ascii_bw.py** - Black and white ASCII visualization with red antenna marker

## Setup Requirements

- Python 3.6+
- A running PiAware ADS-B receiver (or compatible dump1090-based ADS-B receiver)
- Internet connection for OpenSky Network API access (required for console_track_foreign_mil.py)
- Required Python packages: 
  ```
  pip install requests
  ```

## Getting Started

### 1. Calculate Your Monitoring Area

First, determine the coordinates for your monitoring area using the coordinate calculator:

```bash
python calculate_coords.py
```

Follow the prompts to enter your:
- Latitude and longitude (your location)
- Desired monitoring radius in kilometers

The script will output the required LAT_MIN, LAT_MAX, LON_MIN, LON_MAX coordinates for the other scripts.

Example output of python calculate_coords.py for New York City coordinates (40.7128, -74.0060) with a 50km monitoring radius
![Screenshot 2025-05-18 at 11 02 43 PM](https://github.com/user-attachments/assets/182e4ffb-96b2-4652-957c-9b5b7cd84d7f)


### 2. Configure Your Tracking Scripts

#### For the Plotting Visualizations

Edit either `plot_adsb_ascii_hc.py` (color version) or `plot_adsb_ascii_bw.py` (B&W version) and update:

```python
PIAWARE_IP = "<pi-ip>"  # Replace with your PiAware IP address
PIAWARE_PORT = 80
REFRESH_INTERVAL = 5  # Seconds between updates
TABLE_LIMIT = 10  # Number of aircraft to show in the table
PLOT_WIDTH = 80  # ASCII plot width
PLOT_HEIGHT = 20  # ASCII plot height

# Antenna coordinates - replace with your actual location
ANTENNA_LAT = 40.7128  # Replace with your latitude
ANTENNA_LON = -74.0060  # Replace with your longitude
```

#### For Foreign & Military Aircraft Tracking

Edit `console_track_foreign_mil.py` and update:

```python
# PiAware connection
PIAWARE_URL = "http://<pi-ip>/skyaware/data/aircraft.json"

# OpenSky API with bounding box (customize for your location)
LAT_MIN = 40.0  # Southern boundary - using outputs from calculate_coords.py
LAT_MAX = 45.0  # Northern boundary
LON_MIN = -74.0  # Western boundary
LON_MAX = -69.0  # Eastern boundary
```

You can also customize the military identification patterns in the script to better match aircraft in your region.

## Using the Tools

### Aircraft Visualization (ASCII Plotters)

Run either of the ASCII visualization tools:

```bash
# For color-coded visualization
python plot_adsb_ascii_hc.py

# For black and white visualization (with red antenna)
python plot_adsb_ascii_bw.py
```

These tools provide:
- A tabular view of the nearest aircraft
- An ASCII plot showing aircraft positions relative to your antenna
- Regular updates based on your configured refresh interval

**Color-coded Version Legend:**
- Green `#`: Aircraft with flight ID/callsign
- Blue `+`: High altitude aircraft (above 20,000 feet)
- Yellow `+`: Low altitude aircraft
- Red `O`: Antenna location

**B&W Version Legend:**
- `#`: Aircraft with flight ID/callsign
- `^`: High altitude aircraft (above 20,000 feet)
- `+`: Low altitude aircraft
- `X`: Unknown aircraft
- Red `O`: Antenna location

### Foreign & Military Aircraft Tracking

For specialized tracking of foreign and military aircraft:

```bash
python console_track_foreign_mil.py
```

This tool:
- Identifies military aircraft based on callsign patterns and ICAO hex codes
- Identifies foreign aircraft using OpenSky Network registration data
- Provides color-coded alerts when military or foreign aircraft are detected
- Manages API usage to stay within OpenSky Network's free tier limits

## Running as a Background Service

### Using systemd (Linux)

1. Create a service file for your preferred script:
   ```bash
   sudo nano /etc/systemd/system/aircraft-tracker.service
   ```

2. Add the following content (adjust paths as needed):
   ```
   [Unit]
   Description=Aircraft Tracking System
   After=network.target

   [Service]
   User=pi
   WorkingDirectory=/path/to/script/directory
   ExecStart=/usr/bin/python3 /path/to/script/console_track_foreign_mil.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl enable aircraft-tracker.service
   sudo systemctl start aircraft-tracker.service
   ```

## OpenSky Network API Limitations

Anonymous users of the OpenSky Network API have the following limitations:
- 400 API credits per day
- Minimum 10 seconds between API calls
- No historical data access
- Considerations for bounding box size (affects credit usage)

The `console_track_foreign_mil.py` script is optimized to work within these limits.

## Troubleshooting

- **No data received**: Ensure your PiAware is running and the IP address is correct
- **No aircraft displayed**: Verify your antenna coordinates and monitoring area size
- **OpenSky API errors**: Check your internet connection and reduce monitoring area size
- **Terminal display issues**: Adjust PLOT_WIDTH and PLOT_HEIGHT values to fit your terminal

## Acknowledgments

- PiAware/FlightAware for providing local ADS-B data
- OpenSky Network for aircraft registration data
- Contributors to the ADS-B community
