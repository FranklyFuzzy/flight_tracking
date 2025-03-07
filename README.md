# Aircraft Tracking System

A Python-based system for monitoring aircraft in your area with special focus on tracking non-US and military aircraft. This script uses data from a local PiAware ADS-B receiver combined with OpenSky Network data to identify and track aircraft of interest.

## Features

- **Dual Category Tracking**: Identifies both foreign and military aircraft
- **Visual Distinction**: Uses color-coded terminal output to distinguish between aircraft types
- **API Optimization**: Works within OpenSky Network API anonymous user limitations
- **Continuous Monitoring**: Runs as a background process to provide real-time alerts
- **Configurable Monitoring Area**: Adjustable geographic boundaries to optimize API usage

## Requirements

- Python 3.6+
- A running PiAware ADS-B receiver
- Internet connection for OpenSky Network API access
- Required Python packages: `requests`, `logging`

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/aircraft-tracking-system.git
   cd aircraft-tracking-system
   ```

2. Install required packages:
   ```
   pip install requests
   ```

3. Configure the script (see Configuration section below)

4. Run the script:
   ```
   python aircraft_tracker.py
   ```

## Configuration

Before running the script, you need to update several key parameters:

### 1. PiAware Connection

Update the `PIAWARE_URL` variable with your PiAware IP address:

```python
PIAWARE_URL = "http://<pi-ip>/skyaware/data/aircraft.json"
```

Replace `<pi-ip>` with your PiAware device's IP address (e.g., `192.168.1.10`).

### 2. Geographic Boundaries

Set your monitoring area by updating these coordinates:

```python
LAT_MIN = 40.0  # Southern boundary - adjust for your location
LAT_MAX = 45.0  # Northern boundary - adjust for your location
LON_MIN = -74.0  # Western boundary - adjust for your location
LON_MAX = -69.0  # Eastern boundary - adjust for your location
```

For optimal API usage, keep your area under 25 square degrees (approximately 500km × 500km).

### 3. Military Aircraft Identification

You can customize the military aircraft detection by updating the following lists:

```python
MILITARY_CALLSIGN_PATTERNS = [
    # Add additional patterns relevant to your region
]

MILITARY_ICAO_PREFIXES = [
    # Add additional prefixes relevant to your region
]
```

### 4. API Usage Settings

You can adjust the API usage parameters if needed:

```python
OPENSKY_RATE_LIMIT = 10  # Minimum time between API calls (seconds)
DAILY_CREDIT_LIMIT = 400  # Total API credits per day
CREDIT_USAGE = 1  # Credits used per call (depends on area size)
```

## Determining Your Location Parameters

To find appropriate coordinates for your monitoring area:

1. **Using Google Maps**:
   - Right-click on points that define your area boundaries
   - Select "What's here?" to see the coordinates

2. **Using a Bounding Box Tool**:
   - Visit https://boundingbox.klokantech.com/
   - Draw your area and copy the coordinates

3. **Calculate Area Size**:
   - Ensure your area is within one of these credit usage categories:
     - Under 25 square degrees: 1 credit per call
     - 25-100 square degrees: 2 credits per call
     - 100-400 square degrees: 3 credits per call
     - Over 400 square degrees: 4 credits per call

## Understanding the Output

The script provides color-coded terminal output:

- 🌐 **Yellow text**: Foreign aircraft
- 🪖 **Red text**: Military aircraft
- **Cyan text**: API usage information

Each aircraft report includes:
- ICAO hex code
- Callsign (if available)
- Status (Military or Foreign with country)
- Altitude, speed, and heading
- GPS coordinates

## Running as a Background Service

To run this script continuously as a service:

### Using systemd (Linux):

1. Create a service file:
   ```
   sudo nano /etc/systemd/system/aircraft-tracker.service
   ```

2. Add the following content:
   ```
   [Unit]
   Description=Aircraft Tracking System
   After=network.target

   [Service]
   User=pi
   WorkingDirectory=/path/to/script/directory
   ExecStart=/usr/bin/python3 /path/to/script/aircraft_tracker.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```
   sudo systemctl enable aircraft-tracker.service
   sudo systemctl start aircraft-tracker.service
   ```

4. Check status:
   ```
   sudo systemctl status aircraft-tracker.service
   ```

## Troubleshooting

- **No aircraft detected**: Ensure your PiAware is functioning correctly and the IP address is correct
- **API rate limit issues**: Reduce your monitoring area size or increase the polling interval
- **Missing military aircraft**: Add additional callsign patterns or ICAO prefixes to the detection lists

## API Limitations

Anonymous users of the OpenSky Network API have the following limitations:

- Data is limited to the most recent state vectors (no historical data)
- Time resolution is limited to 10 seconds
- 400 API credits per day

## Acknowledgments

- PiAware for providing local ADS-B data
- OpenSky Network for aircraft registration data
- Contributors to the ADS-B community
