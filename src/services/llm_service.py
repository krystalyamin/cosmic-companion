"""
Groq integration layer for the AI Stargazing Planner.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("Configuration Error: GROQ_API_KEY is missing!")

MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """
You are an astronomy and stargazing guide helping beginner and intermediate observers.

Rules:

- Use astronomy and weather data provided in the prompt as the source of truth.
- Never invent visibility information.
- Recommend observing targets appropriate for the user's equipment.
- Keep explanations beginner friendly.
- Mention weather limitations when relevant.
- Use previous conversation context to avoid repeating information already given.
- Assume the user remembers information already discussed unless they ask for a recap.
- Answer the user's most recent question directly before providing additional context.
- Only include sections that are relevant to the user's current question.
- Do not repeat full observing briefings unless explicitly requested.
- If the user asks a follow-up question, focus only on answering that question.
- Be concise when information has already been covered earlier in the session.
"""


def build_llm_context(
    session_data: dict,
    astronomy_data: dict,
    weather_data: dict,
    chat_history: list,
    user_message: str
) -> str:
    """
    Build the final context string sent to Groq.
    """

    history_text = "\n".join(
        [
            f"{msg['role'].upper()}: {msg['message'][:1000]}" # truncate messages that are too long
            for msg in chat_history[-5:]
        ]
    )

    assistant_messages = [
        msg for msg in chat_history
        if msg.get("role") == "assistant"
    ]

    is_initial_briefing = len(assistant_messages) == 0

    conversation_mode = (
        "INITIAL_SESSION_BRIEFING"
        if is_initial_briefing
        else "FOLLOW_UP_CONVERSATION"
    )

    context = f"""
CONVERSATION MODE

{conversation_mode}

INSTRUCTIONS

{
    "Provide a complete observing briefing using: Recommended Objects, Why They Are Visible, Equipment Advice, and Viewing Tips"
    if is_initial_briefing
    else
    "Use a natural conversational format. Include headings only when they improve readability. Only discuss weather, equipment, visibility, or recommendations if relevant to the current question. Answer only the user's latest question. Do not repeat previous recommendations, visibility explanations, equipment advice, or weather summaries unless directly relevant."
}

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
            chat_history=chat_history,
            user_message=user_message
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