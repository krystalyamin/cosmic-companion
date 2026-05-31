
from astronomy import get_astronomy_data
from weather import get_weather_data

def generate_initial_briefing(session_data):
    """
    Dummy AI-generated session briefing.
    Replace with Groq API call.
    """

    astronomy = get_astronomy_data(session_data)
    weather = get_weather_data(session_data)

    response = f"""
        # Recommended Objects

        - {astronomy['recommended_objects'][0]}
        - {astronomy['recommended_objects'][1]}
        - {astronomy['recommended_objects'][2]}
        - {astronomy['recommended_objects'][3]}

        # Conditions

        - Cloud Cover: {weather['cloud_cover']}
        - Visibility: {weather['visibility']}
        - Moon Phase: {astronomy['moon_phase']}

        # Equipment Advice

        Using **{session_data['equipment']}**, these objects should be suitable for observation.

        # Viewing Tips

        - Allow your eyes to adjust to darkness.
        - Avoid bright phone screens.
        - Check local weather before travelling.

        Feel free to ask follow-up questions.
        """

    return response.strip()


def ask_stargazing_assistant(user_prompt, session_data, chat_history):
    """
    Dummy chatbot response.

    Replace with Groq implementation.
    """

    return f"""
        This is a placeholder response.

        Your question:
        > {user_prompt}

        Current observing session:

        - Location: {session_data['location']}
        - Date: {session_data['date']}
        - Time: {session_data['time']}
        - Equipment: {session_data['equipment']}

        This function will later call the Groq API and include:

        - Session context
        - Astronomy API data
        - Conversation history
        """
