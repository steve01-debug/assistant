import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
import speech_recognition as sr

def test_microphone():
    print("Mencari microphone...")
    recognizer = sr.Recognizer()
    
    mics = sr.Microphone.list_microphone_names()
    if not mics:
        print("❌ Tidak ada microphone yang terdeteksi.")
        return
        
    print(f"✅ Ditemukan {len(mics)} microphone.")
    print("\nMenguji microphone default...")
    
    try:
        with sr.Microphone() as source:
            print("⏳ Menyesuaikan dengan suara latar (harap diam selama 2 detik)...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            
            print("🎙️  SILAKAN BERBICARA SEKARANG! (Katakan kata 'Edith' atau lainnya selama 3 detik)")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            print("⏳ Sedang memproses suara Anda (OFFLINE dengan Faster-Whisper)...")
            # This will download the tiny model on first run if not cached
            text = recognizer.recognize_faster_whisper(audio, language="en", model="tiny")
            
            if isinstance(text, str):
                text = text.strip()
            
            if text:
                print(f"✅ Berhasil (Offline)! Anda mengatakan: '{text}'")
            else:
                print("❌ Suara tidak terdengar jelas.")
                
    except sr.WaitTimeoutError:
        print("❌ Tidak ada suara yang terdeteksi (Timeout).")
    except Exception as e:
        print(f"❌ Terjadi error: {e}")

if __name__ == "__main__":
    test_microphone()
