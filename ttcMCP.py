from typing import Any
import json
import logging
import httpx
import os
from dotenv import load_dotenv
from fastmcp import FastMCP

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


@mcp.tool()
async def arrival_times(stop_id: str, ignore_scheduled: bool = False) -> str:
    """Get real-time arrival times for a bus stop in Tbilisi.

    Args:
        stop_id: four-digit ID of a bus stop
        ignore_scheduled: whether to ignore scheduled arrival times (default: False)
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
async def get_all_stops() -> str:
    """Get all bus stops in the system.
    
    Returns:
        JSON string with all bus stops in Tbilisi.
    """
    url = f"{API_BASE}/stops"
    data = await make_request(url)
    
    if not data:
        return "Unable to fetch stops."
    
    return json.dumps(data, indent=2)


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
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    
    # For testing examples:
    #import asyncio
    #asyncio.run(arrival_times("4115"))
    #asyncio.run(get_all_stops())
    #asyncio.run(get_stop("4115"))
    #asyncio.run(get_all_routes())
    #asyncio.run(plan_trip(41.7151, 44.8271, 41.7255, 44.7943))
    #asyncio.run(get_bus_polyline("101"))
    #asyncio.run(get_bus_locations("101"))
    #asyncio.run(get_stop_routes("4115"))
    #asyncio.run(get_bus_stops("101"))
