import os
import config

def get_history():
    """Zwraca historię obrazów, dbając o to, by oryginały były główne, a _preview były dodatkami."""
    history = []
    
    # 1. Pobieranie z Cloudinary
    try:
        from services.cloudinary_service import cloudinary
        resources = cloudinary.api.resources(
            type="upload",
            prefix="puzzle_ai/",
            max_results=500
        ).get("resources", [])
        
        # Mapa dla szybkiego szukania: klucz to nazwa pliku bez rozszerzenia
        all_urls = {res['public_id']: res['secure_url'] for res in resources}
        
        for res in resources:
            public_id = res.get("public_id")
            full_filename = os.path.basename(public_id) # np. "test.jpg" lub "test_preview.png"
            
            # Ignorujemy pliki preview jako główne wpisy
            if "_preview" in full_filename:
                continue
            
            parts = public_id.split('/')
            if len(parts) >= 3:
                author_slug = parts[1]
                filename = parts[2] # Nazwa pliku z rozszerzeniem
                url = res.get("secure_url")
                
                # Szukamy odpowiadającego mu preview
                # Próbujemy dopasować nazwę bazową + _preview.png
                base_name = os.path.splitext(filename)[0]
                preview_id = f"puzzle_ai/{author_slug}/{base_name}_preview.png"
                preview_url = all_urls.get(preview_id)

                history.append({
                    "id": filename,
                    "title": base_name.replace('_', ' '),
                    "model": "Cloud",
                    "url": url,
                    "preview_url": preview_url,
                    "author_slug": author_slug,
                    "created_at": res.get("created_at")
                })
        
        if history:
            return sorted(history, key=lambda x: x.get('created_at', ''), reverse=True)
            
    except Exception as e:
        print(f"⚠️ Cloudinary History Error: {e}. Przełączam na skanowanie lokalne.")

    # 2. FALLBACK: Skanowanie lokalne
    if not os.path.exists(config.OUTPUT_DIR):
        return []

    for author_slug in os.listdir(config.OUTPUT_DIR):
        author_path = os.path.join(config.OUTPUT_DIR, author_slug)
        if not os.path.isdir(author_path): continue
        
        for filename in os.listdir(author_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and "_preview" not in filename:
                path = os.path.join(author_path, filename)
                base_name = os.path.splitext(filename)[0]
                preview_url = None
                
                # Szukamy lokalnego preview
                preview_filename = f"{base_name}_preview.png"
                if os.path.exists(os.path.join(author_path, preview_filename)):
                    preview_url = f"/output/{author_slug}/{preview_filename}"
                
                history.append({
                    "id": filename,
                    "title": base_name.replace('_', ' '),
                    "model": "Local",
                    "url": f"/output/{author_slug}/{filename}",
                    "preview_url": preview_url,
                    "author_slug": author_slug,
                    "mtime": os.path.getmtime(path)
                })
    
    return sorted(history, key=lambda x: x.get('mtime', 0), reverse=True)
