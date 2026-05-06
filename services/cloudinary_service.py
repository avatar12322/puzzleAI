import os
import cloudinary
import cloudinary.uploader
import config

# Konfiguracja Cloudinary
cloudinary.config(
    cloud_name=config.CLOUDINARY_CLOUD_NAME,
    api_key=config.CLOUDINARY_API_KEY,
    api_secret=config.CLOUDINARY_API_SECRET,
    secure=True
)

def upload_image(file_path, folder="puzzle_ai"):
    """Przesyła obraz do Cloudinary, zachowując pełną nazwę z rozszerzeniem."""
    try:
        # Używamy pełnej nazwy pliku jako public_id
        public_id = os.path.basename(file_path)
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            public_id=public_id,
            resource_type="image",
            overwrite=True
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Błąd Cloudinary Upload (Image): {e}")
        return None

def upload_raw_file(file_path, folder="authors"):
    """Przesyła plik tekstowy/JSON do Cloudinary jako zasób 'raw'."""
    try:
        # Używamy nazwy pliku jako public_id (bez rozszerzenia dla ładnego wyglądu w chmurze)
        public_id = os.path.basename(file_path)
        response = cloudinary.uploader.upload(
            file_path,
            folder=folder,
            public_id=public_id,
            resource_type="raw",
            overwrite=True
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Błąd Cloudinary Upload (Raw): {e}")
        return None

def list_cloud_authors(folder="authors"):
    """Pobiera listę plików JSON z folderu autorów w chmurze."""
    try:
        import cloudinary.api
        result = cloudinary.api.resources(
            type="upload",
            prefix=folder,
            resource_type="raw"
        )
        return result.get("resources", [])
    except Exception as e:
        print(f"Błąd Cloudinary List: {e}")
        return []

def download_raw_file(public_id, save_path):
    """Pobiera plik raw z Cloudinary i zapisuje go lokalnie."""
    try:
        import requests
        # Generujemy URL do zasobu raw
        url = cloudinary.utils.cloudinary_url(public_id, resource_type="raw")[0]
        r = requests.get(url)
        with open(save_path, 'wb') as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"Błąd Cloudinary Download: {e}")
        return False

def rename_cloud_folder(old_slug, new_slug):
    """Zmienia nazwę folderu autora w Cloudinary (Admin API)."""
    try:
        import cloudinary.api
        old_folder = f"puzzle_ai/{old_slug}"
        new_folder = f"puzzle_ai/{new_slug}"
        
        print(f"📡 Próba zmiany nazwy folderu w chmurze: {old_folder} -> {new_folder}")
        
        # Cloudinary API wymaga dokładnych ścieżek
        result = cloudinary.api.rename_folder(old_folder, new_folder)
        print(f"✅ Cloudinary: Folder zmieniony pomyślnie. Szczegóły: {result}")
        return True
    except Exception as e:
        print(f"⚠️ Błąd zmiany nazwy folderu w Cloudinary: {e}")
        # Jeśli folder nie istnieje, to technicznie nie jest to błąd blokujący aplikację
        return False

def delete_cloud_raw_file(public_id):
    """Usuwa plik raw (np. JSON autora) z Cloudinary."""
    try:
        # public_id powinien zawierać folder, np. "authors/stara_nazwa.json"
        print(f"🗑️ Usuwanie pliku z chmury: {public_id}")
        cloudinary.uploader.destroy(public_id, resource_type="raw")
        return True
    except Exception as e:
        print(f"⚠️ Błąd usuwania pliku z Cloudinary: {e}")
        return False
