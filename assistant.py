from ollama_client import chat, chat_stream
import memory
from tools import ALL_TOOLS, PermissionDeniedError, open_file_default, open_app, list_directory, open_browser, write_file, read_file
from path_resolver import parse_path_or_url

# Pemetaan tool name ke callable
TOOL_MAP = {func.__name__: func for func in ALL_TOOLS}


class Assistant:

    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.history = []
        self.typing_target = None

    def _build_system_prompt(self):
        name = memory.recall("user_name")
        prompt = self.system_prompt
        if name:
            prompt += f"\nCatatan memori: lawan bicara/mahasiswa Anda saat ini adalah {name}."
        prompt += (
            "\nPedoman Interaksi Penting:"
            "\n- Gunakan metode Sokratik ('grill-me'): ketika ada argumen/ide, tunjukkan celahnya dan lemparkan pertanyaan pancingan kritis terlebih dahulu agar lawan bicara berpikir, alih-alih langsung menyuapi solusi final."
            "\n- Nada: Dosen pembimbing senior yang tajam, faktual, mendidik, hangat, dan analogi sederhana."
            "\n- Anda memiliki tools untuk membuka aplikasi, mencari catatan, membaca dokumen, membuka URL, dan menulis file."
        )
        return prompt

    def _handle_typing_mode(self, message):
        lowered = message.lower().strip()
        if self.typing_target is not None:
            if lowered in ["batal", "stop", "berhenti", "selesai menulis"]:
                self.typing_target = None
                return "Mode menulis dihentikan."
                
            import pyautogui
            import time
            import subprocess
            pyautogui.FAILSAFE = False
            
            ps_command = f"Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::AppActivate('{self.typing_target}')"
            subprocess.run(["powershell", "-command", ps_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.4)
            
            try:
                pyautogui.typewrite(message + '\n', interval=0.02)
                return f"Teks berhasil ditulis ke {self.typing_target}."
            except Exception as e:
                self.typing_target = None
                return f"Gagal menulis: {str(e)}"

        if lowered.startswith("tulis di "):
            target = lowered[len("tulis di "):].strip()
            if target:
                app_map = {
                    "word": "winword",
                    "microsoft word": "winword",
                    "excel": "excel",
                    "powerpoint": "powerpnt",
                    "notepad": "notepad",
                    "notes": "notepad"
                }
                exe_name = app_map.get(target, target)
                import subprocess
                import os
                import time
                if exe_name == "notepad":
                    filename = f"Catatan_Baru_{int(time.time())}.txt"
                    filepath = os.path.join(os.path.expanduser("~"), "Documents", filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        pass
                    subprocess.Popen(f'start "" notepad "{filepath}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen(f'start "" {exe_name}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                self.typing_target = target
                return f"Aplikasi '{target}' telah dibuka. Silakan ketik teks yang ingin ditulis, atau ketik 'batal'."
        return None

    def ask(self, message):
        # 1. Cek mode mengetik aktif
        typing_resp = self._handle_typing_mode(message)
        if typing_resp is not None:
            return typing_resp

        lowered = message.lower().strip()

        # FAST-PATH: Pertanyaan identitas / sapaan umum langsung dijawab tanpa tool-calling schema
        if lowered in ["kamu siapa", "siapa kamu", "who are you", "what is your name", "halo", "hi", "hai"]:
            name = memory.recall("user_name")
            user_info = f", {name}" if name else ""
            reply_text = (
                f"Saya Galadriel (EDITH){user_info}. Rekan diskusi sekaligus dosen pembimbing dan pengujimu. "
                f"Saya di sini untuk mengevaluasi logikamu secara kritis, jujur apa adanya, dan membantumu menyelesaikan masalah secara terstruktur. "
                f"Ada ide atau bahasan yang mau kita uji sekarang?"
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply_text})
            return "\x00" + reply_text

        # 2. Susun pesan percakapan
        system_content = self._build_system_prompt()
        messages = [{"role": "system", "content": system_content}]
        
        # Tambahkan history terbaru (maksimal 2 interaksi terakhir agar inferensi CPU sangat ringan)
        for h in self.history[-2:]:
            messages.append(h)
            
        messages.append({"role": "user", "content": message})

        # Deteksi apakah pesan memerlukan tools (misal ada kata 'buka', 'baca', 'tulis', 'simpan', 'cari')
        tool_keywords = ["buka", "baca", "tulis", "simpan", "cari", "buat", "folder", "file", "http", ".com", "catatan", "aplikasi"]
        need_tools = any(kw in lowered for kw in tool_keywords)

        if need_tools:
            # Panggil dengan tool declaration
            msg = chat(messages)
            if msg.tool_calls:
                messages.append(msg)
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    args = tool_call.function.arguments or {}
                    if func_name in TOOL_MAP:
                        try:
                            result = str(TOOL_MAP[func_name](**args))
                        except PermissionDeniedError:
                            result = "Aksi dibatalkan karena izin ditolak oleh pengguna."
                        except Exception as e:
                            result = f"Error saat menjalankan {func_name}: {e}"
                    else:
                        result = f"Tool {func_name} tidak ditemukan."
                    
                    messages.append({
                        "role": "tool",
                        "content": result,
                    })
                
                # Stream ringkasan
                final_stream = chat_stream(messages)
                chunks = []
                for part in final_stream:
                    delta = part.message.content
                    if delta:
                        chunks.append(delta)
                full_reply = "".join(chunks)
                self.history.append({"role": "user", "content": message})
                self.history.append({"role": "assistant", "content": full_reply})
                return "\x00" + full_reply
            else:
                reply_text = msg.content or ""
                self.history.append({"role": "user", "content": message})
                self.history.append({"role": "assistant", "content": reply_text})
                return "\x00" + reply_text
        else:
            # Langsung streaming respons biasa (jauh lebih cepat, tidak butuh evaluasi JSON schema)
            stream = chat_stream(messages)
            chunks = []
            for part in stream:
                delta = part.message.content
                if delta:
                    chunks.append(delta)
            reply_text = "".join(chunks)
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply_text})
            return "\x00" + reply_text
