"""
Puzzle AI Agent — Konfiguracja
"""
import os
from dotenv import load_dotenv

load_dotenv()

# === API ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Brak klucza GEMINI_API_KEY! Ustaw go w pliku .env")

# === Modele Gemini ===
TEXT_MODEL = "gemini-2.5-flash"          # Do generowania promptów/scen
IMAGE_MODEL = "gemini-2.5-flash-preview-image-generation" 

# === Ścieżki ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTHORS_DIR = os.path.join(BASE_DIR, "authors")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# === Cloudinary ===
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "CLOUDINARY_API_SECRET")

# === Domyślne wartości ===
DEFAULT_COUNT = 10
IMAGE_FORMAT = "image/jpeg"
