"""
Main application loop and GUI.

UI created with Streamlit, and code generated with ChatGPT.
"""

import json
import uuid
from datetime import date, time, timedelta

import streamlit as st

from orchestrator import process_user_request
from services.llm_service import test_groq_connection
from services.astronomy_service import get_astronomy_data
from services.weather_service import (
    test_weather_api_connection,
    geocode_location
)
from services.memory_service import (
    test_memory_connection,
    save_session_data,
    load_session_data,
    get_chat_history,
    initialize_session_collection,
    delete_session
)

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="AI Stargazing Planner",
    page_icon="🌌",
    layout="wide"
)

# ============================================================
# SESSION STATE
# ============================================================

if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "show_new_session_form" not in st.session_state:
    st.session_state.show_new_session_form = True

# Tracks whether we have already pulled history from ChromaDB
# in this process — only needs to happen once per app start
if "sessions_loaded" not in st.session_state:
    st.session_state.sessions_loaded = False

# Cache the last validated location so geocoding only fires
# when the location field value actually changes
if "location_validation" not in st.session_state:
    st.session_state.location_validation = {
        "last_input": None,   # the raw string that was checked
        "is_valid":   None,   # True / False / None (not yet checked)
        "error":      None    # human-readable error message
    }

# Set to a warning string if loading past sessions from ChromaDB
# fails on startup — displayed as a non-blocking banner
if "db_load_warning" not in st.session_state:
    st.session_state.db_load_warning = None


# ============================================================
# ERROR DETECTION HELPERS
# ============================================================

# Prefixes that the orchestrator and individual services use when
# they catch an exception and return a plain-text error string.
_ERROR_PREFIXES = (
    "Unable to process",
    "Unable to generate",
    "Unable to retrieve",
    "Error:",
    "error",
)

def _is_error_response(text: str) -> bool:
    """
    Return True if *text* looks like an error string returned by
    the orchestrator or one of the service layers, rather than a
    genuine AI answer.
    """
    if not text:
        return True
    lowered = text.lower().strip()
    return any(lowered.startswith(p.lower()) for p in _ERROR_PREFIXES)


def _classify_error(text: str) -> dict:
    """
    Inspect an error string and return a dict with:
        title       – short heading shown in st.error
        detail      – one-line explanation
        actions     – list of bullet-point steps the user can take
    """
    lowered = text.lower()

    if "groq" in lowered or "llm" in lowered or "completion" in lowered:
        return {
            "title":   "🤖 AI Service Unavailable (Groq API)",
            "detail":  "The language model could not be reached.",
            "actions": [
                "Check that your `GROQ_API_KEY` in `.env` is correct and not expired.",
                "Visit [Groq status page](https://status.groq.com) to check for outages.",
                "Confirm your network connection is active.",
                "If the key is valid, wait a moment and try again — the API may be rate-limiting.",
            ],
        }

    if "astronomy" in lowered or "planet" in lowered or "astronomyapi" in lowered:
        return {
            "title":   "🔭 Astronomy Data Unavailable",
            "detail":  "Could not fetch planet or moon data for your session.",
            "actions": [
                "Check that `ASTRONOMY_API_ID` and `ASTRONOMY_API_SECRET` are set in `.env`.",
                "Visit [AstronomyAPI status](https://astronomyapi.com) to check for outages.",
                "Confirm your account has remaining API credits.",
                "Your session will continue — the AI will note that live sky data is unavailable.",
            ],
        }

    if "weather" in lowered or "forecast" in lowered or "open-meteo" in lowered:
        return {
            "title":   "🌤 Weather Data Unavailable",
            "detail":  "Could not retrieve the weather forecast for your location.",
            "actions": [
                "Open-Meteo is a free public API — check [open-meteo.com](https://open-meteo.com) for outages.",
                "Ensure your network allows outbound HTTPS traffic.",
                "Weather data will be skipped; astronomy recommendations will still work.",
            ],
        }

    if "chroma" in lowered or "memory" in lowered or "collection" in lowered:
        return {
            "title":   "💾 Memory Service Unavailable (ChromaDB)",
            "detail":  "Could not save or retrieve conversation history.",
            "actions": [
                "Check that `CHROMA_DB_PATH` in `.env` points to a writable directory.",
                "Ensure the ChromaDB package is installed: `pip install chromadb`.",
                "Restart the application — ChromaDB sometimes needs a clean process.",
            ],
        }

    if "coordinates" in lowered or "geocod" in lowered or "location" in lowered:
        return {
            "title":   "📍 Location Could Not Be Found",
            "detail":  "The location you entered could not be geocoded to coordinates.",
            "actions": [
                "Try a more specific location name, e.g. \"Singapore\" or \"New York, USA\".",
                "Avoid special characters or abbreviations.",
                "Check your network connection (geocoding uses an external API).",
            ],
        }

    # Generic fallback
    return {
        "title":   "⚠️ Something Went Wrong",
        "detail":  "An unexpected error occurred while processing your request.",
        "actions": [
            "Check the terminal / logs for a more detailed traceback.",
            "Verify all API keys in your `.env` file are correct.",
            "Restart the Streamlit app: `streamlit run app.py`.",
        ],
    }


def _render_error_card(text: str) -> None:
    """
    Display a structured, actionable error card using st.error
    and st.expander so the raw message is accessible if needed.
    """
    info = _classify_error(text)

    st.error(f"**{info['title']}**\n\n{info['detail']}")

    with st.expander("What can I do?", expanded=True):
        for action in info["actions"]:
            st.markdown(f"- {action}")

    with st.expander("Technical details", expanded=False):
        st.code(text, language=None)


if "pending_error" not in st.session_state:
    st.session_state.pending_error = None

# ============================================================
# STARTUP: load persisted sessions from ChromaDB
# ============================================================

def create_chat_title(session_data):
    """
    Create a ChatGPT-style sidebar title from session data.
    """

    session_date = session_data["date"]
    date_string  = str(session_date)

    goals = session_data.get("goal", [])
    topic = ", ".join(goals) if goals else "General Stargazing"

    return f"🌙 {date_string} | {session_data['location']} | {topic}"


def load_sessions_from_db() -> None:
    """
    Hydrate st.session_state.chat_sessions from ChromaDB on
    first load. Each saved session becomes a sidebar entry;
    its chat messages are loaded so the conversation is
    immediately viewable when the user selects it.
    """

    try:
        collection = initialize_session_collection()

        # Fetch every saved session (no filter = all rows)
        results = collection.get(
            include=["documents", "metadatas"]
        )

        ids       = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])

        for session_id, document, metadata in zip(
            ids, documents, metadatas
        ):
            # Skip sessions already in memory
            # (e.g. created earlier in the same process)
            if session_id in st.session_state.chat_sessions:
                continue

            try:
                session_data = json.loads(document)
            except (json.JSONDecodeError, TypeError):
                continue

            # Rebuild chat messages from ChromaDB
            raw_messages = get_chat_history(
                session_id=session_id,
                limit=200
            )

            # get_chat_history returns {"role", "message", "timestamp"}
            # — remap to the {"role", "content"} shape the UI expects
            messages = [
                {
                    "role":    msg["role"],
                    "content": msg["message"]
                }
                for msg in raw_messages
            ]

            title = create_chat_title(session_data)

            st.session_state.chat_sessions[session_id] = {
                "id":           session_id,
                "title":        title,
                "session_data": session_data,
                "messages":     messages,
                "saved_at":     metadata.get("saved_at", "")
            }

    except Exception as exc:
        # Surface a non-blocking warning so the user knows
        # past sessions could not be loaded, without crashing.
        st.session_state.db_load_warning = (
            f"⚠️ Could not load previous sessions from memory: {exc}. "
            "Check that ChromaDB is configured correctly in your `.env` file."
        )


if not st.session_state.sessions_loaded:
    load_sessions_from_db()
    st.session_state.sessions_loaded = True

    # If sessions were found, start on the form rather than
    # forcing the user straight into one of the old chats
    if st.session_state.chat_sessions:
        st.session_state.show_new_session_form = True


# ============================================================
# HELPERS
# ============================================================


def validate_location(location: str) -> tuple[bool, str | None]:
    """
    Call geocode_location and return (is_valid, error_message).

    Results are cached in st.session_state so the geocoding API
    is only called when the location string changes.
    """

    cache = st.session_state.location_validation

    if cache["last_input"] == location:
        return cache["is_valid"], cache["error"]

    # New input — run the geocoding check
    try:
        geocode_location(location)
        result   = (True, None)

    except ValueError:
        result = (
            False,
            f'Could not find "{location}". '
            "Please enter a recognisable city, region, or address."
        )

    except Exception:
        result = (
            False,
            "Unable to verify the location right now. "
            "Please check your connection and try again."
        )

    st.session_state.location_validation = {
        "last_input": location,
        "is_valid":   result[0],
        "error":      result[1]
    }

    return result

def get_current_chat():
    """
    Get information about current chat session.
    """
    chat_id = st.session_state.current_chat_id

    if not chat_id:
        return None

    return st.session_state.chat_sessions.get(chat_id)


def create_new_chat(session_data) -> bool:
    """
    Create a new chat session and generate an opening briefing
    by calling process_user_request with a fixed opening prompt.

    Returns:
        True  — session created and opening briefing generated OK.
        False — a service error occurred; caller should show error UI.
    """

    from datetime import datetime, timezone

    chat_id = str(uuid.uuid4())

    title    = create_chat_title(session_data)
    saved_at = datetime.now(timezone.utc).isoformat()

    # Persist the session settings to ChromaDB before the first call
    try:
        save_session_data(chat_id, session_data)
    except Exception as exc:
        st.session_state.pending_error = (
            f"Unable to save session to memory: {exc}"
        )
        return False

    # Register the chat with an empty message list first so the
    # session exists when process_user_request calls get_chat_history
    st.session_state.chat_sessions[chat_id] = {
        "id":           chat_id,
        "title":        title,
        "session_data": session_data,
        "messages":     [],
        "saved_at":     saved_at
    }

    st.session_state.current_chat_id = chat_id
    st.session_state.show_new_session_form = False

    # Generate the initial AI briefing via the real orchestrator
    opening_prompt = (
        "Please give me a full observing briefing for tonight's session. "
        "Cover what's visible, the weather outlook, and your top recommended targets "
        "for my equipment and goals."
    )

    initial_response = process_user_request(
        session_id=chat_id,
        session_data=session_data,
        user_message=opening_prompt
    )

    # The orchestrator already persisted both messages in ChromaDB.
    # Mirror them into Streamlit session state for display.
    st.session_state.chat_sessions[chat_id]["messages"] = [
        {"role": "user",      "content": opening_prompt},
        {"role": "assistant", "content": initial_response}
    ]

    # Store whether the opening response was an error so the chat
    # view can render it with the appropriate error card.
    if _is_error_response(initial_response):
        st.session_state.chat_sessions[chat_id]["opening_error"] = True

    return True


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🌌 Stargazing Planner")

    if st.button(
        "➕ New Stargazing Session",
        use_container_width=True
    ):
        st.session_state.show_new_session_form = True

    st.divider()

    st.subheader("Sessions")

    if not st.session_state.chat_sessions:
        st.caption("No sessions yet.")

    sorted_sessions = sorted(
        st.session_state.chat_sessions.values(),
        key=lambda c: c.get("saved_at", ""),
        reverse=True
    )

    for chat in sorted_sessions:

        chat_id = chat["id"]

        col_title, col_delete = st.columns([5, 1])

        with col_title:
            if st.button(
                chat["title"],
                key=f"session_{chat_id}",
                use_container_width=True
            ):
                st.session_state.current_chat_id = chat_id
                st.session_state.show_new_session_form = False

        with col_delete:
            if st.button(
                "🗑",
                key=f"delete_{chat_id}",
                help="Delete this session"
            ):
                # Remove from ChromaDB
                delete_session(chat_id)

                # Remove from in-memory state
                del st.session_state.chat_sessions[chat_id]

                # If this was the active chat, reset to the form
                if st.session_state.current_chat_id == chat_id:
                    st.session_state.current_chat_id = None
                    st.session_state.show_new_session_form = True

                st.rerun()

    st.divider()

    # --------------------------------------------------------
    # Live API Status using real test functions
    # --------------------------------------------------------

    st.subheader("API Status")

    groq_ok      = test_groq_connection()
    weather_ok   = test_weather_api_connection()
    memory_ok    = test_memory_connection()

    if groq_ok:
        st.success("✅ Groq API")
    else:
        st.error("❌ Groq API")
        st.caption(
            "Check `GROQ_API_KEY` in `.env` and confirm your "
            "[Groq account](https://console.groq.com) is active."
        )

    if weather_ok:
        st.success("✅ Weather API")
    else:
        st.error("❌ Weather API")
        st.caption(
            "Open-Meteo is a free public API. "
            "Check your network connection or visit "
            "[open-meteo.com](https://open-meteo.com) for status."
        )

    if memory_ok:
        st.success("✅ Memory (ChromaDB)")
    else:
        st.error("❌ Memory (ChromaDB)")
        st.caption(
            "Check `CHROMA_DB_PATH` in `.env` and ensure the "
            "directory exists and is writable."
        )

    # Non-blocking warning if past sessions failed to load on startup
    if st.session_state.db_load_warning:
        st.divider()
        st.warning(st.session_state.db_load_warning)


# ============================================================
# NEW SESSION FORM
# ============================================================

if (
    st.session_state.show_new_session_form
    or st.session_state.current_chat_id is None
):

    st.title("🌌 AI Stargazing Planner")

    st.markdown(
        "Start a new observing session by filling out the details below."
    )

    with st.form("observation_form"):

        st.subheader("Observation Details")

        # Input location
        col_location, col_validate = st.columns([4, 1])

        with col_location:
            location = st.text_input(
                "📍 Observation Location",
                placeholder="Singapore"
            )

        # Check if location is valid
        with col_validate:
            st.markdown("<br>", unsafe_allow_html=True)
            validate_clicked = st.form_submit_button(
                "Check Location",
                use_container_width=True
            )

        if validate_clicked:

            if not location.strip():
                st.warning("Please enter a location first.")

            else:
                with st.spinner("Verifying location..."):

                    location_valid, location_error = validate_location(
                        location.strip()
                    )

                if location_valid:
                    st.success(
                        f"✅ Location found: {location.strip()}"
                    )
                else:
                    st.error(location_error)


        col1, col2 = st.columns(2)

        with col1:
            observation_date = st.date_input(
                "📅 Observation Date",
                value=date.today(),
                max_value=date.today() + timedelta(days=16),
                help="You can select a date up to 16 days in the future."
            )

        with col2:
            observation_time = st.time_input(
                "🕘 Observation Time",
                value=time(21, 0)
            )

        equipment = st.multiselect(
            "🔭 Equipment",
            ["Naked Eye", "Binoculars", "Telescope"],
            default=["Naked Eye"]
        )

        if not equipment:
            st.error("Please select at least one piece of equipment.")

        if "Telescope" in equipment:

            st.markdown("### Telescope Details")

            telescope_type = st.selectbox(
                "Telescope Type",
                ["Refractor", "Reflector", "Dobsonian", "Catadioptric"]
            )

            aperture = st.number_input(
                "Aperture (mm)",
                min_value=50,
                max_value=500,
                value=80
            )

            magnification = st.number_input(
                "Magnification",
                min_value=10,
                max_value=500,
                value=40
            )

        else:
            telescope_type = None
            aperture      = None
            magnification = None

        experience = st.selectbox(
            "Experience Level",
            ["Beginner", "Intermediate", "Advanced"]
        )

        goal = st.multiselect(
            "🎯 Observation Goal",
            [
                "Visible Planets",
                "Moon Viewing",
                "Deep Sky Objects",
                "Meteor Shower",
                "Astrophotography",
                "General Stargazing"
            ],
            default=["General Stargazing"]
        )

        target = st.text_input(
            "Optional Target Object",
            placeholder="Saturn"
        )

        submitted = st.form_submit_button(
            "Start Session",
            use_container_width=True
        )

        if submitted:

            if not location.strip():
                st.error("Please enter an observation location.")

            elif not equipment:
                st.error("Please select at least one piece of equipment.")

            else:
                # Validate the location via geocoding before proceeding
                with st.spinner("Verifying location..."):
                    location_valid, location_error = validate_location(
                        location.strip()
                    )

                if not location_valid:
                    st.error(location_error)

                else:
                    session_data = {
                        # date stored as YYYY-MM-DD string so all services
                        # receive the format they expect
                        "location":       location.strip(),
                        "date":           observation_date.isoformat(),
                        "time":           observation_time.strftime("%H:%M"),
                        "equipment":      equipment,
                        "experience":     experience,
                        "goal":           goal,
                        "target":         target.strip(),
                        # telescope fields — None when no telescope selected
                        "telescope_type": telescope_type,
                        "aperture":       aperture,
                        "magnification":  magnification
                    }

                    with st.spinner(
                        "Setting up your session and fetching astronomy data..."
                    ):
                        success = create_new_chat(session_data)

                    if not success:
                        # create_new_chat stored the error in pending_error
                        error_text = st.session_state.pending_error or "Unknown error"
                        st.session_state.pending_error = None
                        _render_error_card(error_text)
                    else:
                        st.rerun()


# ============================================================
# CHAT VIEW
# ============================================================

else:

    current_chat = get_current_chat()

    if current_chat is None:
        st.stop()

    session_data = current_chat["session_data"]

    # --------------------------------------------------------
    # Session Summary Card
    # --------------------------------------------------------

    st.title("🌌 AI Stargazing Planner")

    with st.container(border=True):

        st.subheader("Current Observing Session")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(f"📍 **Location:** {session_data['location']}")
            st.write(f"📅 **Date:** {session_data['date']}")

        with col2:
            st.write(f"🕘 **Time:** {session_data['time']}")
            st.write(
                f"🔭 **Equipment:** {', '.join(session_data['equipment'])}"
            )

        with col3:
            goals_display = (
                ", ".join(session_data["goal"])
                if session_data["goal"]
                else "General Stargazing"
            )
            st.write(f"🎯 **Goal:** {goals_display}")

            if session_data.get("target"):
                st.write(f"⭐ **Target:** {session_data['target']}")

    st.write("")

    # --------------------------------------------------------
    # Chat Messages
    # --------------------------------------------------------

    for i, message in enumerate(current_chat["messages"]):

        with st.chat_message(message["role"]):

            if (
                message["role"] == "assistant"
                and _is_error_response(message["content"])
            ):
                _render_error_card(message["content"])
            else:
                st.markdown(message["content"])

    # --------------------------------------------------------
    # Chat Input
    # --------------------------------------------------------

    user_prompt = st.chat_input(
        "Ask about visible objects, equipment, viewing tips, photography, and more..."
    )

    if user_prompt:

        # Show user message immediately
        current_chat["messages"].append(
            {"role": "user", "content": user_prompt}
        )

        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Generate AI response via orchestrator
        with st.chat_message("assistant"):
            with st.spinner("Consulting the stars..."):

                response = process_user_request(
                    session_id=current_chat["id"],
                    session_data=session_data,
                    user_message=user_prompt
                )

            if _is_error_response(response):
                _render_error_card(response)
            else:
                st.markdown(response)

        # Mirror assistant reply into Streamlit session state
        # (orchestrator already persisted both sides in ChromaDB)
        current_chat["messages"].append(
            {"role": "assistant", "content": response}
        )

        st.rerun()