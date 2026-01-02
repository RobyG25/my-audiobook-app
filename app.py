import streamlit as st
import fitz  # PyMuPDF
import edge_tts
import asyncio
import io
from langdetect import detect

st.set_page_config(page_title="Audiobook Maker", page_icon="📖")

st.title("📖 הפיכת PDF ל-MP3")
st.markdown("גרסה דיגיטלית מהירה - תומכת בעברית ואנגלית עבור נורצ'י")

# הגדרות קול ומהירות בתפריט הצד
st.sidebar.header("הגדרות שמע")
speed_pct = st.sidebar.slider("מהירות דיבור (%)", -50, 50, 0, 5)
gender = st.sidebar.radio("מין הקריין/נית:", ["נקבה", "זכר"])

# מפת קולות - Microsoft Edge Neural Voices
VOICE_MAP = {
    "he": {"נקבה": "he-IL-HilaNeural", "זכר": "he-IL-AvriNeural"},
    "en": {"נקבה": "en-US-EmmaNeural", "זכר": "en-US-GuyNeural"}
}

async def generate_audio(text, voice_name, speed):
    communicate = edge_tts.Communicate(text, voice_name, rate=speed)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

uploaded_file = st.file_uploader("העלה קובץ PDF דיגיטלי", type="pdf")

if uploaded_file:
    with st.spinner("חלץ טקסט מהקובץ..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        # ניקוי טקסט בסיסי: מחבר שורות כדי למנוע קפיצות בקריאה
        full_text = " ".join([page.get_text().replace('\n', ' ') for page in doc])
        
        if len(full_text.strip()) > 10:
            try:
                # זיהוי שפה (עברית או אנגלית)
                lang = detect(full_text[:1000])
                supported_lang = "he" if (lang == 'he' or lang == 'iw') else "en"
                st.info(f"שפה שזוהתה: {supported_lang.upper()}")
                
                selected_voice = VOICE_MAP[supported_lang][gender]

                if st.button("צור קובץ שמע (MP3)"):
                    with st.spinner("מייצר אודיו..."):
                        # הפקת האודיו
                        speed_str = f"{speed_pct:+d}%"
                        audio_bytes = asyncio.run(generate_audio(full_text, selected_voice, speed_str))
                        
                        # הצגת הנגן והורדה
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button(
                            label="הורד קובץ MP3",
                            data=audio_bytes,
                            file_name="my_audiobook.mp3",
                            mime="audio/mp3"
                        )
            except Exception as e:
                st.error(f"אירעה שגיאה: {e}")
        else:
            st.warning("לא נמצא טקסט דיגיטלי בקובץ. וודא שהקובץ אינו סרוק כתמונה.")

st.divider()
st.caption("טיפ: האפליקציה עובדת הכי טוב עם קבצי PDF שיוצרו ב-Word או נשמרו מאתרי אינטרנט.")

