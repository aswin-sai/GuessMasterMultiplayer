import tkinter as tk
from tkinter import ttk
from ttkbootstrap import Style
from PIL import Image, ImageTk
import requests
import qrcode
import io

def fetch_ngrok_url():
    try:
        resp = requests.get("https://guessmastermultiplayer.onrender.com:4040/api/tunnels", timeout=2)
        tunnels = resp.json().get("tunnels", [])
        for t in tunnels:
            if t.get("public_url", "").startswith("http"):
                return t["public_url"]
        return None
    except Exception:
        return None

def show_ngrok_qr():
    url = fetch_ngrok_url()
    if url:
        url_label.config(text=f"ngrok URL: {url}")
        qr_img = qrcode.make(url)
        buf = io.BytesIO()
        qr_img.save(buf, format='PNG')
        buf.seek(0)
        pil_img = Image.open(buf)
        pil_img = pil_img.resize((180, 180), Image.LANCZOS)  # Smaller QR for phone
        tk_img = ImageTk.PhotoImage(pil_img)
        qr_label.config(image=tk_img)
        qr_label.image = tk_img
    else:
        url_label.config(text="ngrok not running or no public URL found.")
        qr_label.config(image='')
        qr_label.image = None

root = tk.Tk()
root.title("ngrok QR Code")
root.geometry("320x420")  # Phone-sized window

style = Style("cosmo")
frame = ttk.Frame(root, padding=10)
frame.pack(fill="both", expand=True)

fetch_btn = ttk.Button(
    frame,
    text="Show ngrok Public URL QR",
    command=show_ngrok_qr,
    style="success.TButton"
)
fetch_btn.pack(pady=(10, 16), ipadx=10, ipady=8)

url_label = ttk.Label(
    frame,
    text="Click the button to fetch ngrok URL.",
    wraplength=260,
    font=("Arial", 12)
)
url_label.pack(pady=(0, 14))

qr_label = ttk.Label(frame)
qr_label.pack(pady=(0, 10))

root.mainloop()
