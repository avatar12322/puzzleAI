import os
import config

def get_history():
    """Przeszukuje folder output i zbiera historię wygenerowanych obrazów."""
    history = []
    if not os.path.exists(config.OUTPUT_DIR):
        return []
    
    # Przeszukaj foldery autorów
    for author_slug in os.listdir(config.OUTPUT_DIR):
        author_path = os.path.join(config.OUTPUT_DIR, author_slug)
        if not os.path.isdir(author_path):
            continue
            
        # Sprawdź podfoldery gemini/flux lub pliki bezpośrednio w folderze autora
        subdirs = [os.path.join(author_path, d) for d in ["gemini", "flux"] if os.path.isdir(os.path.join(author_path, d))]
        subdirs.append(author_path) # Dodaj główny folder autora (dla starszych generacji)

        for current_dir in subdirs:
            if not os.path.exists(current_dir): continue
            
            # Określ model na podstawie nazwy folderu
            model_name = os.path.basename(current_dir).capitalize()
            if model_name.lower() == author_slug.lower():
                model_name = "AI" # Domyślny model jeśli plik jest w głównym folderze
                
            for f in os.listdir(current_dir):
                if f.endswith(".jpg"):
                    base_name = f.replace(".jpg", "")
                    # Sprawdź czy istnieje preview.png (wersja pixel art)
                    preview_f = f"{base_name}_preview.png"
                    preview_path = os.path.join(current_dir, preview_f)
                    
                    # Budowanie relatywnej ścieżki do /output/
                    rel_path = os.path.relpath(os.path.join(current_dir, f), config.OUTPUT_DIR).replace("\\", "/")
                    url = f"/output/{rel_path}"
                    
                    pixel_url = None
                    if os.path.exists(preview_path):
                        rel_pixel_path = os.path.relpath(preview_path, config.OUTPUT_DIR).replace("\\", "/")
                        pixel_url = f"/output/{rel_pixel_path}"
                    
                    history.append({
                        "id": f,
                        "title": base_name.split("_", 1)[-1] if "_" in base_name else base_name,
                        "model": model_name,
                        "url": url,
                        "preview_url": pixel_url,
                        "author_slug": author_slug,
                        "mtime": os.path.getmtime(os.path.join(current_dir, f))
                    })
                    
    # Sortuj od najnowszych
    history.sort(key=lambda x: x["mtime"], reverse=True)
    return history
