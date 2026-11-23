import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from assistant import Assistant
from config import SYSTEM_PROMPT_FILE
from voice import VoiceAssistant
import memory
import sys
import tts

with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
    system_prompt = f.read()


memory.init_memory()


assistant = Assistant(system_prompt)

# Initialize Voice Assistant
def handle_voice_command(command_text):
    try:
        if any(word in command_text.lower() for word in ["stand by", "standby", "stand bye", "keluar"]):
            print("\nEDITH : Baik, saya keluar dari mode suara.")
            tts.speak("Baik, saya keluar dari mode suara.")
            voice_assistant.stop_listening()
            return

        reply = assistant.ask(command_text)
        if not reply.startswith("\x00"):
            print(f"\nEDITH : {reply}")
        tts.speak(reply)
    except Exception as exc:
        error_msg = "Maaf, saya tidak bisa menjawab saat ini."
        print(f"\nEDITH : {error_msg} {exc}")
        tts.speak(error_msg)

def handle_wake():
    reply = "Iya, saya mendengarkan."
    print(f"\nEDITH : {reply}")
    tts.speak(reply)

voice_assistant = VoiceAssistant(wake_word="halo", on_command=handle_voice_command, on_wake=handle_wake)


print("=" * 40)
print("      EDITH")
print("=" * 40)


try:
    while True:

        user = input("\nKamu : ")


        if user.lower() in ["exit", "quit"]:
            voice_assistant.stop_listening()
            break

        if not user.strip():
            continue
            
        if user.lower().strip() == "voice":
            voice_assistant.start_listening()
            continue


        try:
            lowered = user.lower().strip()

            if lowered.startswith("panggil saya"):
                name = user.split("panggil saya", 1)[1].strip()
                if name:
                    memory.remember("user_name", name)
                    print("\nEDITH : Oke, saya akan memanggil Anda", name)
                    continue
            if lowered in ["kamu siapa", "siapa kamu", "who are you", "what is your name", "как вас зовут"]:
                resp = "Saya adalah EDITH, maker saya adalah Fadhil dan nama panjang saya adalah Even Death, I'm The Hero"
                print(f"\nEDITH : {resp}")
                continue

            if lowered in ["siapa saya", "saya siapa", "siapa aku", "aku siapa", "nama saya siapa", "как меня зовут"]:
                name = memory.recall("user_name")
                if name:
                    print(f"\nEDITH : Anda adalah {name}")
                else:
                    print("\nEDITH : Saya belum tahu nama Anda")
                continue

            reply = assistant.ask(user)
            if reply.startswith("\x00"):
                pass
            else:
                print("\nEDITH :", reply)
                
        except Exception as exc:
            print(f"\nEDITH : Maaf, saya tidak bisa menjawab saat ini. {exc}")
            continue

except KeyboardInterrupt:
    voice_assistant.stop_listening()
    print("\n\nEDITH : до свиданья сэр!")
