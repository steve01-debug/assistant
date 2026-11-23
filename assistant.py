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
            "\nKonteks Tambahan:"
            "\n- Anda memiliki tools untuk membuka aplikasi, mencari catatan, membaca dokumen, membuka URL, dan menulis file."
            "\n- Berikan respons dengan kepribadian dosen pembimbing: tajam mengevaluasi, jujur jika ada yang keliru, analogi sederhana, dan berikan solusi jelas."
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

        # 2. Susun pesan percakapan
        system_content = self._build_system_prompt()
        messages = [{"role": "system", "content": system_content}]
        
        # Tambahkan history terbaru (maksimal 4 interaksi terakhir agar konteks tetap cepat)
        for h in self.history[-4:]:
            messages.append(h)
            
        messages.append({"role": "user", "content": message})

        # 3. Minta Ollama mengevaluasi apakah ada tool call yang relevan
        print("Menganalisis permintaan...")
        msg = chat(messages)

        # 4. Jika model memilih tool_calls
        if msg.tool_calls:
            messages.append(msg)
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                args = tool_call.function.arguments or {}
                print(f"[Aksi] Menjalankan {func_name}({args})...")
                
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
            
            # Panggilan kedua untuk merangkum respons ke user setelah tool dijalankan
            final_stream = chat_stream(messages)
            chunks = []
            print("\nEDITH : ", end="", flush=True)
            for part in final_stream:
                delta = part.message.content
                if delta:
                    chunks.append(delta)
                    print(delta, end="", flush=True)
            print()
            full_reply = "".join(chunks)
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": full_reply})
            return "\x00" + full_reply

        # 5. Jika tidak ada tool call, stream jawaban biasa
        # Karena msg sudah didapat dari chat(), jika berisi konten langsung kita cetak / stream
        reply_text = msg.content or ""
        print(f"\nEDITH : {reply_text}")
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": reply_text})
        return "\x00" + reply_text
