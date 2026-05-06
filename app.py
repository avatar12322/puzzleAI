"""
Puzzle AI Agent — Aplikacja webowa (Flask)
Struktura modularna

Uruchom: python app.py
Otwórz: http://localhost:5000
"""
import os
from flask import Flask
import config

# Importuj Blueprinty
from routes.views import views_bp
from routes.authors import authors_bp
from routes.generation import generation_bp

def create_app():
    """Inicjalizacja i konfiguracja aplikacji."""
    app = Flask(__name__)
    
    # Rejestracja modułów
    app.register_blueprint(views_bp)
    app.register_blueprint(authors_bp)
    app.register_blueprint(generation_bp)
    
    return app

if __name__ == "__main__":
    # Upewnij się, że foldery istnieją
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.AUTHORS_DIR, exist_ok=True)
    
    app = create_app()
    
    print("\n  🧩 Puzzle AI Agent — Web App (Modular)")
    print("  Otwórz: http://localhost:5000\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
