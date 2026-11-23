import speech_recognition as sr
print("Testing recognize_vosk")
r = sr.Recognizer()
try:
    with sr.Microphone() as source:
        print("Please say something...")
        audio = r.listen(source, timeout=3, phrase_time_limit=3)
    text = r.recognize_vosk(audio)
    print("Result:", text)
except Exception as e:
    print("Error:", e)

