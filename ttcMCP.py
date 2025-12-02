from typing import Any
import json
import logging
import httpx
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
import time

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("ttc")

# API Configuration
API_BASE = "https://transit.ttc.com.ge/pis-gateway/api/v2"
API_KEY = os.getenv("TTC_API_KEY")
if not API_KEY:
    raise ValueError("TTC_API_KEY environment variable is not set. Please check your .env file.")
DEFAULT_LOCALE = "en"
#DEFAULT_LOCALE = "ka"
REQUEST_TIMEOUT = 30.0


async def make_request(url: str, custom_params: dict[str, str] | None = None) -> dict[str, Any] | None:
    """Make a request to the TTC API with proper error handling.
    
    Args:
        url: The full API endpoint URL to request
        custom_params: Optional custom parameters to merge with default params
        
    Returns:
        JSON response data as a dictionary, or None if the request fails
    """
    headers = {"X-Api-Key": API_KEY}
    params = {"locale": DEFAULT_LOCALE}
    
    # Merge custom params if provided
    if custom_params:
        params.update(custom_params)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Response data: {data}")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching TTC data: {e}")
            return None
            return None


# Global cache for stops
STOPS_CACHE = None
STOPS_CACHE_TIMESTAMP = 0
CACHE_DURATION = 3600*24

async def get_cached_stops() -> list[dict[str, Any]] | None:
    """Get stops data from cache or fetch from API if expired."""
    global STOPS_CACHE, STOPS_CACHE_TIMESTAMP
    
    current_time = time.time()
    if STOPS_CACHE and (current_time - STOPS_CACHE_TIMESTAMP < CACHE_DURATION):
        logger.info("Using cached stops data")
        return STOPS_CACHE
        
    url = f"{API_BASE}/stops"
    data = await make_request(url)
    
    if data:
        STOPS_CACHE = data
        STOPS_CACHE_TIMESTAMP = current_time
        logger.info("Refreshed stops cache")
        
    return data

@mcp.tool()
async def arrival_times(stop_id: str, ignore_scheduled: bool = False) -> str:
    """Get real-time arrival times for a bus stop in Tbilisi.

    Args:
        stop_id: four-digit ID of a bus stop
    """
    url = f"{API_BASE}/stops/1:{stop_id}/arrival-times"
    custom_params = {"ignoreScheduledArrivalTimes": str(ignore_scheduled).lower()}
    data = await make_request(url, custom_params)

    if not data:
        return "Unable to fetch routes or no routes found."

    # Format the response data as readable sentences
    routes = []
    for route in data:
        short_name = route.get('shortName', '')
        vehicle_mode = route.get('vehicleMode', 'Vehicle')
        arrival_minutes = route.get('realtimeArrivalMinutes', 'Unknown')
        
        routes.append(f"{vehicle_mode} {short_name} arrives in {arrival_minutes} minutes.")
    
    logger.info("\n".join(routes))
    return "\n".join(routes)


@mcp.tool()
async def search_stop_by_name(name: str) -> str:
    """Search for bus stops by name in Tbilisi.
    
    Args:
        name: Partial or full name of the bus stop to search for (case-insensitive)
    
    Returns:
        JSON string with matching stops (id, code, name, lat, lon, vehicleMode)
    """

    data = await get_cached_stops()
    
    if not data:
        return "Unable to fetch stops."
    
    # Filter stops by name (case-insensitive partial match)
    search_term = name.lower()
    matching_stops = [
        stop for stop in data 
        if search_term in stop.get('name', '').lower()
    ]
    
    if not matching_stops:
        return f"No stops found matching '{name}'."
    
    return json.dumps(matching_stops, indent=2)


@mcp.tool()
async def search_stops_nearby(lat: float, lon: float) -> str:
    """Find the 5 closest bus stops to given coordinates in Tbilisi.
    
    Args:
        lat: Latitude of the location
        lon: Longitude of the location
    
    Returns:
        JSON string with the 5 nearest stops, sorted by distance
    """
    import math
    
    data = await get_cached_stops()
    
    if not data:
        return "Unable to fetch stops."
    
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula (in km)."""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    # Calculate distance for each stop and add it to the stop data
    stops_with_distance = []
    for stop in data:
        stop_lat = stop.get('lat')
        stop_lon = stop.get('lon')
        
        if stop_lat is not None and stop_lon is not None:
            distance = calculate_distance(lat, lon, stop_lat, stop_lon)
            stop_copy = stop.copy()
            stop_copy['distance_km'] = round(distance, 3)
            stops_with_distance.append(stop_copy)
    
    # Sort by distance and get the 5 closest
    stops_with_distance.sort(key=lambda x: x['distance_km'])
    nearest_stops = stops_with_distance[:5]
    
    if not nearest_stops:
        return "No stops found."
    
    return json.dumps(nearest_stops, indent=2)


@mcp.tool()
async def get_stop(stop_id: str) -> str:
    """Get details for a specific bus stop in Tbilisi.
    
    Args:
        stop_id: four-digit ID of a bus stop
    """
    url = f"{API_BASE}/stops/1:{stop_id}"
    data = await make_request(url)
    
    if not data:
        return f"Unable to fetch details for stop {stop_id}."
    
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_all_routes() -> str:
    """Get all bus routes in the system.
    
    Returns:
        JSON string with all bus routes in Tbilisi.
    """
    url = f"{API_BASE}/routes"
    custom_params = {"modes": "BUS"}
    data = await make_request(url, custom_params)
    
    if not data:
        return "No routes found."
    
    return json.dumps(data, indent=2)


@mcp.tool()
async def plan_trip(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
    """Plan a trip from one location to another using public transit in Tbilisi.
    
    Args:
        from_lat: Starting location latitude
        from_lng: Starting location longitude
        to_lat: Destination latitude
        to_lng: Destination longitude
    """
    url = f"{API_BASE}/plan"
    custom_params = {
        "fromPlace": f"{from_lat},{from_lng}",
        "toPlace": f"{to_lat},{to_lng}",
        "departMode": "leaveNow",
        "modes": "WALK,BUS",
        "optimize": "quick"
    }
    data = await make_request(url, custom_params)
    
    if not data:
        return "No trip plan found."
    
    return json.dumps(data, indent=2)


@mcp.tool()
async def get_stop_routes(stop_id: str) -> str:
    """Get all routes that serve a specific stop in Tbilisi.
    
    Args:
        stop_id: four-digit ID of a bus stop
    """
    url = f"{API_BASE}/stops/1:{stop_id}/routes"
    data = await make_request(url)
    
    if not data:
        return f"Unable to fetch routes for stop {stop_id}."
    
    return json.dumps(data, indent=2)


if __name__ == "__main__":
    # Initialize and run the server
    # Expose via HTTP for remote access
    #mcp.run(transport="http", host="0.0.0.0", port=8000)
    mcp.run(transport="sse", host="0.0.0.0", port=8000)
    
    # For testing examples:
    #import asyncio
    #asyncio.run(arrival_times("4115"))
    #asyncio.run(search_stop_by_name("Freedom"))
    #asyncio.run(search_stops_nearby(41.7151, 44.8271))
    #asyncio.run(get_stop("4115"))
    #asyncio.run(get_all_routes())
    #asyncio.run(plan_trip(41.7151, 44.8271, 41.7255, 44.7943))
    #asyncio.run(get_stop_routes("4115"))
