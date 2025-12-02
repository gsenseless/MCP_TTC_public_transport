# TTC MCP Server

MCP server for real-time Tbilisi public transit information via the TTC API.

## Features

- 🚌 Real-time bus arrival times
- 🗺️ Trip planning between coordinates
- 🛑 Stop and route information
- 📋 Complete system data (all stops and routes)

## Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Configure API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add: TTC_API_KEY=your-api-key-here
   ```

3. **Run the server:**
   ```bash
   python ttcMCP.py
   ```
   Server runs on `http://0.0.0.0:8000`

## Getting an API Key

I don't know the oficial way to obtain the TTC API key, but you can simply google it: "tbilisi ttc api key site:github.com":).

**Note:** 
1) I was unable to find API documentation, that's why some params are hardcoded.
2) The TTC API only serves requests originating from Georgia due to a geo firewall.

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `arrival_times` | Get real-time arrivals for a stop | `stop_id` |
| `search_stop_by_name` | Search for stops by name | `name` |
| `search_stops_nearby` | Find 5 closest stops to coordinates | `lat`, `lon` |
| `get_stop` | Get stop details | `stop_id` |
| `get_all_routes` | List all routes | - |
| `plan_trip` | Plan a trip between coordinates | `from_lat`, `from_lng`, `to_lat`, `to_lng` |
| `get_stop_routes` | Get routes serving a stop | `stop_id` |

