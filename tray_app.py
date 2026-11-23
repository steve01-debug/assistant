import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from PIL import Image, ImageDraw
import pystray
import os
import tts
from assistant import Assistant
from config import SYSTEM_PROMPT_FILE
from voice import VoiceAssistant
import memory


ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")
ICON_PNG_PATH = os.path.join(os.path.dirname(__file__), "icon.png")


def create_tray_icon_image():
    """Memuat icon kustom (icon.ico / icon.png) jika ada, atau buat icon default."""
    if os.path.exists(ICON_PNG_PATH):
        try:
            return Image.open(ICON_PNG_PATH)
        except Exception:
            pass
    if os.path.exists(ICON_PATH):
        try:
            return Image.open(ICON_PATH)
        except Exception:
            pass

    # Icon bawaan jika belum ada file gambar
    width = 64
    height = 64
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), fill=(24, 119, 242, 255), outline=(255, 255, 255, 255), width=2)
    draw.ellipse((20, 20, 44, 44), fill=(255, 255, 255, 220))
    return image


class GaladrielTrayApp:
    def __init__(self):
        # Inisialisasi Memori & Assistant
        memory.init_memory()
        with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        self.assistant = Assistant(system_prompt)

        # Inisialisasi Voice Assistant di latar belakang
        self.voice_assistant = VoiceAssistant(
            wake_word="halo",
            on_command=self.handle_voice_command,
            on_wake=self.handle_voice_wake
        )

        self.root = None
        self.tray_icon = None
        self.is_window_visible = False

    def handle_voice_command(self, text):
        if any(w in text.lower() for w in ["stand by", "standby", "keluar"]):
            tts.speak("Mode suara dinonaktifkan.")
            self.voice_assistant.stop_listening()
            return
        reply = self.assistant.ask(text)
        clean_reply = reply[1:] if reply.startswith("\x00") else reply
        if self.root and self.is_window_visible:
            self.root.after(0, lambda: self._append_chat("Kamu (Suara)", text))
            self.root.after(0, lambda: self._append_chat("Galadriel", clean_reply))
        tts.speak(clean_reply)

    def handle_voice_wake(self):
        tts.speak("Iya, saya mendengarkan.")

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("Galadriel - Personal AI Assistant")
        self.root.geometry("450x580")
        self.root.minsize(380, 480)

        # Pasang icon pada jendela popup chat jika file tersedia
        if os.path.exists(ICON_PATH):
            try:
                self.root.iconbitmap(ICON_PATH)
            except Exception:
                pass
        elif os.path.exists(ICON_PNG_PATH):
            try:
                icon_img = tk.PhotoImage(file=ICON_PNG_PATH)
                self.root.iconphoto(False, icon_img)
            except Exception:
                pass
        
        # Tema modern gelap (Dark Theme)
        bg_color = "#1E1E2E"
        card_bg = "#252538"
        fg_color = "#CDD6F4"
        accent_color = "#89B4FA"
        user_color = "#A6E3A1"

        self.root.configure(bg=bg_color)

        # Header Frame
        header = tk.Frame(self.root, bg=card_bg, height=50)
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        title_label = tk.Label(
            header,
            text="✨ Galadriel (EDITH)",
            font=("Segoe UI", 13, "bold"),
            bg=card_bg,
            fg=accent_color
        )
        title_label.pack(side="left", padx=12, pady=10)

        subtitle_label = tk.Label(
            header,
            text="Online • Mentor Mode",
            font=("Segoe UI", 9),
            bg=card_bg,
            fg="#A6ADC8"
        )
        subtitle_label.pack(side="right", padx=12, pady=10)

        # Chat Log
        self.chat_area = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            bg=card_bg,
            fg=fg_color,
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
            borderwidth=0,
            highlightthickness=0
        )
        self.chat_area.pack(fill="both", expand=True, padx=10, pady=5)
        self.chat_area.tag_config("user", foreground=user_color, font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("ai", foreground=accent_color, font=("Segoe UI", 10, "bold"))
        self.chat_area.tag_config("content", foreground=fg_color)
        self.chat_area.config(state="disabled")

        # Input Frame
        input_frame = tk.Frame(self.root, bg=bg_color)
        input_frame.pack(fill="x", padx=10, pady=10)

        self.input_entry = tk.Entry(
            input_frame,
            bg=card_bg,
            fg=fg_color,
            font=("Segoe UI", 11),
            insertbackground="white",
            borderwidth=1,
            relief="flat"
        )
        self.input_entry.pack(side="left", fill="both", expand=True, padx=(0, 8), ipady=6)
        self.input_entry.bind("<Return>", lambda event: self.send_message())

        send_btn = tk.Button(
            input_frame,
            text="Kirim",
            font=("Segoe UI", 10, "bold"),
            bg=accent_color,
            fg="#11111B",
            activebackground="#B4BEFE",
            borderwidth=0,
            padx=15,
            cursor="hand2",
            command=self.send_message
        )
        send_btn.pack(side="right", fill="y")

        # Saat tombol [X] jendela ditekan, jangan tutup proses, tapi sembunyikan ke Tray
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Mulai dalam keadaan tersembunyi
        self.root.withdraw()
        self.is_window_visible = False

    def _append_chat(self, sender, text):
        self.chat_area.config(state="normal")
        tag = "user" if "Kamu" in sender else "ai"
        self.chat_area.insert(tk.END, f"\n{sender}:\n", tag)
        self.chat_area.insert(tk.END, f"{text}\n", "content")
        self.chat_area.see(tk.END)
        self.chat_area.config(state="disabled")

    def send_message(self):
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, tk.END)
        self._append_chat("Kamu", text)

        # Jalankan inferensi di background thread agar UI tidak macet/freeze
        def _worker():
            try:
                reply = self.assistant.ask(text)
                clean_reply = reply[1:] if reply.startswith("\x00") else reply
                self.root.after(0, lambda: self._append_chat("Galadriel", clean_reply))
            except Exception as e:
                self.root.after(0, lambda: self._append_chat("Galadriel", f"Maaf terjadi kendala: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def show_window(self):
        if self.root:
            self.root.after(0, self._do_show)

    def _do_show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after_idle(self.root.attributes, "-topmost", False)
        self.input_entry.focus_set()
        self.is_window_visible = True

    def hide_window(self):
        if self.root:
            self.root.withdraw()
            self.is_window_visible = False

    def toggle_window(self):
        if self.is_window_visible:
            self.hide_window()
        else:
            self.show_window()

    def quit_app(self):
        self.voice_assistant.stop_listening()
        if self.tray_icon:
            self.tray_icon.stop()
        if self.root:
            self.root.after(0, self.root.destroy)

    def run_tray(self):
        image = create_tray_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Buka Galadriel", self.show_window, default=True),
            pystray.MenuItem("Mode Suara (Voice)", lambda: self.voice_assistant.start_listening()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Keluar", self.quit_app)
        )
        self.tray_icon = pystray.Icon("Galadriel", image, "Galadriel AI Assistant", menu)
        self.tray_icon.run()

    def start(self):
        # Jalankan system tray di background thread
        tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        tray_thread.start()

        # Bangun GUI di main thread (wajib untuk Tkinter di Windows)
        self.build_gui()
        self.root.mainloop()


if __name__ == "__main__":
    app = GaladrielTrayApp()
    app.start()

