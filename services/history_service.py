import os
import config

def get_history():
    """Zwraca całą historię wygenerowanych obrazów, preferując Cloudinary."""
    history = []
    
    # 1. Próbujemy pobrać z Cloudinary
    try:
        from services.cloudinary_service import cloudinary
        # Pobieramy listę wszystkich obrazów z folderu puzzle_ai/
        # Ustawiamy max_results na 500, aby pobrać całą historię
        resources = cloudinary.api.resources(
            type="upload",
            prefix="puzzle_ai/",
            max_results=500
        ).get("resources", [])
        
        for res in resources:
            public_id = res.get("public_id")
            # public_id to np. "puzzle_ai/amara_kioni/manual_123_test"
            parts = public_id.split('/')
            if len(parts) >= 3:
                author_slug = parts[1]
                # Nazwa pliku z rozszerzeniem
                filename = os.path.basename(public_id) + "." + res.get("format", "jpg")
                url = res.get("secure_url")
                
                # Ignorujemy miniatury (preview) w głównej pętli
                if "_preview" in filename:
                    continue 

                history.append({
                    "id": filename,
                    "title": filename.replace('_', ' ').replace('.jpg', '').replace('.png', ''),
                    "model": "Cloud",
                    "url": url,
                    # Dla Cloudinary zakładamy, że preview ma podobną nazwę lub używamy transformacji
                    "preview_url": url.replace(filename, filename.replace(".", "_preview.")), 
                    "author_slug": author_slug,
                    "created_at": res.get("created_at")
                })
        
        if history:
            print(f"🌐 Wczytano {len(history)} obrazów z Cloudinary")
            # Sortujemy po dacie utworzenia z Cloudinary
            return sorted(history, key=lambda x: x.get('created_at', ''), reverse=True)
            
    except Exception as e:
        print(f"⚠️ Cloudinary History Error: {e}. Przełączam na skanowanie lokalne.")

    # 2. FALLBACK: Skanowanie lokalne (jeśli chmura pusta lub błąd)
    if not os.path.exists(config.OUTPUT_DIR):
        return []

    for author_slug in os.listdir(config.OUTPUT_DIR):
        author_path = os.path.join(config.OUTPUT_DIR, author_slug)
        if not os.path.isdir(author_path): continue
        
        for filename in os.listdir(author_path):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')) and "_preview" not in filename:
                path = os.path.join(author_path, filename)
                preview_url = None
                preview_filename = filename.replace('.jpg', '_preview.png').replace('.png', '_preview.png')
                if os.path.exists(os.path.join(author_path, preview_filename)):
                    preview_url = f"/output/{author_slug}/{preview_filename}"
                
                history.append({
                    "id": filename,
                    "title": filename.replace('_', ' ').replace('.jpg', '').replace('.png', ''),
                    "model": "Local",
                    "url": f"/output/{author_slug}/{filename}",
                    "preview_url": preview_url,
                    "author_slug": author_slug,
                    "mtime": os.path.getmtime(path)
                })
    
    return sorted(history, key=lambda x: x.get('mtime', 0), reverse=True)
