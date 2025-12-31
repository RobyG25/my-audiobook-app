import streamlit as st
import fitz
import edge_tts
import asyncio
import io
from langdetect import detect

st.set_page_config(page_title="Custom Audiobook Maker", page_icon="🎙️")
st.title("🎙️ PDF to MP3 with Voice Control")

# 1. Sidebar for Settings
st.sidebar.header("Voice Settings")
speed_pct = st.sidebar.slider("Speed Adjustment (%)", -50, 50, 0, 5)
# Convert speed to the format edge-tts expects (e.g., "+10%" or "-5%")
speed_str = f"{speed_pct:+d}%"

uploaded_file = st.file_uploader("Upload a PDF (English or Hebrew)", type="pdf")

# Define available voices
VOICE_MAP = {
    "he": {
        "Female": "he-IL-HilaNeural",
        "Male": "he-IL-AvriNeural"
    },
    "en": {
        "Female": "en-US-EmmaNeural",
        "Male": "en-US-GuyNeural"
    }
}

async def generate_audio(text, voice_name, speed):
    communicate = edge_tts.Communicate(text, voice_name, rate=speed)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

if uploaded_file:
    with st.spinner("Extracting text..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        # Cleaning: join lines to fix the "skipping" issue you had
        text = " ".join([page.get_text().replace('\n', ' ') for page in doc])
        
        if text.strip():
            try:
                lang = detect(text[:1000])
                # Default to English if detection is unsure
                supported_lang = lang if lang in VOICE_MAP else "en"
                
                st.write(f"**Detected Language:** {lang.upper()}")
                
                # 2. Voice Selection UI
                gender = st.radio("Select Voice Gender:", ["Female", "Male"])
                selected_voice = VOICE_MAP[supported_lang][gender]

                if st.button("Generate MP3"):
                    with st.spinner("Creating audio..."):
                        audio_bytes = asyncio.run(generate_audio(text, selected_voice, speed_str))
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button("Download MP3", audio_bytes, file_name="audiobook.mp3")
            except Exception as e:
                st.error(f"Something went wrong: {e}")