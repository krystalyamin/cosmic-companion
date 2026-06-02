"""
Coordinates all application services.
"""

from services.astronomy_service import (
    get_astronomy_data
)

from services.weather_service import (
    get_weather_forecast
)

from services.memory_service import (
    save_chat_message,
    get_chat_history,
    search_relevant_memories,
    save_session_data
)

from services.llm_service import (
    generate_stargazing_response
)


def process_user_request(
    session_id: str,
    session_data: dict,
    user_message: str
) -> str:
    """
    Main application workflow.
    """

    try:

        # ----------------------------------
        # Persist latest session settings
        # ----------------------------------

        save_session_data(
            session_id,
            session_data
        )

        # ----------------------------------
        # Astronomy data
        # ----------------------------------

        astronomy_data = get_astronomy_data(
            session_data
        )

        # ----------------------------------
        # Weather data
        # ----------------------------------

        latitude = astronomy_data.get(
            "latitude"
        )

        longitude = astronomy_data.get(
            "longitude"
        )

        if latitude is not None and longitude is not None:

            weather_data = get_weather_forecast(
                latitude=latitude,
                longitude=longitude,
                date=session_data["date"],
                time=session_data["time"]
            )

        else:

            weather_data = {
                "error":
                    "Unable to retrieve coordinates "
                    "for weather lookup."
            }

        # ----------------------------------
        # Retrieve memory
        # ----------------------------------

        chat_history = get_chat_history(
            session_id=session_id,
            limit=20
        )

        relevant_memories = (
            search_relevant_memories(
                session_id=session_id,
                query=user_message,
                top_k=5
            )
        )

        combined_history = (
            chat_history +
            relevant_memories
        )

        # ----------------------------------
        # Save user message
        # ----------------------------------

        save_chat_message(
            session_id=session_id,
            role="user",
            message=user_message
        )

        # ----------------------------------
        # Generate AI response
        # ----------------------------------

        response = (
            generate_stargazing_response(
                user_message=user_message,
                session_data=session_data,
                astronomy_data=astronomy_data,
                weather_data=weather_data,
                chat_history=combined_history
            )
        )

        # ----------------------------------
        # Save assistant message
        # ----------------------------------

        save_chat_message(
            session_id=session_id,
            role="assistant",
            message=response
        )

        return response

    except Exception as exc:

        error_message = (
            "Unable to process your stargazing request.\n\n"
            f"Error: {exc}"
        )

        try:

            save_chat_message(
                session_id=session_id,
                role="assistant",
                message=error_message
            )

        except Exception:
            pass

        return error_message