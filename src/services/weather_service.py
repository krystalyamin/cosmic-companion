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

from datetime import datetime
import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

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
        GEOCODING_URL,
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


# ==========================================================
# General Weather Data
# ==========================================================

def get_weather_forecast(
    latitude: float,
    longitude: float,
    date: str,
    time: str
) -> dict:
    """
    Retrieve weather conditions relevant to stargazing.

    Parameters:
        latitude (float)
        longitude (float)
        date (str) : YYYY-MM-DD
        time (str) : HH:MM

    Returns:
        dict:
            Structured weather forecast information.
    """

    try:
        response = requests.get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
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

        target_datetime = f"{date}T{time}"

        hourly_times = data["hourly"]["time"]

        if target_datetime not in hourly_times:
            raise ValueError(
                f"No forecast available for {target_datetime}"
            )

        index = hourly_times.index(target_datetime)

        weather_data = {
            "datetime": target_datetime,
            "temperature_c": (
                data["hourly"]["temperature_2m"][index]
            ),
            "cloud_cover_percent": (
                data["hourly"]["cloud_cover"][index]
            ),
            "visibility_m": (
                data["hourly"]["visibility"][index]
            ),
            "humidity_percent": (
                data["hourly"]["relative_humidity_2m"][index]
            ),
            "precipitation_probability_percent": (
                data["hourly"][
                    "precipitation_probability"
                ][index]
            ),
            "wind_speed_kmh": (
                data["hourly"]["wind_speed_10m"][index]
            )
        }

        weather_data["stargazing_conditions"] = (
            calculate_stargazing_conditions(
                weather_data
            )
        )

        return weather_data

    except Exception as e:
        return {
            "error": str(e)
        }


def calculate_stargazing_conditions(
    weather_data: dict
) -> dict:
    """
    Convert raw weather data into stargazing-friendly metrics.

    Parameters:
        weather_data (dict)

    Returns:
        dict:
            Cloud cover, visibility score,
            and observing quality assessment.
    """

    try:
        cloud_cover = weather_data.get(
            "cloud_cover_percent",
            100
        )

        visibility = weather_data.get(
            "visibility_m",
            0
        )

        precipitation = weather_data.get(
            "precipitation_probability_percent",
            100
        )

        wind_speed = weather_data.get(
            "wind_speed_kmh",
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

        score = max(0, min(100, round(score)))

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

