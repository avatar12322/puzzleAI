import os
import json
import dataclasses
from flask import Blueprint, request, jsonify
import config
from models import load_author, Author, get_slug

authors_bp = Blueprint('authors_api', __name__)

@authors_bp.route("/api/author/<name>", methods=["GET"])
def api_get_author(name):
    """Pobiera dane autora w formacie JSON."""
    try:
        author = load_author(name)
        return jsonify(dataclasses.asdict(author))
    except FileNotFoundError:
        return jsonify({"error": "Autor nie znaleziony"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@authors_bp.route("/api/author/<name>", methods=["POST"])
def api_save_author(name):
    """Zapisuje zmienione dane autora."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Brak danych"}), 400
            
        author = Author(**data)
        new_slug = author.slug
        filepath = os.path.join(config.AUTHORS_DIR, f"{new_slug}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Obsługa zmiany nazwy (przenoszenie plików)
        old_slug = get_slug(name)
        if old_slug and old_slug != new_slug:
            old_filepath = os.path.join(config.AUTHORS_DIR, f"{old_slug}.json")
            if os.path.exists(old_filepath):
                os.remove(old_filepath)
            
            old_output_dir = os.path.join(config.OUTPUT_DIR, old_slug)
            new_output_dir = os.path.join(config.OUTPUT_DIR, new_slug)
            
            if os.path.exists(old_output_dir):
                if os.path.exists(new_output_dir):
                    import shutil
                    for f in os.listdir(old_output_dir):
                        shutil.move(os.path.join(old_output_dir, f), os.path.join(new_output_dir, f))
                    os.rmdir(old_output_dir)
                else:
                    os.rename(old_output_dir, new_output_dir)
            
        return jsonify({"success": True, "slug": new_slug, "name": author.name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@authors_bp.route("/api/author/<name>", methods=["DELETE"])
def api_delete_author(name):
    """Usuwa autora (plik JSON)."""
    try:
        slug = get_slug(name)
        filepath = os.path.join(config.AUTHORS_DIR, f"{slug}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"success": True})
        return jsonify({"error": "Autor nie znaleziony"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
