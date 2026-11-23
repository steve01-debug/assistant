
from ollama import Client  # pyright: ignore [missing-import]
from config import MODEL_NAME

client = Client(host="http://localhost:11434")

# Gunakan opsi statis untuk semua interaksi agar Ollama tidak perlu memuat ulang model
# Mengubah parameter num_ctx secara dinamis menyebabkan penundaan besar karena model harus di-reload.
STATIC_OPTIONS = {
    "num_predict": 300,
    "temperature": 0.2,
    "top_p": 0.9,
    "num_ctx": 2048,
    "repeat_penalty": 1.05
}


def chat(system_prompt, message, fast_mode=None):
    print("Menghubungi Ollama...")

    try:
        chunks = []
        stream = client.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt[:600]
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            stream=True,
            think=False,
            options=STATIC_OPTIONS
        )
        print("\nEDITH : ", end="", flush=True)
        for part in stream:
            delta = part["message"]["content"]
            if delta:
                chunks.append(delta)
                print(delta, end="", flush=True)

        print() # Newline after stream finishes
        
        # Kembalikan teks dengan prefix \x00 agar app.py tahu tidak perlu memprint ulang
        return "\x00" + "".join(chunks)
    except Exception as exc:
        raise RuntimeError(f"Gagal menghubungi Ollama: {exc}") from exc