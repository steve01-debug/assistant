import os
import asyncio
import pygame
import edge_tts

# Inisialisasi mixer pygame untuk memutar audio
pygame.mixer.init()

# Menggunakan suara perempuan Indonesia dari Edge TTS
VOICE = "id-ID-GadisNeural"

def speak(text):
    """Speaks the given text using edge-tts (Online)."""
    if not text:
        return
    # Strip \x00 if it exists
    if text.startswith("\x00"):
        text = text[1:]
    
    # Remove some markdown characters that shouldn't be pronounced
    text = text.replace("*", "").replace("#", "")
    
    if not text.strip():
        return
        
    try:
        audio_file = "temp_response.mp3"
        
        # Fungsi async untuk men-generate suara
        async def _generate_speech():
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(audio_file)
            
        # Jalankan secara synchronous
        asyncio.run(_generate_speech())
        
        # Putar audionya menggunakan pygame
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # Tunggu sampai audionya selesai diputar
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # Unload file agar bisa dihapus
        pygame.mixer.music.unload()
        
        # Hapus file temporary
        try:
            os.remove(audio_file)
        except Exception:
            pass
            
    except Exception as e:
        print(f"\n[TTS Error]: {e}")
