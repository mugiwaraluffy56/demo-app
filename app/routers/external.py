"""
Routes that call free public APIs — no keys needed.
Great for generating varied, real traffic to observe in api-monitor.

APIs used:
  - open-meteo.com     — weather forecasts
  - restcountries.com  — country info
  - coingecko.com      — crypto prices (public tier)
  - official-joke-api  — random jokes
  - openlibrary.org    — book search
  - dog.ceo            — random dog images
"""

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/external", tags=["External APIs"])

_client = httpx.AsyncClient(timeout=10)


# ── Weather ───────────────────────────────────────────────────────────────────

@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int = Query(3, ge=1, le=7, description="Forecast days"),
):
    """Current weather + forecast via open-meteo.com (no API key)."""
    resp = await _client.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weathercode,windspeed_10m,relativehumidity_2m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "forecast_days": days,
            "timezone": "auto",
        },
    )
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Weather API error")
    return resp.json()


@router.get("/weather/city")
async def get_weather_by_city(city: str = Query(..., description="City name")):
    """Geocode city then fetch weather."""
    geo = await _client.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1},
    )
    if not geo.is_success or not geo.json().get("results"):
        raise HTTPException(404, f"City {city!r} not found")
    result = geo.json()["results"][0]
    lat, lon = result["latitude"], result["longitude"]

    weather = await _client.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weathercode,windspeed_10m,relativehumidity_2m",
            "timezone": "auto",
        },
    )
    return {
        "city": result["name"],
        "country": result.get("country"),
        "latitude": lat,
        "longitude": lon,
        "weather": weather.json().get("current"),
    }


# ── Countries ─────────────────────────────────────────────────────────────────

@router.get("/countries")
async def list_countries(region: str | None = Query(None, description="Filter by region")):
    """All countries, optionally filtered by region (restcountries.com)."""
    url = "https://restcountries.com/v3.1/all" if not region else f"https://restcountries.com/v3.1/region/{region}"
    resp = await _client.get(url, params={"fields": "name,capital,population,region,flags,currencies"})
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Countries API error")
    data = resp.json()
    return [
        {
            "name": c.get("name", {}).get("common"),
            "capital": c.get("capital", [None])[0],
            "population": c.get("population"),
            "region": c.get("region"),
            "flag": c.get("flags", {}).get("png"),
            "currencies": list(c.get("currencies", {}).keys()),
        }
        for c in data
    ]


@router.get("/countries/{name}")
async def get_country(name: str):
    """Look up a country by name."""
    resp = await _client.get(f"https://restcountries.com/v3.1/name/{name}")
    if resp.status_code == 404:
        raise HTTPException(404, f"Country {name!r} not found")
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Countries API error")
    c = resp.json()[0]
    return {
        "name": c.get("name", {}).get("common"),
        "official_name": c.get("name", {}).get("official"),
        "capital": c.get("capital", [None])[0],
        "population": c.get("population"),
        "area_km2": c.get("area"),
        "region": c.get("region"),
        "subregion": c.get("subregion"),
        "languages": list(c.get("languages", {}).values()),
        "currencies": list(c.get("currencies", {}).keys()),
        "flag": c.get("flags", {}).get("png"),
        "timezones": c.get("timezones"),
    }


# ── Crypto ────────────────────────────────────────────────────────────────────

@router.get("/crypto/prices")
async def crypto_prices(
    coins: str = Query("bitcoin,ethereum,solana", description="Comma-separated coin IDs"),
    currency: str = Query("usd", description="Target currency"),
):
    """Live crypto prices from CoinGecko public API."""
    resp = await _client.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": coins,
            "vs_currencies": currency,
            "include_24hr_change": "true",
            "include_market_cap": "true",
        },
    )
    if not resp.is_success:
        raise HTTPException(resp.status_code, "CoinGecko API error")
    return resp.json()


@router.get("/crypto/trending")
async def crypto_trending():
    """Top-7 trending coins on CoinGecko."""
    resp = await _client.get("https://api.coingecko.com/api/v3/search/trending")
    if not resp.is_success:
        raise HTTPException(resp.status_code, "CoinGecko API error")
    coins = resp.json().get("coins", [])
    return [
        {
            "name": c["item"]["name"],
            "symbol": c["item"]["symbol"],
            "market_cap_rank": c["item"].get("market_cap_rank"),
            "thumb": c["item"].get("thumb"),
        }
        for c in coins
    ]


# ── Jokes ─────────────────────────────────────────────────────────────────────

@router.get("/jokes/random")
async def random_joke():
    """Random programming joke."""
    resp = await _client.get("https://official-joke-api.appspot.com/jokes/programming/random")
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Jokes API error")
    jokes = resp.json()
    return jokes[0] if isinstance(jokes, list) else jokes


@router.get("/jokes/ten")
async def ten_jokes():
    """Ten random jokes."""
    resp = await _client.get("https://official-joke-api.appspot.com/jokes/ten")
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Jokes API error")
    return resp.json()


# ── Books ─────────────────────────────────────────────────────────────────────

@router.get("/books/search")
async def search_books(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50),
):
    """Search books via OpenLibrary."""
    resp = await _client.get(
        "https://openlibrary.org/search.json",
        params={"q": q, "limit": limit, "fields": "key,title,author_name,first_publish_year,edition_count"},
    )
    if not resp.is_success:
        raise HTTPException(resp.status_code, "OpenLibrary API error")
    docs = resp.json().get("docs", [])
    return [
        {
            "title": d.get("title"),
            "authors": d.get("author_name", []),
            "first_published": d.get("first_publish_year"),
            "editions": d.get("edition_count"),
            "key": d.get("key"),
        }
        for d in docs
    ]


# ── Dogs ──────────────────────────────────────────────────────────────────────

@router.get("/dogs/random")
async def random_dog():
    """Random dog image from dog.ceo."""
    resp = await _client.get("https://dog.ceo/api/breeds/image/random")
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Dog API error")
    return resp.json()


@router.get("/dogs/breeds")
async def list_dog_breeds():
    """All dog breeds."""
    resp = await _client.get("https://dog.ceo/api/breeds/list/all")
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Dog API error")
    breeds = resp.json().get("message", {})
    return {"total": len(breeds), "breeds": list(breeds.keys())}


@router.get("/dogs/breed/{breed}")
async def dog_by_breed(breed: str, count: int = Query(3, ge=1, le=10)):
    """Random images for a specific breed."""
    resp = await _client.get(f"https://dog.ceo/api/breed/{breed}/images/random/{count}")
    if resp.status_code == 404:
        raise HTTPException(404, f"Breed {breed!r} not found")
    if not resp.is_success:
        raise HTTPException(resp.status_code, "Dog API error")
    return resp.json()
