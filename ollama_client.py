from ollama import Client  # pyright: ignore [missing-import]
from config import MODEL_NAME
from tools import ALL_TOOLS

client = Client(host="http://localhost:11434")

STATIC_OPTIONS = {
    "num_predict": 400,
    "temperature": 0.2,
    "top_p": 0.9,
    "num_ctx": 2048,
    "repeat_penalty": 1.05
}


def chat(messages, stream=True):
    """Kirim percakapan ke Ollama dengan dukungan tool-calling dan streaming."""
    try:
        # Panggilan pertama dengan tools untuk mendeteksi intent fungsi
        response = client.chat(
            model=MODEL_NAME,
            messages=messages,
            tools=ALL_TOOLS,
            stream=False,
            options=STATIC_OPTIONS
        )
        return response.message
    except Exception as exc:
        raise RuntimeError(f"Gagal menghubungi Ollama: {exc}") from exc


def chat_stream(messages):
    """Streaming respons biasa tanpa tools untuk efisiensi kecepatan token."""
    try:
        stream = client.chat(
            model=MODEL_NAME,
            messages=messages,
            stream=True,
            think=False,
            options=STATIC_OPTIONS
        )
        return stream
    except Exception as exc:
        raise RuntimeError(f"Gagal streaming Ollama: {exc}") from exc
