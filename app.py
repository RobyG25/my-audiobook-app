import streamlit as st
import fitz  # PyMuPDF
import edge_tts
import asyncio
import io
import numpy as np
import easyocr
from langdetect import detect
from PIL import Image

st.set_page_config(page_title="Audiobook Pro", page_icon="🎙️")
st.title("🎙️ מעבד PDF מתקדם: עמודות וסריקות")

# הגדרת מנוע ה-OCR עם בדיקת שגיאות
@st.cache_resource
def load_ocr():
    try:
        return easyocr.Reader(['he', 'en'])
    except:
        return easyocr.Reader(['en'])

reader = load_ocr()

# פונקציה להפקת קול
async def generate_audio(text, voice_name, speed):
    communicate = edge_tts.Communicate(text, voice_name, rate=speed)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# פונקציה למיון טקסט לפי עמודות (תצוגת עיתון/ספר פתוח)
def get_layout_aware_text(page):
    blocks = page.get_text("blocks")
    if not blocks:
        return ""
    
    mid_point = page.rect.width / 2
    
    # מיון בלוקים לפי עמודה ימנית ואז שמאלית (מתאים לעברית)
    right_column = [b for b in blocks if b[0] > (mid_point - 20)]
    left_column = [b for b in blocks if b[0] <= (mid_point - 20)]
    
    # מיון כל עמודה מלמעלה למטה
    right_column.sort(key=lambda b: b[1])
    left_column.sort(key=lambda b: b[1])
    
    combined = right_column + left_column
    return " ".join([b[4].replace('\n', ' ') for b in combined if b[4].strip()])

uploaded_file = st.file_uploader("העלה קובץ PDF", type="pdf")

VOICE_MAP = {
    "he": {"Female": "he-IL-HilaNeural", "Male": "he-IL-AvriNeural"},
    "en": {"Female": "en-US-EmmaNeural", "Male": "en-US-GuyNeural"}
}

if uploaded_file:
    with st.spinner("מעבד דפים..."):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        
        for page in doc:
            page_text = get_layout_aware_text(page)
            
            # אם הדף סרוק (תמונה)
            if len(page_text.strip()) < 20:
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                results = reader.readtext(np.array(img), paragraph=True)
                
                # מיון תוצאות OCR לפי עמודות (ימין ואז שמאל)
                mid = pix.width / 2
                r_res = [r for r in results if r[0][0][0] > (mid - 20)]
                l_res = [r for r in results if r[0][0][0] <= (mid - 20)]
                
                r_res.sort(key=lambda r: r[0][0][1])
                l_res.sort(key=lambda r: r[0][0][1])
                
                page_text = " ".join([r[1] for r in r_res + l_res])
            
            full_text += page_text + " "

        if full_text.strip():
            try:
                lang = detect(full_text[:1000])
                st.write(f"**שפה שזוהתה:** {lang.upper()}")
                
                speed_pct = st.sidebar.slider("מהירות (%)", -50, 50, 0, 5)
                gender = st.radio("בחר קול:", ["Female", "Male"])
                
                # תמיכה בעברית ואנגלית בלבד כרגע
                supported_lang = "he" if (lang == 'he' or lang == 'iw') else "en"
                selected_voice = VOICE_MAP[supported_lang][gender]

                if st.button("צור קובץ שמע"):
                    with st.spinner("מייצר אודיו..."):
                        audio_bytes = asyncio.run(generate_audio(full_text, selected_voice, f"{speed_pct:+d}%"))
                        st.audio(audio_bytes)
                        st.download_button("הורד MP3", audio_bytes, "audiobook.mp3")
            except Exception as e:
                st.error(f"שגיאה בעיבוד השפה: {e}")
