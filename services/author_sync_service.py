import os
import config
from services.cloudinary_service import list_cloud_authors, download_raw_file, upload_raw_file

def sync_authors_from_cloud():
    """Pobiera autorów z Cloudinary do lokalnego folderu authors/."""
    print("🔄 Synchronizacja autorów z chmury...")
    os.makedirs(config.AUTHORS_DIR, exist_ok=True)
    
    cloud_resources = list_cloud_authors(folder="authors")
    download_count = 0
    
    for res in cloud_resources:
        public_id = res.get("public_id")
        # public_id to np. "authors/amara_kioni.json"
        filename = os.path.basename(public_id)
        local_path = os.path.join(config.AUTHORS_DIR, filename)
        
        if download_raw_file(public_id, local_path):
            download_count += 1
            
    print(f"✅ Zakończono synchronizację. Pobrano {download_count} profili.")

def sync_author_to_cloud(author_slug):
    """Wysyła lokalny plik JSON autora do chmury."""
    filename = f"{author_slug}.json"
    local_path = os.path.join(config.AUTHORS_DIR, filename)
    
    if os.path.exists(local_path):
        print(f"📤 Wysyłanie autora {author_slug} do chmury...")
        upload_raw_file(local_path, folder="authors")
    else:
        print(f"⚠️ Błąd: Nie znaleziono pliku lokalnego {local_path}")
