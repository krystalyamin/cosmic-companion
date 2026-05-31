"""
Central Configuration Layer
Safely loads config values for application.
Forcibly exits if config is not set up properly.
"""

import os
import sys
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables if testing locally
load_dotenv()

# --- CONFIGURATION & SECURITY GATEKEEPER ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("Configuration Error: GROQ_API_KEY is missing!")
    st.info("Please add your key to a `.env` file locally or inside Streamlit's Secrets panel on the cloud.")
    st.stop()
    sys.exit(1)

# MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")
# DB_NAME = os.getenv("DB_NAME", "review_history.db")
