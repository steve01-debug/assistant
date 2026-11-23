import os
import subprocess
import webbrowser
from pathlib import Path
from path_resolver import find_file_fuzzy, find_folder_fuzzy, find_application, parse_path_or_url
import memory

ALLOWED_ACTIONS = {"filesystem", "application", "writer", "browser", "memory"}
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


def list_directory(path: str) -> str:
    """Melihat daftar isi file dan folder dalam sebuah direktori.
    Args:
        path: Nama atau path folder yang ingin dilihat.
    """
    resolved_path = find_folder_fuzzy(path) or path
    require_permission(f"Melihat isi folder {resolved_path}", action_type="filesystem")
    try:
        items = os.listdir(resolved_path)
        return "\n".join(items) if items else "Folder kosong."
    except Exception as e:
        return f"Gagal melihat folder: {e}"


def read_file(path: str) -> str:
    """Membaca isi teks dari dokumen, kode sumber, atau file catatan.
    Args:
        path: Nama atau path file yang ingin dibaca.
    """
    resolved_path = path if os.path.exists(path) else (find_file_fuzzy(path) or path)
    if not os.path.exists(resolved_path):
        return f"File tidak ditemukan: {path}."
    require_permission(f"Membaca file {resolved_path}", action_type="filesystem")
    
    file_ext = os.path.splitext(resolved_path)[1].lower()
    binary_extensions = {
        '.xlsx', '.xls', '.pdf', '.zip', '.exe', '.dll', '.bin',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.csv'
    }
    
    if file_ext in binary_extensions:
        return open_file_default(resolved_path)
    
    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(resolved_path, "r", encoding="latin-1") as f:
                return f.read()
        except Exception as e:
            return f"Tidak bisa membaca file: {str(e)}"


def open_file_default(path: str) -> str:
    """Membuka file dengan aplikasi default sistem (misal PDF di Acrobat/Edge, Word di MS Word, Excel).
    Args:
        path: Nama atau path file yang ingin dibuka.
    """
    resolved_path = path if os.path.exists(path) else (find_file_fuzzy(path) or path)
    if not os.path.exists(resolved_path):
        return f"File tidak ditemukan: {path}."
    require_permission(f"Membuka file {resolved_path}", action_type="filesystem")
    
    try:
        zone_identifier = f"{resolved_path}:Zone.Identifier"
        if os.path.exists(zone_identifier):
            try:
                os.remove(zone_identifier)
            except Exception:
                pass

        subprocess.Popen(
            f'start "" "{resolved_path}"', 
            shell=True, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        return f"Membuka file {os.path.basename(resolved_path)}..."
    except Exception as e:
        return f"Tidak bisa membuka file: {str(e)}"


def write_file(path: str, content: str) -> str:
    """Membuat file baru atau menimpa file dengan teks/catatan baru.
    Args:
        path: Lokasi atau nama file tujuan.
        content: Isi teks yang ingin ditulis ke dalam file.
    """
    resolved_path = path if os.path.isabs(path) else (find_file_fuzzy(path) or path)
    require_permission(f"Menulis ke file {resolved_path}", action_type="filesystem")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Berhasil disimpan di {path}"


def append_file(path: str, content: str) -> str:
    """Menambahkan teks ke baris akhir file yang sudah ada.
    Args:
        path: Lokasi atau nama file.
        content: Teks tambahan yang ingin disematkan ke akhir file.
    """
    resolved_path = path if os.path.exists(path) else (find_file_fuzzy(path) or path)
    require_permission(f"Menambahkan teks ke file {resolved_path}", action_type="filesystem")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + content)
    return f"Berhasil menambahkan isi ke {path}"


def open_app(app_name: str) -> str:
    """Membuka aplikasi desktop di sistem (misal: Word, Notepad, VS Code, Chrome, Spotify, Calculator).
    Args:
        app_name: Nama aplikasi yang ingin dibuka.
    """
    resolved_app = find_application(app_name) or app_name
    require_permission(f"Membuka aplikasi {resolved_app}", action_type="application")
    try:
        if os.name == 'nt':
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
        return f"Membuka aplikasi {resolved_app}"
    except Exception as exc:
        return f"Gagal membuka aplikasi: {exc}"


def open_browser(url: str) -> str:
    """Membuka situs web atau tautan di browser internet.
    Args:
        url: Alamat URL atau domain (misal: https://scholar.google.com, youtube.com).
    """
    require_permission(f"Membuka browser ke {url}", action_type="browser")
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Membuka {url}"


def save_thesis_note(title: str, content: str, category: str = "skripsi") -> str:
    """Menyimpan catatan riset skripsi, kutipan jurnal, metodologi, ide, atau saran dosen.
    Args:
        title: Judul atau ringkasan topik catatan.
        content: Detail isi catatan, argumen, atau kutipan.
        category: Kategori catatan (contoh: 'skripsi', 'jurnal', 'metode', 'bab1', 'ide').
    """
    return memory.save_thesis_note(title, content, category)


def search_thesis_notes(query: str) -> str:
    """Mencari catatan skripsi atau referensi yang pernah disimpan sebelumnya menggunakan kata kunci.
    Args:
        query: Kata kunci atau topik yang ingin dicari di memori skripsi.
    """
    notes = memory.search_thesis_notes(query, limit=5)
    if not notes:
        return f"Tidak ditemukan catatan skripsi yang cocok dengan '{query}'."
    output = [f"Ditemukan {len(notes)} catatan relevan:"]
    for title, content, cat, created in notes:
        output.append(f"\n[{cat.upper()}] {title} ({created}):\n{content}")
    return "\n".join(output)


# Tool registry yang akan diekspos langsung ke Ollama LLM
ALL_TOOLS = [
    open_app,
    open_browser,
    read_file,
    write_file,
    append_file,
    list_directory,
    save_thesis_note,
    search_thesis_notes
]
