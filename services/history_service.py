import os
import config

def get_history():
    """Zwraca historię obrazów, filtrując zbędne pliki PNG i parując oryginały JPG z miniaturami."""
    history = []
    
    # 1. Pobieranie z Cloudinary
    try:
        from services.cloudinary_service import cloudinary
        resources = cloudinary.api.resources(
            type="upload",
            prefix="puzzle_ai/",
            max_results=500,
            metadata=True,
            context=True
        ).get("resources", [])
        
        # Mapa wszystkich plików (public_id -> secure_url)
        all_urls = {res['public_id']: res['secure_url'] for res in resources}
        
        for res in resources:
            public_id = res.get("public_id")
            full_filename = os.path.basename(public_id)
            
            # FILTRY:
            # 1. Ignorujemy miniatury jako główne wpisy
            if "_preview" in full_filename:
                continue
            
            # 2. Ignorujemy pliki PNG jako główne wpisy (użytkownik chce tylko JPG jako główne)
            if full_filename.lower().endswith('.png'):
                continue

            parts = public_id.split('/')
            if len(parts) >= 3:
                author_slug = parts[1]
                filename = parts[2]
                url = res.get("secure_url")
                
                # Pobieramy koszt z metadanych lub kontekstu
                context = res.get("context", {}).get("custom", {})
                cost = context.get("cost")
                if not cost:
                    cost = res.get("context", {}).get("cost")

                # Szukamy odpowiadającego mu preview
                base_name = os.path.splitext(filename)[0]
                preview_id = f"puzzle_ai/{author_slug}/{base_name}_pixel_preview"
                preview_url = all_urls.get(preview_id)

                from datetime import datetime, timedelta
                created_at_utc = res.get("created_at", "")
                created_at_local = ""
                if created_at_utc:
                    dt = datetime.strptime(created_at_utc, "%Y-%m-%dT%H:%M:%SZ")
                    created_at_local = (dt + timedelta(hours=2)).strftime("%d.%m %H:%M")

                history.append({
                    "id": filename,
                    "title": base_name.replace('_', ' '),
                    "model": "Gemini (Cloud)",
                    "url": url,
                    "preview_url": preview_url,
                    "author_slug": author_slug,
                    "created_at": created_at_local,
                    "cost": float(cost) if cost else None
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
            # Pokazujemy tylko JPG jako główne
            if filename.lower().endswith('.jpg') and "_preview" not in filename:
                path = os.path.join(author_path, filename)
                base_name = os.path.splitext(filename)[0]
                preview_url = None
                
                # Szukamy lokalnego preview
                preview_filename = f"{base_name}_pixel_preview.png"
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
