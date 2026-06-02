# cosmic-companion

Cosmic Companion: The AI-powered chatbot that helps you plan your stargazing sessions!

---

## Problem Statement

Beginner stargazers often do not know which celestial objects are visible on a given night, whether their equipment is capable of observing them, or how to locate them in the sky. This application solves that problem by pulling live planet positions, moon data, and weather forecasts for the user's chosen location and date, then using an LLM to translate that raw data into plain-language recommendations tailored to the user's specific equipment and goals.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Frontend | Streamlit |
| LLM Provider | Groq API |
| Astronomy Data | AstronomyAPI (planet positions) · IPGeolocation API (moon phase) |
| Weather Data | Open-Meteo Forecast API · Open-Meteo Geocoding API |
| Persistent Memory | ChromaDB (local vector database) |
| Configuration | python-dotenv |
| Key Libraries | `requests`, `chromadb`, `groq`, `streamlit` |

---

## Setup Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/krystalyamin/cosmic-companion.git
   cd cosmic-companion/src
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS / Linux
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Copy the example file and fill in your API keys:

   ```bash
   cp .env.example .env
   ```

   Open `.env` and set the following values:

   ```
	PROJECT_ROOT_PATH=<absolute-path-here>
	GROQ_API_KEY=<groq-key-here: https://console.groq.com>
	IPGEO_API_KEY=<ipgeolocation-key-here: https://ipgeolocation.io>
	ASTRONOMY_API_ID=<astronomyapi-id-here: https://astronomyapi.com>
	ASTRONOMY_API_SECRET=<astronomyapi-secret-here: https://astronomyapi.com>
   ```

   API keys can be obtained for free from:
   - Groq: https://console.groq.com
   - AstronomyAPI: https://astronomyapi.com
   - IPGeolocation: https://ipgeolocation.io

5. **Run the application**

   ```bash
   streamlit run app.py
   ```

   The app will open automatically at `http://localhost:8501`.

---

## Usage Examples

### Example 1 — Beginner with binoculars

**Session setup:**
- Location: Singapore
- Date: 2026-08-15
- Time: 21:00
- Equipment: Binoculars
- Experience: Beginner
- Goal: Visible Planets

**AI response (excerpt):**

>**Recommended Targets:** My top recommendation for tonight, considering your equipment and goals, is the Moon. It's a full moon, which makes it a reliable and easy target to observe. The Moon is always a fascinating sight, and with your naked eye, you can observe its phases and surface features like craters and mare.
>
>**Equipment Advice:** Since you're using the naked eye, make sure to find a spot with minimal light pollution to get the best view. While the Moon is easily visible to the naked eye, the low-horizon positions of Venus and Jupiter might be more difficult without any optical aid.
>
>**Viewing Tips:** For observing the Moon, try to find a comfortable spot where you can sit and enjoy the view without straining your neck. Look for the different shades and textures on the Moon's surface. If you decide to try and spot Venus or Jupiter, look towards the west (azimuth around 294 degrees for Venus and 292 degrees for Jupiter), but be aware that they are low on the horizon and might be hard to see clearly.

---

### Example 2 — Follow-up question using conversation memory

After the session above is running, the user asks a follow-up without repeating any details:

**User:** "Will Saturn be visible?"

**AI response (excerpt):**

> Saturn is not mentioned in the list of visible planets for your location at 21:00. This suggests that Saturn is not visible, or at least not easily visible, during your observing session tonight.

The application remembered the location, date, time, and equipment from the original session without the user needing to re-enter them.

---

## Known Limitations

- **Limited to one location and time per session:** The chatbot cannot help with prompts that involve a range of locations or timings.

- **Forecast range:** The Open-Meteo API only provides forecasts up to approximately 16 days ahead. Entering a date beyond that window will return an error rather than weather data.

- **Deep sky object positions:** The current recommendation engine suggests well-known deep sky objects (Orion Nebula, Andromeda Galaxy, Pleiades) based on equipment type and goals, but does not verify whether those objects are actually above the horizon for the chosen location and date. A future version should cross-check against real altitude data before recommending them.

---

## Future Improvements

- **Intgrate Stellarium API:** Give the chatbot the ability to configure a Stellarium star map according to the details of the user's stargazing session and provide the user with a link to open the visualization straight in their browser for reference.

- **Integrate web search capabilities:** Enable web search capabilities when the model needs more information on specific topics like astrophotography. 
