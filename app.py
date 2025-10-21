import streamlit as st
import speech_recognition as sr
from googletrans import Translator, LANGUAGES
from gtts import gTTS
from gtts.lang import tts_langs
import base64
import io
import uuid
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Voice Translator",
    page_icon="🎤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Language mappings ----------
TTS_SUPPORTED = tts_langs()
LANG_NAME_TO_CODE = {name.title(): code for code, name in LANGUAGES.items()}

# ---------- Session State ----------
if 'detected_lang_code' not in st.session_state:
    st.session_state.detected_lang_code = "auto"
if 'translation_history' not in st.session_state:
    st.session_state.translation_history = []
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = None

# ---------- Speech Recognition ----------
def listen_speech():
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.9
    recognizer.phrase_threshold = 0.4
    recognizer.non_speaking_duration = 0.5

    try:
        with sr.Microphone() as source:
            status_placeholder = st.empty()
            status_placeholder.info("Calibrating mic... stay quiet")
            
            recognizer.adjust_for_ambient_noise(source, duration=1.5)

            status_placeholder.info("Listening... Speak now 🎤")
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=25)

            status_placeholder.info("Recognizing speech...")

            # Get selected input language
            selected_input_lang = st.session_state.input_lang
            if selected_input_lang == "Auto Detect":
                lang_code = "auto"
            else:
                lang_code = LANG_NAME_TO_CODE.get(selected_input_lang, "auto")

            # Recognize speech
            if lang_code != "auto":
                if lang_code == "te":
                    lang_code = "te-IN"
                text = recognizer.recognize_google(audio, language=lang_code)
                st.session_state.detected_lang_code = lang_code.split("-")[0]
            else:
                # Auto mode
                raw_text = recognizer.recognize_google(audio, show_all=False)
                translator = Translator()
                detected = translator.detect(raw_text)
                st.session_state.detected_lang_code = detected.lang
                try:
                    text = recognizer.recognize_google(audio, language=st.session_state.detected_lang_code)
                except Exception:
                    text = raw_text

            st.session_state.input_text = text
            detected_lang_name = LANGUAGES.get(st.session_state.detected_lang_code, "Unknown").title()
            status_placeholder.success(f"Speech captured ({detected_lang_name}) ✅")

    except sr.WaitTimeoutError:
        st.error("No speech detected. Please try again.")
    except sr.UnknownValueError:
        st.error("Could not understand audio. Try speaking clearly.")
    except sr.RequestError:
        st.error("Speech service unavailable.")
    except Exception as e:
        st.error(f"Error: {str(e)}")

# ---------- Translation ----------
def translate_text():
    text = st.session_state.input_text.strip()
    if not text:
        st.warning("No input text to translate!")
        return

    tgt_full = st.session_state.target_lang.strip()
    if not tgt_full:
        st.warning("Please select a Target Language.")
        return

    dest_code = LANG_NAME_TO_CODE[tgt_full]

    try:
        translator = Translator()
        result = translator.translate(text, src=st.session_state.detected_lang_code, dest=dest_code)

        st.session_state.translated_text = result.text

        # Save history
        src_lang_name = LANGUAGES.get(result.src, "Unknown").title()
        tgt_lang_name = LANGUAGES.get(dest_code, "Unknown").title()
        st.session_state.translation_history.append(
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             src_lang_name, tgt_lang_name, text, result.text]
        )

        st.success(f"Translated {src_lang_name} → {tgt_lang_name} ✅")

    except Exception as e:
        st.error(f"Translation error: {str(e)}")

# ---------- Text-to-Speech ----------
def speak_text(text, lang_code):
    try:
        if lang_code in TTS_SUPPORTED:
            tts = gTTS(text, lang=lang_code)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            # Store audio in session state
            st.session_state.audio_data = audio_buffer
            st.session_state.audio_lang = lang_code
            
        else:
            st.warning(f"No TTS support for {LANGUAGES.get(lang_code, lang_code)}")
    except Exception as e:
        st.error(f"TTS Error: {str(e)}")

def speak_input():
    text = st.session_state.input_text.strip()
    if text and st.session_state.detected_lang_code in TTS_SUPPORTED:
        speak_text(text, st.session_state.detected_lang_code)
    else:
        st.info("No input text or unsupported language for TTS.")

def speak_output():
    text = st.session_state.translated_text.strip()
    tgt_full = st.session_state.target_lang.strip()
    if text and tgt_full:
        dest_code = LANG_NAME_TO_CODE[tgt_full]
        speak_text(text, dest_code)
    else:
        st.info("No translated text to speak.")

# ---------- History ----------
def view_history():
    if not st.session_state.translation_history:
        st.info("No translations yet.")
        return
    
    st.subheader("Translation History")
    for entry in st.session_state.translation_history:
        timestamp, src, tgt, inp, outp = entry
        with st.expander(f"[{timestamp}] {src} → {tgt}"):
            st.write(f"**Input:** {inp}")
            st.write(f"**Output:** {outp}")
            st.write("---")

# ---------- Streamlit UI ----------
def main():
    st.title("🎤 Voice Translator")
    st.markdown("Translate speech or text between multiple languages with text-to-speech support")

    # Initialize session state variables
    if 'input_text' not in st.session_state:
        st.session_state.input_text = ""
    if 'translated_text' not in st.session_state:
        st.session_state.translated_text = ""
    if 'input_lang' not in st.session_state:
        st.session_state.input_lang = "Auto Detect"
    if 'target_lang' not in st.session_state:
        st.session_state.target_lang = "English"

    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        st.session_state.input_lang = st.selectbox(
            "Input Language:",
            ["Auto Detect"] + list(LANG_NAME_TO_CODE.keys()),
            index=0
        )
        st.session_state.target_lang = st.selectbox(
            "Target Language:",
            list(LANG_NAME_TO_CODE.keys()),
            index=list(LANG_NAME_TO_CODE.keys()).index("English") if "English" in LANG_NAME_TO_CODE else 0
        )
        
        st.markdown("---")
        if st.button("📝 View History", use_container_width=True):
            view_history()

    # Main content area
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Input Text")
        st.session_state.input_text = st.text_area(
            "Recognized Speech / Input Text:",
            value=st.session_state.input_text,
            height=150,
            placeholder="Speak using the microphone or type here...",
            key="input_text_area"
        )

    with col2:
        st.subheader("Translated Text")
        st.session_state.translated_text = st.text_area(
            "Translated Text:",
            value=st.session_state.translated_text,
            height=150,
            placeholder="Translation will appear here...",
            key="translated_text_area"
        )

    # Buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🎤 Speak", use_container_width=True):
            listen_speech()

    with col2:
        if st.button("🌍 Translate", use_container_width=True):
            translate_text()

    with col3:
        if st.button("📢 Speak Input", use_container_width=True):
            speak_input()

    with col4:
        if st.button("📢 Speak Output", use_container_width=True):
            speak_output()

    # Audio player
    if st.session_state.audio_data:
        st.markdown("---")
        st.subheader("Audio Output")
        audio_bytes = st.session_state.audio_data.getvalue()
        st.audio(audio_bytes, format='audio/mp3')
        
        # Download button for audio
        st.download_button(
            label="📥 Download Audio",
            data=audio_bytes,
            file_name=f"translation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3",
            mime="audio/mp3"
        )

    # Status
    if st.session_state.detected_lang_code != "auto":
        detected_lang_name = LANGUAGES.get(st.session_state.detected_lang_code, "Unknown").title()
        st.sidebar.markdown(f"**Detected Language:** {detected_lang_name}")

    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. **Select Input Language** (or use Auto Detect)
        2. **Select Target Language**
        3. Click **🎤 Speak** to record your voice
        4. Click **🌍 Translate** to translate the text
        5. Use **📢 Speak** buttons to hear the text
        6. View history in the sidebar
        """)

if __name__ == "__main__":
    main()