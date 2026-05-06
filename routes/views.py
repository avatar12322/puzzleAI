from flask import Blueprint, render_template, send_from_directory
import config
from models import load_author, list_authors
from services.history_service import get_history

views_bp = Blueprint('views', __name__)

@views_bp.route("/")
def index():
    """Główna strona aplikacji."""
    authors_names = list_authors()
    authors_data = []
    author_name_map = {}
    
    for name in authors_names:
        try:
            author = load_author(name)
            authors_data.append(author)
            author_name_map[author.slug] = author.name
        except Exception:
            pass
            
    history = get_history()
    
    # Przygotuj metadane dla folderów
    folders_metadata = {}
    from collections import defaultdict
    grouped_history = defaultdict(list)
    for item in history:
        slug = item['author_slug']
        grouped_history[slug].append(item)
    
    for slug, images in grouped_history.items():
        folders_metadata[slug] = {
            "name": author_name_map.get(slug, slug.replace('_', ' ').title()),
            "count": len(images),
            "cover": images[0]['url'] if images else None
        }

    return render_template("index.html", 
                         authors=authors_data, 
                         history=grouped_history, 
                         folders=folders_metadata)

@views_bp.route("/output/<path:filepath>")
def serve_output(filepath):
    """Serwuje wygenerowane obrazki."""
    return send_from_directory(config.OUTPUT_DIR, filepath)
