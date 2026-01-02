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

# הגדרת מנוע ה-OCR (נטען פעם אחת כדי לחסוך זמן)
@st.cache_resource
def load_ocr():
 # שינינו מ-'he' ל-'iw' כדי לפתור את השגיאה
    return easyocr.Reader(['iw', 'en'])

reader = load_ocr()

# פונקציה להפקת קול
async def generate_audio(text, voice_name, speed):
    communicate = edge_tts.Communicate(text, voice_name, rate=speed)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data

# פונקציה למיון טקסט לפי עמודות (תצוגת עיתון)
def get_layout_aware_text(page):
    blocks = page.get_text("blocks")
    # מחלקים את הדף באמצע
    mid_point = page.rect.width / 2
    
    # מחלקים את הבלוקים לימין ושמאל
    right_column = [b for b in blocks if b[0] > mid_point]
    left_column = [b for b in blocks if b[0] <= mid_point]
    
    # בעברית: קודם קוראים את צד ימין מלמעלה למטה, ואז את צד שמאל
    right_column.sort(key=lambda b: b[1])
    left_column.sort(key=lambda b: b[1])
    
    combined_blocks = right_column + left_column
    return " ".join([b[4].replace('\n', ' ') for b in combined_blocks if b[4].strip()])
uploaded_file = st.file_uploader("העלה קובץ PDF (דיגיטלי או סרוק)", type="pdf")

VOICE_MAP = {
    "he": {"Female": "he-IL-HilaNeural", "Male": "he-IL-AvriNeural"},
    "en": {"Female": "en-US-EmmaNeural", "Male": "en-US-GuyNeural"}
}

if uploaded_file:
    with st.spinner("מעבד את הקובץ... זה עשוי לקחת זמן בגלל ה-OCR"):
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        full_text = ""
        
        for page in doc:
            # 1. ניסיון לחלץ טקסט דיגיטלי עם הבנה של עמודות
            page_text = get_layout_aware_text(page)
            
            # 2. אם העמוד ריק (סריקה), נפעיל OCR
            if len(page_text.strip()) < 10:
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                results = reader.readtext(np.array(img), paragraph=True)
                # מיון תוצאות ה-OCR לפי עמודות
                results.sort(key=lambda r: (r[0][0][0] < (pix.width / 2), r[0][0][1]))
                page_text = " ".join([r[1] for r in results])
            
            full_text += page_text + " "

        if full_text.strip():
            try:
                lang = detect(full_text[:500])
                st.write(f"**שפה שזוהתה:** {lang.upper()}")
                
                speed_pct = st.sidebar.slider("מהירות דיבור (%)", -50, 50, 0, 5)
                gender = st.radio("בחר קול:", ["Female", "Male"])
                
                supported_lang = "he" if lang == "he" else "en"
                selected_voice = VOICE_MAP[supported_lang][gender]

                if st.button("צור קובץ שמע"):
                    with st.spinner("מייצר אודיו..."):
                        audio_bytes = asyncio.run(generate_audio(full_text, selected_voice, f"{speed_pct:+d}%"))
                        st.audio(audio_bytes)
                        st.download_button("הורד MP3", audio_bytes, "audiobook.mp3")
            except Exception as e:
                st.error(f"שגיאה: {e}")

