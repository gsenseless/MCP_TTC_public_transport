from typing import Any
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


async def make_request(url: str) -> dict[str, Any] | None:
    """Make a request to the TTC API with proper error handling.
    
    Args:
        url: The full API endpoint URL to request
        
    Returns:
        JSON response data as a dictionary, or None if the request fails
    """
    headers = {"X-Api-Key": API_KEY}
    params = {"locale": DEFAULT_LOCALE}
    
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
async def get_routes(stop_id: str) -> str:
    """Get a real-time timetable of busses for a bus stop.

    Args:
        stop_id: four-digits id of a bus stop
    """
    url = f"{API_BASE}/stops/1:{stop_id}/arrival-times"
    data = await make_request(url)

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


if __name__ == "__main__":
    # Initialize and run the server
    # Expose via HTTP for remote access
    mcp.run(transport="http", host="0.0.0.0", port=8000)
    
    # For testing: fetch routes for stop 4115
    #import asyncio
    #asyncio.run(get_routes("4115"))
