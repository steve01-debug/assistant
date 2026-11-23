from ollama import Client  # pyright: ignore [missing-import]
from config import MODEL_NAME
from tools import ALL_TOOLS

import os

client = Client(host="http://localhost:11434")

# Disesuaikan untuk CPU Windows: gunakan 8 thread dan batasi num_predict agar respons cepat
STATIC_OPTIONS = {
    "num_predict": 150,
    "temperature": 0.3,
    "top_p": 0.9,
    "num_ctx": 1024,
    "num_thread": 8,
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
