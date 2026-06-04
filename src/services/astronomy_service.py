"""
astronomy_service.py

Astronomy data integration layer for the AI Stargazing Planner.

Responsibilities:
- Geocode user locations
- Retrieve planetary visibility data
- Retrieve moon information
- Generate recommended observing targets
- Consolidate astronomy information into a single response
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT_PATH = os.getenv("PROJECT_ROOT_PATH")

sys.path.insert(1, f"{PROJECT_ROOT_PATH}src/services/")
from weather_service import geocode_location, get_elevation

ASTRONOMY_API_ID = os.getenv("ASTRONOMY_API_ID")
ASTRONOMY_API_SECRET = os.getenv("ASTRONOMY_API_SECRET")
ASTRONOMY_API_URL = "https://api.astronomyapi.com/api/"

if not ASTRONOMY_API_ID or not ASTRONOMY_API_SECRET:
    raise EnvironmentError("Configuration Error: ASTRONOMY_API_KEY is missing!")

IPGEO_API_KEY = os.getenv("IPGEO_API_KEY")

if not IPGEO_API_KEY:
    raise EnvironmentError("Configuration Error: IPGEO_API_KEY is missing!")

# ==========================================================
# Planet Visibility
# ==========================================================

def get_visible_planets(
    latitude: float,
    longitude: float,
    elevation: float,
    date: str,
    time: str
) -> list:
    """
    Retrieve visible planets for the requested observation time.

    Parameters:
        latitude (float)
        longitude (float)
        date (str)
        time (str)

    Returns:
        list:
            Visible planets and visibility information.
    """

    planets = [
        "mercury",
        "venus",
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune"
    ]

    visible_planets = []

    try:

        formatted_time = (
            f"{time}:00"
            if len(time) == 5
            else time
        )

        url = (
            f"{ASTRONOMY_API_URL}v2/bodies/positions"
        )

        response = requests.get(
            url,
            auth=(ASTRONOMY_API_ID, ASTRONOMY_API_SECRET),
            params={
                "latitude": latitude,
                "longitude": longitude,
                "elevation": elevation, 
                "from_date": date,
                "to_date": date,
                "time": formatted_time
            },
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        body_data = (
            data.get("data", {})
                .get("table", {})
                .get("rows", [])
        )

        for row in body_data:

            body_name = row.get("entry", {}).get("name", "").lower()

            if body_name not in planets:
                continue

            cells = row.get("cells", [])

            if not cells:
                continue

            cell = cells[0]
            try:
                altitude = float(
                    cell.get("position", {})
                        .get("horizontal", {})
                        .get("altitude", {})
                        .get("degrees")
                )

                azimuth = float(
                    cell.get("position", {})
                        .get("horizontal", {})
                        .get("azimuth", {})
                        .get("degrees")
                )

            except (
                KeyError,
                TypeError,
                ValueError
            ):
                continue

            if altitude is not None and altitude > 0:

                visible_planets.append(
                    {
                        "name": row["entry"]["name"],
                        "altitude": altitude,
                        "azimuth": azimuth,
                        "visibility": (
                            "Excellent"
                            if altitude > 45
                            else "Good"
                            if altitude > 20
                            else "Low Horizon"
                        )
                    }
                )

    except Exception as exc:

        print(f"Planet API error: {exc}")

    return visible_planets


# ==========================================================
# Moon Data
# ==========================================================
def get_moon_data(
    latitude: float,
    longitude: float,
    date: str
) -> dict:
    """
    Retrieve moon phase and moon rise/set data.
    """

    try:

        response = requests.get(
            "https://api.ipgeolocation.io/astronomy",
            params={
                "apiKey": IPGEO_API_KEY,
                "lat": latitude,
                "long": longitude,
                "date": date
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return {
            "phase": data.get("moon_phase"),
            "illumination": abs(float(data.get(
                "moon_illumination_percentage"
            ))),
            "moonrise": data.get("moonrise"),
            "moonset": data.get("moonset")
        }

    except Exception as exc:

        print(f"Moon API error: {exc}")

        return {
            "phase": "Unknown",
            "illumination": None,
            "moonrise": None,
            "moonset": None
        }


# ==========================================================
# Target Recommendation Engine
# ==========================================================

def get_recommended_targets(
    session_data: dict,
    astronomy_data: dict
) -> list:
    """
    Generate a list of candidate viewing targets based on
    equipment and observing goals.
    """

    equipment = session_data.get("equipment", [])
    goals = session_data.get("goal", [])

    recommendations = []

    planets = astronomy_data.get("visible_planets", [])

    if "Visible Planets" in goals:

        for planet in planets:

            recommendations.append(
                {
                    "name": planet["name"],
                    "type": "Planet",
                    "reason":
                        f"{planet['name']} is currently above the horizon."
                }
            )

    if "Moon Viewing" in goals:

        recommendations.append(
            {
                "name": "Moon",
                "type": "Moon",
                "reason":
                    f"Current phase: {astronomy_data['moon']['phase']}"
            }
        )

    if "Deep Sky Objects" in goals:

        if "Telescope" in equipment:

            recommendations.extend([
                {
                    "name": "Orion Nebula",
                    "type": "Nebula",
                    "reason":
                        "One of the easiest nebulae for small telescopes."
                },
                {
                    "name": "Andromeda Galaxy",
                    "type": "Galaxy",
                    "reason":
                        "Bright and beginner friendly."
                }
            ])

        elif "Binoculars" in equipment:

            recommendations.extend([
                {
                    "name": "Pleiades",
                    "type": "Open Cluster",
                    "reason":
                        "Excellent binocular target."
                }
            ])

    if not recommendations:

        recommendations.extend([
            {
                "name": "Moon",
                "type": "Moon",
                "reason":
                    "Reliable observing target."
            }
        ])

    return recommendations


# ==========================================================
# Main Astronomy Query
# ==========================================================

def get_astronomy_data(
    session_data: dict
) -> dict:
    """
    Retrieve all astronomy information needed for planning.

    Parameters:
        session_data (dict):
            Observation session settings.

    Returns:
        dict:
            Consolidated astronomy data.
    """

    try:

        latitude, longitude = geocode_location(
            session_data["location"]
        )

        try:
            elevation = get_elevation(latitude, longitude)
        except:
            elevation = 0


        visible_planets = get_visible_planets(
            latitude,
            longitude,
            elevation,
            session_data["date"],
            session_data["time"]
        )

        moon_data = get_moon_data(
            latitude,
            longitude,
            session_data["date"]
        )

        astronomy_data = {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation,
            "visible_planets": visible_planets,
            "moon": moon_data
        }

        astronomy_data["recommended_targets"] = (
            get_recommended_targets(
                session_data,
                astronomy_data
            )
        )

        return astronomy_data

    except Exception as exc:

        print(f"Astronomy data error: {exc}")

        return {
            "error": str(exc),
            "visible_planets": [],
            "moon": {},
            "recommended_targets": []
        }
    
# ==========================================================
# API Health Checks
# ==========================================================

def test_astronomy_api_connection() -> bool:
    """
    Verify AstronomyAPI credentials and connectivity.
    """

    try:

        response = requests.get(
            f"{ASTRONOMY_API_URL}v2/bodies",
            auth=(ASTRONOMY_API_ID, ASTRONOMY_API_SECRET),
            timeout=10
        )

        return response.status_code == 200

    except Exception:
        return False


def test_moon_api_connection() -> bool:
    """
    Verify IPGeolocation astronomy API connectivity.
    """

    try:

        response = requests.get(
            "https://api.ipgeolocation.io/astronomy",
            params={
                "apiKey": IPGEO_API_KEY,
                "lat": 1.3521,
                "long": 103.8198
            },
            timeout=10
        )

        return response.status_code == 200

    except Exception:
        return False