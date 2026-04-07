import azure.functions as func
import httpx
from mcp.server.fastmcp import FastMCP
from typing import Any

mcp = FastMCP("weather", stateless_http=True)  # stateless = no session, safe for serverless

NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"

async def make_nws_request(url: str) -> dict[str, Any] | None:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state. Args: state: Two-letter US state code (e.g. CA, NY)"""
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    if not data["features"]:
        return "No active alerts for this state."
    return "\n---\n".join([str(f["properties"].get("event","")) for f in data["features"]])

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast. Args: latitude: Latitude, longitude: Longitude"""
    points_data = await make_nws_request(f"{NWS_API_BASE}/points/{latitude},{longitude}")
    if not points_data:
        return "Unable to fetch forecast data."
    forecast_data = await make_nws_request(points_data["properties"]["forecast"])
    if not forecast_data:
        return "Unable to fetch detailed forecast."
    periods = forecast_data["properties"]["periods"]
    return "\n---\n".join([
        f"{p['name']}: {p['temperature']}°{p['temperatureUnit']}, {p['detailedForecast']}"
        for p in periods[:5]
    ])

# Wrap FastMCP as an Azure Function ASGI app
app = func.AsgiFunctionApp(
    app=mcp.streamable_http_app(),
    http_auth_level=func.AuthLevel.ANONYMOUS,
)