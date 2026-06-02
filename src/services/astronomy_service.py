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
from weather_service import geocode_location, get_moon_data

ASTRONOMY_API_ID = os.getenv("ASTRONOMY_API_ID")
ASTRONOMY_API_SECRET = os.getenv("ASTRONOMY_API_SECRET")
ASTRONOMY_API_URL = "https://api.astronomyapi.com/api/"


# ==========================================================
# Planet Visibility
# ==========================================================

def get_visible_planets(
    latitude: float,
    longitude: float,
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

        url = (
            f"{ASTRONOMY_API_URL}v2/bodies/positions"
        )

        response = requests.get(
            url,
            auth=(ASTRONOMY_API_ID, ASTRONOMY_API_SECRET),
            params={
                "latitude": latitude,
                "longitude": longitude,
                "from_date": date,
                "to_date": date,
                "time": time
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

            altitude = (
                cell.get("position", {})
                    .get("horizontal", {})
                    .get("altitude", {})
                    .get("degrees")
            )

            azimuth = (
                cell.get("position", {})
                    .get("horizontal", {})
                    .get("azimuth", {})
                    .get("degrees")
            )

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

        visible_planets = get_visible_planets(
            latitude,
            longitude,
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