from ollama_client import chat
import memory
from tools import PermissionDeniedError
from modules.filesystem import list_directory, write_file, append_file, read_file, open_file_default
from modules.browser import open_browser
from modules.application import open_app
from path_resolver import parse_path_or_url


class Assistant:

    def __init__(self, system_prompt):
        self.system_prompt = system_prompt
        self.history = []
        self.typing_target = None

    def _build_prompt(self, message):
        name = memory.recall("user_name")
        system_prompt = self.system_prompt
        if name:
            system_prompt = (
                f"{self.system_prompt}\n\n"
                f"Catatan memori: nama pengguna saat ini adalah {name}."
            )
        return system_prompt[:900], message

    def _extract_target(self, message, lowered, prefixes):
        """Extract the target (filename, URL, etc.) after the command prefix."""
        for prefix in prefixes:
            if lowered.startswith(prefix):
                target = message[len(prefix):].strip()
                return target
        return None

    def _handle_tool_request(self, message):
        lowered = message.lower().strip()
        
        # Handle typing state first
        if self.typing_target is not None:
            if lowered in ["batal", "stop", "berhenti", "selesai menulis"]:
                self.typing_target = None
                return "Mode menulis dihentikan."
                
            import pyautogui
            import time
            import subprocess
            pyautogui.FAILSAFE = False
            
            # Activate the window using PowerShell
            ps_command = f"Add-Type -AssemblyName Microsoft.VisualBasic; [Microsoft.VisualBasic.Interaction]::AppActivate('{self.typing_target}')"
            subprocess.run(["powershell", "-command", ps_command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Beri waktu sedikit agar jendela benar-benar aktif
            time.sleep(0.5)
            
            try:
                pyautogui.typewrite(message + '\n', interval=0.02)
                target = self.typing_target
                return f"Teks berhasil ditulis ke {target}."
            except Exception as e:
                self.typing_target = None
                return f"Gagal menulis: {str(e)}"

        # Periksa apakah pengguna ingin masuk ke mode menulis
        if lowered.startswith("tulis di "):
            target = lowered[len("tulis di "):].strip()
            if target:
                # Memetakan nama umum ke nama eksekusi Windows agar selalu membuka aplikasi baru
                app_map = {
                    "word": "winword",
                    "microsoft word": "winword",
                    "excel": "excel",
                    "powerpoint": "powerpnt",
                    "notepad": "notepad",
                    "notes": "notepad",
                    "sticky notes": "stikynot"
                }
                exe_name = app_map.get(target, target)
                
                try:
                    import subprocess
                    import os
                    import time
                    
                    if exe_name == "notepad":
                        # Notepad Windows 11 sering me-restore sesi lama.
                        # Kita buat file kosong baru dengan nama unik agar ia membuka tab yang benar-benar bersih.
                        filename = f"Catatan_Baru_{int(time.time())}.txt"
                        filepath = os.path.join(os.path.expanduser("~"), "Documents", filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            pass
                        subprocess.Popen(f'start "" notepad "{filepath}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        # Gunakan 'start' agar Windows membuka instance/jendela BARU dari aplikasi tersebut
                        subprocess.Popen(f'start "" {exe_name}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                    self.typing_target = target
                    return f"Aplikasi baru '{target}' telah dibuka. Silakan ketik pesan yang ingin ditulis, atau ketik 'batal'."
                except Exception as e:
                    return f"Gagal membuka aplikasi {target}: {str(e)}"
            return "Sebutkan nama aplikasi tempat Anda ingin menulis (contoh: tulis di notepad)."

        if lowered.startswith("baca file") or lowered.startswith("baca "):
            target = self._extract_target(message, lowered, ["baca file ", "baca "])
            if not target:
                return "Saya butuh nama file yang ingin dibaca."
            try:
                return read_file(target)
            except PermissionDeniedError:
                return "Saya tidak jadi membaca file karena izin ditolak."

        if lowered.startswith("lihat folder") or lowered.startswith("lihat ") or lowered.startswith("buka folder"):
            target = self._extract_target(message, lowered, ["lihat folder ", "lihat ", "buka folder "])
            if not target:
                return "Saya butuh nama folder yang ingin dilihat."
            try:
                return "\n".join(list_directory(target))
            except PermissionDeniedError:
                return "Saya tidak jadi melihat folder karena izin ditolak."

        if lowered.startswith("buat file") or lowered.startswith("tulis file"):
            target = self._extract_target(message, lowered, ["buat file ", "tulis file "])
            if not target:
                return "Saya butuh nama file dan isi yang ingin ditulis."
            parts = target.split(" ", 1)
            if len(parts) < 2:
                return "Saya butuh isi untuk ditulis ke file."
            try:
                return write_file(parts[0], parts[1])
            except PermissionDeniedError:
                return "Saya tidak jadi menulis file karena izin ditolak."

        if lowered.startswith("buka "):
            # Tambahkan "buka file ", "buka aplikasi ", "buka gambar ", "buka video " dsb agar kata pengantar terhapus
            target = self._extract_target(message, lowered, ["buka file ", "buka folder ", "buka aplikasi ", "buka gambar ", "buka video ", "buka "])
            if not target:
                return "Saya butuh file, folder, aplikasi, atau URL yang ingin dibuka."
            
            # Hapus kata-kata akhir yang sering digunakan (seperti "dong", "ya", dll)
            if target.lower().endswith(" dong"):
                target = target[:-5].strip()
            elif target.lower().endswith(" ya"):
                target = target[:-3].strip()


            resolved = parse_path_or_url(target)

            if resolved["type"] == "url":
                try:
                    return open_browser(resolved["value"])
                except PermissionDeniedError:
                    return "Saya tidak jadi membuka browser karena akses browser dibatasi."

            elif resolved["type"] == "file":
                files = resolved["value"]
                if len(files) > 1:
                    import os
                    file_list = "\n".join([f"- {os.path.basename(f)}" for f in files])
                    return f"Ada beberapa file yang cocok:\n{file_list}\nPilih file beserta ekstensinya (contoh: buka {os.path.basename(files[0])})."
                elif len(files) == 1:
                    try:
                        return open_file_default(files[0])
                    except PermissionDeniedError:
                        return "Saya tidak jadi membuka file karena izin ditolak."
                else:
                    return f"Saya tidak bisa menemukan file {target}."

            elif resolved["type"] == "folder":
                try:
                    return "\n".join(list_directory(resolved["value"]))
                except PermissionDeniedError:
                    return "Saya tidak jadi membuka folder karena izin ditolak."

            elif resolved["type"] == "app":
                try:
                    return open_app(resolved["value"])
                except PermissionDeniedError:
                    return "Saya tidak jadi membuka aplikasi karena izin ditolak."

            else:
                return f"Saya tidak bisa menemukan {target}. Coba lagi dengan nama yang lebih jelas."

        if lowered.startswith("tulis ") or lowered.startswith("buat "):
            target = self._extract_target(message, lowered, ["tulis ", "buat "])
            if not target:
                return "Saya butuh target yang ingin ditulis."

            resolved = parse_path_or_url(target)

            if resolved["type"] == "file":
                content_start = message.find(target) + len(target)
                content = message[content_start:].strip() if content_start < len(message) else ""
                if not content:
                    return "Saya butuh isi yang ingin ditulis ke file."
                try:
                    return write_file(resolved["value"], content)
                except PermissionDeniedError:
                    return "Saya tidak jadi menulis file karena izin ditolak."

            elif resolved["type"] == "app":
                return f"Saya akan membuka {resolved['value']} untuk Anda."

        if any(token in lowered for token in ["login", "sign up", "signup", "telegram", "whatsapp"]):
            return "Aksi ini dibatasi. Saya hanya bisa membantu akses file, folder, aplikasi, dan menulis setelah Anda mengizinkan."

        # Fallback: Jika pengguna mengetik nama file/aplikasi tanpa kata awalan (contoh saat diminta memilih)
        if len(lowered.split()) <= 3:
            resolved = parse_path_or_url(message)
            if resolved["type"] == "file" and ("." in message or len(lowered.split()) == 1):
                files = resolved["value"]
                if len(files) > 1:
                    import os
                    file_list = "\n".join([f"- {os.path.basename(f)}" for f in files])
                    return f"Ada beberapa file yang cocok:\n{file_list}\nPilih file beserta ekstensinya (contoh: buka {os.path.basename(files[0])})."
                elif len(files) == 1:
                    try:
                        return open_file_default(files[0])
                    except PermissionDeniedError:
                        return "Saya tidak jadi membuka file karena izin ditolak."
            elif resolved["type"] == "app" and len(lowered.split()) == 1:
                try:
                    return open_app(resolved["value"])
                except PermissionDeniedError:
                    return "Saya tidak jadi membuka aplikasi karena izin ditolak."

        return None

    def ask(self, message):
        tool_result = self._handle_tool_request(message)
        if tool_result is not None:
            return tool_result

        system_prompt, user_message = self._build_prompt(message)
        response = chat(system_prompt, user_message, fast_mode=None)
        
        # Bersihkan marker streaming jika ada
        response_text = response[1:] if response.startswith("\x00") else response
        self.history.append({"role": "assistant", "content": response_text})
        
        return response