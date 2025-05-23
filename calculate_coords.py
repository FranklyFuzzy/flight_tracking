#!/usr/bin/env python3
import math

def calculate_bounding_box(center_lat, center_lon, distance_km):
    """
    Calculate a bounding box given a center point and distance in kilometers.
    
    Args:
        center_lat (float): Center latitude in decimal degrees
        center_lon (float): Center longitude in decimal degrees
        distance_km (float): Distance from center to edge in kilometers
    
    Returns:
        tuple: (lat_min, lat_max, lon_min, lon_max) defining the bounding box
    """
    # Earth's radius in kilometers
    EARTH_RADIUS = 6371.0
    
    # Convert distance from kilometers to degrees
    # (approximate, will vary slightly with latitude)
    distance_deg_lat = (distance_km / EARTH_RADIUS) * (180.0 / math.pi)
    distance_deg_lon = distance_deg_lat / math.cos(math.radians(center_lat))
    
    # Calculate the bounding box
    lat_min = center_lat - distance_deg_lat
    lat_max = center_lat + distance_deg_lat
    lon_min = center_lon - distance_deg_lon
    lon_max = center_lon + distance_deg_lon
    
    # Ensure coordinates are within valid range
    lat_min = max(lat_min, -90.0)
    lat_max = min(lat_max, 90.0)
    lon_min = max(lon_min, -180.0)
    lon_max = min(lon_max, 180.0)
    
    return (lat_min, lat_max, lon_min, lon_max)

def calculate_area_from_distance(center_lat, distance_km):
    """
    Calculate the resulting bounding box area in square degrees for a given distance.
    
    Args:
        center_lat (float): Center latitude in decimal degrees
        distance_km (float): Distance from center to edge in kilometers
    
    Returns:
        float: Area in square degrees
    """
    # Earth's radius in kilometers
    EARTH_RADIUS = 6371.0
    
    # Convert distance from kilometers to degrees
    distance_deg_lat = (distance_km / EARTH_RADIUS) * (180.0 / math.pi)
    distance_deg_lon = distance_deg_lat / math.cos(math.radians(center_lat))
    
    # Calculate the resulting area in square degrees
    # Area = width × height, and both dimensions are doubled because distance is from center to edge
    area = (2 * distance_deg_lat) * (2 * distance_deg_lon)
    
    return area

def find_max_distance_for_area(center_lat, target_area, precision=0.01):
    """
    Find the maximum distance that produces a bounding box with area <= target_area.
    Uses binary search for accuracy.
    
    Args:
        center_lat (float): Center latitude in decimal degrees
        target_area (float): Target area in square degrees
        precision (float): Precision of the result in kilometers
        
    Returns:
        float: Maximum distance in kilometers
    """
    min_dist = 0
    max_dist = 1000  # Start with a reasonable upper bound
    
    # Binary search
    while max_dist - min_dist > precision:
        current_dist = (min_dist + max_dist) / 2
        area = calculate_area_from_distance(center_lat, current_dist)
        
        if area < target_area:
            min_dist = current_dist
        else:
            max_dist = current_dist
    
    return min_dist  # Return the safe lower bound

def main():
    print("============================================")
    print("Aircraft Tracking Area Calculator")
    print("============================================")
    print("This utility helps you calculate monitoring area coordinates")
    print("for aircraft tracking based on your location and desired range.")
    print()
    
    try:
        # Get user input for center coordinates
        center_lat = float(input("Enter your latitude (decimal degrees): "))
        center_lon = float(input("Enter your longitude (decimal degrees): "))
        
        # Validate input coordinates
        if not (-90 <= center_lat <= 90):
            print("Error: Latitude must be between -90 and 90 degrees.")
            return
        if not (-180 <= center_lon <= 180):
            print("Error: Longitude must be between -180 and 180 degrees.")
            return
        
        # Get monitoring distance
        distance_km = float(input("Enter monitoring radius in kilometers: "))
        if distance_km <= 0:
            print("Error: Distance must be greater than 0 kilometers.")
            return
        
        # Calculate the bounding box
        lat_min, lat_max, lon_min, lon_max = calculate_bounding_box(center_lat, center_lon, distance_km)
        
        # Calculate the area in square degrees
        area_deg_squared = (lat_max - lat_min) * (lon_max - lon_min)
        
        # Calculate maximum distances for different credit thresholds
        # Using binary search for accurate results
        max_dist_1_credit = find_max_distance_for_area(center_lat, 25)
        max_dist_2_credit = find_max_distance_for_area(center_lat, 100)
        max_dist_3_credit = find_max_distance_for_area(center_lat, 400)
        
        # Apply safety margin of 1 km
        safety_margin = 1.0
        max_dist_1_credit_safe = max(max_dist_1_credit - safety_margin, 1)
        max_dist_2_credit_safe = max(max_dist_2_credit - safety_margin, 1)
        max_dist_3_credit_safe = max(max_dist_3_credit - safety_margin, 1)
        
        # Display results
        print("\n============================================")
        print("RESULTS")
        print("============================================")
        print(f"Center coordinates: {center_lat:.6f}, {center_lon:.6f}")
        print(f"Monitoring radius: {distance_km:.2f} km")
        print("\nBounding Box Coordinates:")
        print(f"  LAT_MIN = {lat_min:.6f}  # Southern boundary")
        print(f"  LAT_MAX = {lat_max:.6f}  # Northern boundary")
        print(f"  LON_MIN = {lon_min:.6f}  # Western boundary")
        print(f"  LON_MAX = {lon_max:.6f}  # Eastern boundary")
        print("\nArea in square degrees: {:.2f}".format(area_deg_squared))
        
        # OpenSky API credit usage guidance
        print("\nOpenSky Network API Credit Usage:")
        if area_deg_squared < 25:
            print("  Area < 25 sq. deg: 1 credit per API call")
        elif area_deg_squared < 100:
            print("  Area 25-100 sq. deg: 2 credits per API call")
        elif area_deg_squared < 400:
            print("  Area 100-400 sq. deg: 3 credits per API call")
        else:
            print("  Area > 400 sq. deg: 4 credits per API call (Not recommended)")
            print("  Consider reducing your monitoring radius for optimal API usage.")
        
        # Show the actual calculated areas for verification
        area_1_credit = calculate_area_from_distance(center_lat, max_dist_1_credit)
        area_2_credit = calculate_area_from_distance(center_lat, max_dist_2_credit)
        area_3_credit = calculate_area_from_distance(center_lat, max_dist_3_credit)
        
        # Maximum distance recommendations
        print("\nMaximum Recommended Monitoring Distances:")
        print(f"  The maximum distance -1km to stay in the 1 credit threshold is {max_dist_1_credit_safe:.2f} km")
        print(f"  (At {max_dist_1_credit:.2f} km, area would be {area_1_credit:.2f} sq. deg)")
        print(f"  The maximum distance -1km to stay in the 2 credit threshold is {max_dist_2_credit_safe:.2f} km")
        print(f"  (At {max_dist_2_credit:.2f} km, area would be {area_2_credit:.2f} sq. deg)")
        print(f"  The maximum distance -1km to stay in the 3 credit threshold is {max_dist_3_credit_safe:.2f} km")
        print(f"  (At {max_dist_3_credit:.2f} km, area would be {area_3_credit:.2f} sq. deg)")
        
        print("\nNote: Maximum distances vary with latitude due to the Earth's shape.")
        print("Copy these values into your tracking script configuration.")

    except ValueError:
        print("Error: Please enter valid numeric values.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
