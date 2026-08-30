import cv2
from PIL import Image
from google import genai
from gtts import gTTS
import pygame
import speech_recognition as sr
import tempfile
import os
from dotenv import load_dotenv
import threading
import time

# ==========================================
# GEMINI API KEY
# ==========================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set")

client = genai.Client(api_key=API_KEY)
# ==========================================
# GLOBALS
# ==========================================

selected_language = "English"
speech_language_code = "en"
last_result = ""
running = True

# ==========================================
# AUDIO
# ==========================================

pygame.mixer.init()

# ==========================================
# SPEAK
# ==========================================

def speak(text):

    temp_path = None

    try:
        print("\nSpeaking...")
        print(text)

        tts = gTTS(
            text=text,
            lang=speech_language_code,
            slow=False
        )

        with tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        ) as f:
            temp_path = f.name

        tts.save(temp_path)

        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    except Exception as e:
        print("Speech Error:", e)

    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass

# ==========================================
# VOICE COMMANDS
# ==========================================

def voice_command_listener():

    global selected_language
    global speech_language_code
    global running
    global last_result

    recognizer = sr.Recognizer()

    while running:

        try:

            with sr.Microphone() as source:

                recognizer.adjust_for_ambient_noise(
                    source,
                    duration=0.5
                )

                audio = recognizer.listen(
                    source,
                    timeout=2,
                    phrase_time_limit=3
                )

            text = recognizer.recognize_google(audio)
            text = text.lower()

            print("\nVoice Command:", text)

            if "telugu" in text:

                selected_language = "Telugu"
                speech_language_code = "te"

                print("Language changed to Telugu")
                speak("తెలుగు ఎంపిక చేయబడింది")

            elif "hindi" in text:

                selected_language = "Hindi"
                speech_language_code = "hi"

                print("Language changed to Hindi")
                speak("हिंदी चुनी गई है")

            elif "tamil" in text:

                selected_language = "Tamil"
                speech_language_code = "ta"

                print("Language changed to Tamil")
                speak("தமிழ் தேர்ந்தெடுக்கப்பட்டது")

            elif "english" in text:

                selected_language = "English"
                speech_language_code = "en"

                print("Language changed to English")
                speak("English selected")

            elif "repeat" in text:

                if last_result:
                    speak(last_result)

            elif "exit" in text:

                speak("Closing application")
                running = False

        except:
            pass

# ==========================================
# MEDICINE ANALYSIS
# ==========================================

def analyze_medicine(frame):

    frame = cv2.resize(frame, (640, 480))

    image = Image.fromarray(
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            f"""
            Identify this medicine.

            Return the answer ONLY in {selected_language} language.

            Format:

            Medicine Name:
            Uses:
            Warning:

            Keep answer under 40 words.
            """,
            image
        ]
    )

    return response.text

# ==========================================
# CAMERA
# ==========================================

def open_camera():

    backends = []

    if hasattr(cv2, "CAP_DSHOW"):
        backends.append(cv2.CAP_DSHOW)

    if hasattr(cv2, "CAP_MSMF"):
        backends.append(cv2.CAP_MSMF)

    backends.append(cv2.CAP_ANY)

    for backend in backends:

        for index in range(3):

            cap = cv2.VideoCapture(index, backend)

            if cap.isOpened():

                cap.set(
                    cv2.CAP_PROP_FRAME_WIDTH,
                    640
                )

                cap.set(
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    480
                )

                return cap

            cap.release()

    return None

# ==========================================
# START VOICE THREAD
# ==========================================

threading.Thread(
    target=voice_command_listener,
    daemon=True
).start()

# ==========================================
# START CAMERA
# ==========================================

cap = open_camera()

if cap is None or not cap.isOpened():

    print("Camera not found.")
    exit()

print("\n====================================")
print("Medical Strip Identification System")
print("====================================")
print("Voice Commands:")
print("English")
print("Hindi")
print("Telugu")
print("Tamil")
print("Repeat")
print("Exit")
print("------------------------------------")
print("Press SPACE to identify medicine")
print("Press Q to quit")
print("====================================")

while running:

    ret, frame = cap.read()

    if not ret:

        time.sleep(0.2)
        continue

    cv2.putText(
        frame,
        f"Language: {selected_language}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.imshow(
        "Medicine Identification",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == 32:

        try:

            print("\nAnalyzing medicine...")

            result = analyze_medicine(frame)

            last_result = result

            print("\nRESULT:")
            print(result)

            speak(result)

        except Exception as e:

            print("ERROR:", e)

    elif key == ord("q"):

        break

running = False

cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()
