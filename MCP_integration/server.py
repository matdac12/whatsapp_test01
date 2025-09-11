# server.py
import asyncio
from typing import Optional, Tuple

import httpx
from mcp.server.fastmcp import FastMCP


OPENMETEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPENMETEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"

mcp = FastMCP("openmeteo-remote-mcp")


async def _geocode_city(client: httpx.AsyncClient, city: str) -> Tuple[float, float, str]:
    r = await client.get(OPENMETEO_GEOCODE, params={"name": city, "count": 1})
    r.raise_for_status()
    data = r.json()
    results = (data or {}).get("results") or []
    if not results:
        raise ValueError(f"City not found: {city}")
    top = results[0]
    lat, lon = float(top["latitude"]), float(top["longitude"])
    label = f'{top.get("name","")}, {top.get("country","")}'
    return lat, lon, label


async def _fetch_temperature(client: httpx.AsyncClient, lat: float, lon: float) -> Tuple[float, str]:
    r = await client.get(OPENMETEO_FORECAST, params={
        "latitude": lat,
        "longitude": lon,
        "current_weather": True
    })
    r.raise_for_status()
    data = r.json()
    cw = (data or {}).get("current_weather") or {}
    units = (data or {}).get("current_weather_units", {})
    temp = cw.get("temperature")
    unit = units.get("temperature", "°C")
    if temp is None:
        # Fallback for older/newer schemas (rare)
        raise ValueError("Temperature not available from Open-Meteo response.")
    return float(temp), unit


@mcp.tool()
async def get_temperature(
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> dict:
    """
    Return current temperature. Provide either a city name (preferred) or latitude+longitude.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        if city:
            lat, lon, label = await _geocode_city(client, city)
        else:
            if latitude is None or longitude is None:
                raise ValueError("Provide either 'city' or both 'latitude' and 'longitude'.")
            lat, lon = float(latitude), float(longitude)
            label = f"{lat:.4f},{lon:.4f}"

        temp, unit = await _fetch_temperature(client, lat, lon)
        return {
            "location": label,
            "latitude": lat,
            "longitude": lon,
            "temperature": temp,
            "unit": unit,
        }


if __name__ == "__main__":
    mcp.run()

