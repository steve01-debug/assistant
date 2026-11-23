import speech_recognition as sr
import threading
import json

class VoiceAssistant:
    def __init__(self, wake_word="halo", on_command=None, on_wake=None):
        self.wake_word = wake_word.lower()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.listen_thread = None
        self.on_command = on_command
        self.on_wake = on_wake

    def start_listening(self):
        """Menjalankan background listener hemat daya untuk mendeteksi wake word."""
        if not self.is_listening:
            self.is_listening = True
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            print(f"\n[Voice Mode] EDITH aktif di latar belakang (hemat CPU). Katakan '{self.wake_word}' untuk memanggil.")
            print("\nKamu : ", end="", flush=True)

    def stop_listening(self):
        """Menghentikan thread listener suara."""
        self.is_listening = False

    def _detect_wake_word_lightweight(self, audio):
        """Deteksi wake word menggunakan Vosk (sangat hemat CPU) dengan fallback Whisper tiny."""
        try:
            # Gunakan recognize_vosk jika model vosk tersedia
            res_json = self.recognizer.recognize_vosk(audio)
            data = json.loads(res_json)
            text = data.get("text", "").lower()
            if self.wake_word in text:
                return True
        except Exception:
            # Fallback ke Faster-Whisper 'tiny' (sangat cepat & hemat dibanding 'base')
            try:
                text = self.recognizer.recognize_faster_whisper(audio, language="id", model="tiny")
                if isinstance(text, str) and self.wake_word in text.lower():
                    return True
            except Exception:
                pass
        return False

    def _recognize_command_precise(self, audio):
        """Transkripsi perintah lengkap dengan akurasi tinggi menggunakan Whisper."""
        try:
            text = self.recognizer.recognize_faster_whisper(audio, language=None, model="base")
            if isinstance(text, str):
                return text.strip()
        except Exception as e:
            print(f"\n[Voice STT Error] {e}")
        return ""

    def _listen_loop(self):
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Mendengarkan suara pendek (wake word)
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                # Cek wake word secara cepat dan ringan
                if self._detect_wake_word_lightweight(audio):
                    print(f"\n[Voice Mode] Wake word '{self.wake_word}' terdeteksi! Mendengarkan perintah...")
                    
                    if self.on_wake:
                        self.on_wake()
                    
                    # Rekam perintah lengkap
                    with self.microphone as source:
                        command_audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                        
                    command_text = self._recognize_command_precise(command_audio)
                    if command_text:
                        print(f"\n[Voice Mode] Perintah diterima: {command_text}")
                        if self.on_command:
                            self.on_command(command_text)
                        print("\nKamu : ", end="", flush=True)
                    else:
                        print("\n[Voice Mode] Perintah tidak terdengar jelas. Kembali ke siaga.")
                        print("\nKamu : ", end="", flush=True)
                        
            except sr.WaitTimeoutError:
                pass
            except Exception:
                pass
