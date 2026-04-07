import azure.functions as func
import httpx
import json
from typing import Any

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

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


@app.mcp_tool_trigger(
    arg_name="toolinput",
    tool_name="get_alerts",
    description="Get weather alerts for a US state. state: Two-letter US state code (e.g. CA, NY)",
)
async def get_alerts(toolinput: str) -> str:
    args = json.loads(toolinput)
    state = args["state"]
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)
    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."
    if not data["features"]:
        return "No active alerts for this state."
    return "\n---\n".join([str(f["properties"].get("event", "")) for f in data["features"]])


@app.mcp_tool_trigger(
    arg_name="toolinput",
    tool_name="get_forecast",
    description="Get weather forecast for a location. latitude: Latitude of the location, longitude: Longitude of the location",
)
async def get_forecast(toolinput: str) -> str:
    args = json.loads(toolinput)
    latitude = args["latitude"]
    longitude = args["longitude"]
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

