"""
Main application loop and GUI.

UI created with Streamlit, and code generated with ChatGPT.
"""

import uuid
from datetime import datetime, date, time

import streamlit as st
from prompts import generate_initial_briefing, ask_stargazing_assistant
from config import GROQ_API_KEY

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


# ============================================================
# HELPERS
# ============================================================


def create_chat_title(session_data):
    """
    Create a ChatGPT-style title.
    """

    session_date = session_data["date"]

    if isinstance(session_date, date):
        date_string = session_date.strftime("%d %b")
    else:
        date_string = str(session_date)

    topic = session_data["goal"]

    return f"🌙 {date_string} | {session_data['location']} | {topic}"


def get_current_chat():
    chat_id = st.session_state.current_chat_id

    if not chat_id:
        return None

    return st.session_state.chat_sessions.get(chat_id)


def create_new_chat(session_data):
    """
    Create a new chat session.
    """

    chat_id = str(uuid.uuid4())

    title = create_chat_title(session_data)

    initial_ai_message = generate_initial_briefing(session_data)

    st.session_state.chat_sessions[chat_id] = {
        "id": chat_id,
        "title": title,
        "session_data": session_data,
        "messages": [
            {
                "role": "assistant",
                "content": initial_ai_message
            }
        ]
    }

    st.session_state.current_chat_id = chat_id
    st.session_state.show_new_session_form = False


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

    for chat_id, chat in st.session_state.chat_sessions.items():

        if st.button(
            chat["title"],
            key=f"session_{chat_id}",
            use_container_width=True
        ):
            st.session_state.current_chat_id = chat_id
            st.session_state.show_new_session_form = False

    st.divider()

    st.subheader("API Status")

    st.success("Groq API")
    st.success("Astronomy API")
    st.success("Weather API")


# ============================================================
# NEW SESSION FORM
# ============================================================

if (
    st.session_state.show_new_session_form
    or st.session_state.current_chat_id is None
):

    st.title("🌌 AI Stargazing Planner")

    st.markdown(
        """
        Start a new observing session by filling out the details below.
        """
    )

    with st.form("observation_form"):

        st.subheader("Observation Details")

        location = st.text_input(
            "📍 Observation Location",
            placeholder="Singapore"
        )

        col1, col2 = st.columns(2)

        with col1:
            observation_date = st.date_input(
                "📅 Observation Date",
                value=date.today()
            )

        with col2:
            observation_time = st.time_input(
                "🕘 Observation Time",
                value=time(21, 0)
            )

        equipment = st.multiselect(
            "🔭 Equipment",
            [
                "Naked Eye",
                "Binoculars",
                "Telescope"
            ],
            default=["Naked Eye"]
        )

        if not equipment:
            st.error(
                "Please select at least one piece of equipment."
            )

        if "Telescope" in equipment:

            st.markdown("### Telescope Details")

            telescope_type = st.selectbox(
                "Telescope Type",
                [
                    "Refractor",
                    "Reflector",
                    "Dobsonian",
                    "Catadioptric"
                ]
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
            aperture = None
            magnification = None

        experience = st.selectbox(
            "Experience Level",
            [
                "Beginner",
                "Intermediate",
                "Advanced"
            ]
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
                st.error(
                    "Please enter an observation location."
                )
            else:
                session_data = {
                    "location": location, # string
                    "date": observation_date, # string
                    "time": observation_time.strftime("%H:%M"), #string
                    "equipment": equipment, # list of strings (naked eye, binoculars, telescope)
                    "experience": experience, # string (beginner, intermediate, or advanced)
                    "goal": goal, # list of strings ("Visible Planets", "Moon Viewing", "Deep Sky Objects", "Meteor Shower", "Astrophotography", "General Stargazing")
                    "target": target, # string (optional, so could be an emptyy string)
                    # optional fields, only not None if "Telescope" is listed under "Equipment"
                    "telescope_type": telescope_type, # string
                    "aperture": aperture, # integer
                    "magnification": magnification #integer
                }

                create_new_chat(session_data)

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
            st.write(f"🎯 **Goal:** {session_data['goal']}")

            if session_data["target"]:
                st.write(
                    f"⭐ **Target:** {session_data['target']}"
                )

    st.write("")

    # --------------------------------------------------------
    # Chat Messages
    # --------------------------------------------------------

    for message in current_chat["messages"]:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --------------------------------------------------------
    # Chat Input
    # --------------------------------------------------------

    user_prompt = st.chat_input(
        "Ask about visible objects, equipment, viewing tips, photography, and more..."
    )

    if user_prompt:

        current_chat["messages"].append(
            {
                "role": "user",
                "content": user_prompt
            }
        )

        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):

            with st.spinner("Consulting the stars..."):

                response = ask_stargazing_assistant(
                    user_prompt,
                    session_data,
                    current_chat["messages"]
                )

                st.markdown(response)

        current_chat["messages"].append(
            {
                "role": "assistant",
                "content": response
            }
        )

        st.rerun()