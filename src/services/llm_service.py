"""
Groq integration layer for the AI Stargazing Planner.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_NAME = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """
You are an astronomy and stargazing guide.

Your responsibilities:

- Help beginner and intermediate stargazers.
- Use astronomy and weather data provided in the prompt as the source of truth.
- Never invent visibility information.
- Recommend observing targets appropriate for the user's equipment.
- Explain reasoning clearly.
- Keep explanations beginner friendly.
- Mention weather limitations when relevant.

Always structure responses using:

# Recommended Objects

# Why They Are Visible

# Equipment Advice

# Viewing Tips
"""


def build_llm_context(
    session_data: dict,
    astronomy_data: dict,
    weather_data: dict,
    chat_history: list
) -> str:
    """
    Build the final context string sent to Groq.
    """

    history_text = "\n".join(
        [
            f"{msg['role'].upper()}: {msg['message']}"
            for msg in chat_history[-10:]
        ]
    )

    context = f"""
OBSERVATION SESSION

Location:
{session_data.get("location")}

Date:
{session_data.get("date")}

Time:
{session_data.get("time")}

Equipment:
{session_data.get("equipment")}

Experience:
{session_data.get("experience")}

Goals:
{session_data.get("goal")}

Target:
{session_data.get("target")}

ASTRONOMY DATA

{astronomy_data}

WEATHER DATA

{weather_data}

PREVIOUS CONVERSATION

{history_text}
"""

    return context


def generate_stargazing_response(
    user_message: str,
    session_data: dict,
    astronomy_data: dict,
    weather_data: dict,
    chat_history: list
) -> str:
    """
    Generate a Groq response.
    """

    try:

        context = build_llm_context(
            session_data=session_data,
            astronomy_data=astronomy_data,
            weather_data=weather_data,
            chat_history=chat_history
        )

        client = Groq(
            api_key=GROQ_API_KEY
        )

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content":
                        f"{context}\n\n"
                        f"USER QUESTION:\n{user_message}"
                }
            ]
        )

        return (
            completion
            .choices[0]
            .message
            .content
        )

    except Exception as exc:

        return (
            "Unable to generate a stargazing recommendation "
            f"at this time.\n\nError: {exc}"
        )


def test_groq_connection() -> bool:
    """
    Verify Groq connectivity.
    """

    try:

        client = Groq(
            api_key=GROQ_API_KEY
        )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": "Hello"
                }
            ],
            max_tokens=5
        )

        return bool(response.choices)

    except Exception:

        return False