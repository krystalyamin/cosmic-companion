"""
weather_service.py

Weather API integration for the AI Stargazing Planner.

Uses:
    Open-Meteo Forecast API
    https://open-meteo.com/

Functions:
    get_weather_forecast()
    calculate_stargazing_conditions()
    test_weather_api_connection()
"""

import os
from datetime import datetime, timezone
import requests


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

# ==========================================================
# Location Processing
# ==========================================================

def geocode_location(location: str):
    """
    Convert a user-provided location into coordinates.

    Parameters:
        location (str):
            User-entered location.

    Returns:
        tuple:
            (latitude, longitude)

    Raises:
        ValueError:
            If the location cannot be found.
    """

    response = requests.get(
        OPEN_METEO_GEOCODING_URL,
        params={
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    results = data.get("results")

    if not results:
        raise ValueError(f"Unable to locate '{location}'")

    return (
        results[0]["latitude"],
        results[0]["longitude"]
    )


def get_elevation(latitude: float, longitude: float) -> float:
    """
    Retrieve elevation (meters above sea level) for a location.

    Parameters:
        latitude (float)
        longitude (float)

    Returns:
        float:
            Elevation in meters.

    Raises:
        ValueError:
            If the API returns invalid data.
        requests.RequestException:
            If the API request fails.
    """

    try:
        response = requests.get(
            OPEN_METEO_ELEVATION_URL,
            params={
                "latitude": latitude,
                "longitude": longitude
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        elevations = data.get("elevation")

        if elevations is None:
            raise ValueError(
                "Elevation data not returned by API."
            )

        # Open-Meteo returns a list even for a single coordinate
        if isinstance(elevations, list):
            if not elevations:
                raise ValueError(
                    "Empty elevation data returned by API."
                )
            return float(elevations[0])

        return float(elevations)

    except requests.Timeout:
        raise ValueError(
            "Request to Open-Meteo elevation service timed out."
        )

    except requests.RequestException as e:
        raise ValueError(
            f"Failed to retrieve elevation data: {e}"
        )

    except (TypeError, ValueError) as e:
        raise ValueError(
            f"Invalid elevation response: {e}"
        )


# ==========================================================
# General Weather Data
# ==========================================================

def safe_hourly_value(hourly, field, index, default=None):
    try:
        value = hourly[field][index]
        return default if value is None else value
    except (KeyError, IndexError, TypeError):
        return default
    

def get_weather_forecast(
    latitude: float,
    longitude: float,
    date: str,
    time: str
) -> dict:
    """
    Retrieve weather conditions for a specific location and datetime.

    Parameters:
        latitude (float)
        longitude (float)
        date (str): YYYY-MM-DD
        time (str): HH:MM

    Returns:
        dict:
            Structured weather information.
    """

    try:
        target_datetime = datetime.fromisoformat(
            f"{date}T{time}"
        )

        now = datetime.now()

        if target_datetime <= now:
            api_url = OPEN_METEO_ARCHIVE_URL
        else:
            api_url = OPEN_METEO_FORECAST_URL

        response = requests.get(
            api_url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": date,
                "end_date": date,
                "hourly": (
                    "temperature_2m,"
                    "cloud_cover,"
                    "visibility,"
                    "relative_humidity_2m,"
                    "precipitation_probability,"
                    "wind_speed_10m"
                ),
                "timezone": "auto"
            },
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        hourly = data.get("hourly")

        if not hourly:
            raise ValueError(
                "Hourly weather data not available."
            )

        target_hour = f"{date}T{time}"

        hourly_times = hourly.get("time", [])

        if target_hour not in hourly_times:
            raise ValueError(
                f"No weather data available for {target_hour}"
            )

        index = hourly_times.index(target_hour)

        weather_data = {
            "datetime": target_hour,
            "temperature_c": safe_hourly_value(hourly, "temperature_2m", index),
            "cloud_cover_percent": safe_hourly_value(hourly, "cloud_cover", index, 100),
            "visibility_m": safe_hourly_value(hourly, "visibility", index, 0),
            "humidity_percent": safe_hourly_value(hourly, "relative_humidity_2m", index),
            "precipitation_probability_percent": safe_hourly_value(
                hourly,
                "precipitation_probability",
                index,
                100
            ),
            "wind_speed_kmh": safe_hourly_value(
                hourly,
                "wind_speed_10m",
                index,
                100
            )
        }

        weather_data["stargazing_conditions"] = (
            calculate_stargazing_conditions(
                weather_data
            )
        )

        return weather_data

    except requests.Timeout:
        return {
            "error": "Weather request timed out."
        }

    except requests.RequestException as e:
        return {
            "error": f"Weather API request failed: {e}"
        }

    except Exception as e:
        return {
            "error": str(e)
        }


def calculate_stargazing_conditions(
    weather_data: dict
) -> dict:
    """
    Convert raw weather data into stargazing-friendly metrics.
    """

    try:

        def safe_number(
            value,
            default
        ):
            if value is None:
                return default

            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        cloud_cover = safe_number(
            weather_data.get("cloud_cover_percent"),
            100
        )

        visibility = safe_number(
            weather_data.get("visibility_m"),
            0
        )

        precipitation = safe_number(
            weather_data.get(
                "precipitation_probability_percent"
            ),
            100
        )

        wind_speed = safe_number(
            weather_data.get("wind_speed_kmh"),
            100
        )

        score = 100

        # Cloud cover (largest factor)
        score -= cloud_cover * 0.50

        # Rain risk
        score -= precipitation * 0.25

        # Visibility
        if visibility < 2000:
            score -= 25
        elif visibility < 5000:
            score -= 15
        elif visibility < 10000:
            score -= 5

        # Wind
        if wind_speed > 40:
            score -= 15
        elif wind_speed > 25:
            score -= 8

        score = max(
            0,
            min(
                100,
                round(score)
            )
        )

        if score >= 80:
            quality = "Excellent"
        elif score >= 60:
            quality = "Good"
        elif score >= 40:
            quality = "Fair"
        elif score >= 20:
            quality = "Poor"
        else:
            quality = "Very Poor"

        if cloud_cover <= 20:
            cloud_assessment = "Mostly Clear"
        elif cloud_cover <= 50:
            cloud_assessment = "Partly Cloudy"
        elif cloud_cover <= 80:
            cloud_assessment = "Mostly Cloudy"
        else:
            cloud_assessment = "Overcast"

        return {
            "stargazing_score": score,
            "observing_quality": quality,
            "cloud_assessment": cloud_assessment,
            "recommended": score >= 60
        }

    except Exception as e:
        return {
            "error": str(e)
        }


def test_weather_api_connection() -> bool:
    """
    Verify weather API connectivity.

    Parameters:
        None

    Returns:
        bool:
            API status.
    """

    try:
        response = requests.get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": 1.3521,
                "longitude": 103.8198,
                "hourly": "cloud_cover"
            },
            timeout=5
        )

        return response.status_code == 200

    except Exception:
        return False


def get_weather_data(session_data: dict):
    return {
        "cloud_cover":"covered",
        "visibility":"visible",
        "cloud_cover":"covered"
    }

if __name__ == "__main__":

    weather = get_weather_forecast(
        latitude=1.3521,
        longitude=103.8198,
        date="2026-08-15",
        time="21:00"
    )

    print(weather)

