import os
import subprocess
import webbrowser
from pathlib import Path
from path_resolver import find_file_fuzzy, find_folder_fuzzy, find_application, parse_path_or_url

ALLOWED_ACTIONS = {"filesystem", "application", "writer", "browser"}
RESTRICTED_ACTIONS = {"login", "signup", "telegram", "whatsapp"}


class PermissionDeniedError(Exception):
    pass


class ToolController:
    def __init__(self):
        self.allowed = False
        self.pending_action = None

    def request_permission(self, action_description):
        self.pending_action = action_description
        print(f"\n[PERMISSION REQUIRED] {action_description}")
        print("Balas 'iya' untuk mengizinkan atau 'tidak' untuk menolak.")
        answer = input("Izinkan? ").strip().lower()
        if answer in {"iya", "yes", "y", "ok", "oke"}:
            self.allowed = True
            return True
        self.allowed = False
        return False

    def ensure_permission(self, action_description, action_type="filesystem"):
        if action_type in RESTRICTED_ACTIONS:
            raise PermissionDeniedError(f"Aksi {action_type} dibatasi dan tidak diizinkan secara otomatis")
        if not self.allowed:
            if not self.request_permission(action_description):
                raise PermissionDeniedError("Izin ditolak")
        return True

    def reset_permission(self):
        self.allowed = False
        self.pending_action = None


controller = ToolController()


def require_permission(action_description, action_type="filesystem"):
    return controller.ensure_permission(action_description, action_type=action_type)


def list_directory(path):
    resolved_path = find_folder_fuzzy(path) or path
    require_permission(f"Melihat isi folder {resolved_path}", action_type="filesystem")
    return os.listdir(resolved_path)


def read_file(path):
    resolved_path = path if os.path.exists(path) else (find_file_fuzzy(path) or path)
    if not os.path.exists(resolved_path):
        return f"File tidak ditemukan: {path}. Coba lagi dengan nama yang lebih jelas."
    require_permission(f"Membaca file {resolved_path}", action_type="filesystem")
    
    # Handle binary files (Excel, PDF, images, etc.)
    # Handle binary files (Excel, PDF, images, videos, etc.)
    file_ext = os.path.splitext(resolved_path)[1].lower()
    binary_extensions = {
        '.xlsx', '.xls', '.pdf', '.zip', '.exe', '.dll', '.bin',
        # Gambar
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        # Video
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
        # Data
        '.csv'
    }
    
    if file_ext in binary_extensions:
        # For binary files, open with default application instead of reading as text
        import subprocess
        try:
            subprocess.Popen(f'start "" "{resolved_path}"', shell=True)
            return f"Membuka file {os.path.basename(resolved_path)}..."
        except Exception as e:
            return f"Tidak bisa membuka file: {str(e)}"
    
    # For text files, read as text
    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        # If UTF-8 fails, try other encodings
        try:
            with open(resolved_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            return f"Tidak bisa membaca file (format tidak didukung): {str(e)}"

def open_file_default(path):
    resolved_path = path if os.path.exists(path) else (find_file_fuzzy(path) or path)
    if not os.path.exists(resolved_path):
        return f"File tidak ditemukan: {path}. Coba lagi dengan nama yang lebih jelas."
    require_permission(f"Membuka file {resolved_path}", action_type="filesystem")
    
    import subprocess
    try:
        # Hapus "Mark of the Web" (Zone.Identifier) secara otomatis
        # Ini mencegah Windows memunculkan peringatan keamanan "Is this file from a trusted source?"
        # untuk file-file yang didownload dari internet.
        zone_identifier = f"{resolved_path}:Zone.Identifier"
        if os.path.exists(zone_identifier):
            try:
                os.remove(zone_identifier)
            except Exception:
                pass

        # Gunakan subprocess Popen dengan DEVNULL agar output program (seperti CSV dump)
        # tidak bocor ke terminal dan merusak tampilan chat.
        subprocess.Popen(
            f'start "" "{resolved_path}"', 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        return f"Membuka file {os.path.basename(resolved_path)}..."
    except Exception as e:
        return f"Tidak bisa membuka file: {str(e)}"


def write_file(path, content):
    resolved_path = path if os.path.isabs(path) else (find_file_fuzzy(path) or path)
    require_permission(f"Menulis ke file {resolved_path}", action_type="filesystem")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Tersimpan di {path}"


def append_file(path, content):
    resolved_path = path if os.path.exists(path) else (find_file_fuzzy(path) or path)
    require_permission(f"Menambahkan teks ke file {resolved_path}", action_type="filesystem")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Berhasil menambahkan isi ke {path}"


def open_app(app_name):
    resolved_app = find_application(app_name) or app_name
    require_permission(f"Membuka aplikasi {resolved_app}", action_type="application")
    try:
        import subprocess
        
        if os.name == 'nt':
            # Gunakan 'start ""' untuk semua file di Windows agar 
            # aplikasi berjalan terpisah seolah di-klik ganda dari Explorer
            subprocess.Popen(
                f'start "" "{resolved_app}"', 
                shell=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                [resolved_app],
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
        return f"Membuka {resolved_app}"
    except Exception as exc:
        return f"Gagal membuka aplikasi: {exc}"


def open_browser(url):
    require_permission(f"Membuka browser ke {url}", action_type="browser")
    webbrowser.open(url)
    return f"Membuka {url}"


def run_command(command):
    require_permission(f"Menjalankan perintah {command}", action_type="filesystem")
    return subprocess.check_output(command, shell=True, text=True)
