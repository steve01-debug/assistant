import speech_recognition as sr
import threading

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
        """Starts the background thread to listen for the wake word."""
        if not self.is_listening:
            self.is_listening = True
            # Adjust for ambient noise once
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            print(f"\n[Voice Mode] EDITH is listening in the background. Say '{self.wake_word}' to wake her up.")
            print("\nKamu : ", end="", flush=True)

    def stop_listening(self):
        """Stops the background listening thread."""
        self.is_listening = False

    def _recognize_offline(self, audio, lang=None):
        # Uses faster-whisper which runs completely offline after downloading the tiny model once
        text = self.recognizer.recognize_faster_whisper(audio, language=lang, model="base")
        if isinstance(text, str):
            return text.strip()
        return ""

    def _listen_loop(self):
        while self.is_listening:
            try:
                with self.microphone as source:
                    # Listen for audio (short timeout so it can check is_listening flag)
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                # Attempt to recognize what was said
                try:
                    # Force language='id' for wake word detection since 'halo' is too short to auto-detect
                    text = self._recognize_offline(audio, lang="id").lower()
                    
                    if self.wake_word in text:
                        print(f"\n[Voice Mode] Wake word '{self.wake_word}' detected! Mendengarkan perintah...")
                        
                        if self.on_wake:
                            self.on_wake()
                        
                        # Listen for the actual command
                        with self.microphone as source:
                            command_audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                            
                        # Use auto-detect (lang=None) for the actual command so Russian/English/Indonesian works
                        command_text = self._recognize_offline(command_audio, lang=None)
                        if command_text:
                            print(f"\n[Voice Mode] Command received: {command_text}")
                            
                            if self.on_command:
                                self.on_command(command_text)
                            
                            print("\nKamu : ", end="", flush=True) # restore prompt
                        else:
                            print("\n[Voice Mode] Tidak mendengar perintah lanjutan. Kembali ke siaga.")
                            print("\nKamu : ", end="", flush=True)
                        
                except Exception as e:
                    if str(e).strip():
                        print(f"Debug STT Error: {e}")
                    pass
                    
            except sr.WaitTimeoutError:
                # No speech detected within timeout, continue looping
                pass
            except Exception as e:
                # pass silently for other microphone issues
                pass
