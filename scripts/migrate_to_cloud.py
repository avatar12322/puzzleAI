import os
import time
import config
from services.cloudinary_service import upload_image, upload_raw_file

def migrate():
    print("🚀 Rozpoczynam migrację danych do Cloudinary...")

    # 1. Migracja Autorów
    print("\n--- 👥 Migracja Autorów ---")
    if os.path.exists(config.AUTHORS_DIR):
        for filename in os.listdir(config.AUTHORS_DIR):
            if filename.endswith(".json"):
                local_path = os.path.join(config.AUTHORS_DIR, filename)
                print(f"📤 Wysyłam autora: {filename}")
                upload_raw_file(local_path, folder="authors")

    # 2. Migracja Obrazków
    print("\n--- 🖼️ Migracja Obrazków ---")
    if os.path.exists(config.OUTPUT_DIR):
        for author_slug in os.listdir(config.OUTPUT_DIR):
            author_path = os.path.join(config.OUTPUT_DIR, author_slug)
            if not os.path.isdir(author_path): continue

            print(f"\n📂 Przetwarzam folder autora: {author_slug}")

            # Skanujemy pliki (również w podfolderach gemini/flux)
            for root, dirs, files in os.walk(author_path):
                for filename in files:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        local_path = os.path.join(root, filename)

                        # Określamy folder w Cloudinary (puzzle_ai/slug)
                        cloud_folder = f"puzzle_ai/{author_slug}"

                        print(f"  🖼️ Wysyłam: {filename}")
                        upload_image(local_path, folder=cloud_folder)

                        # Mała pauza, żeby nie przeciążyć API Cloudinary (opcjonalnie)
                        time.sleep(0.1)

    print("\n✅ Migracja zakończona! Odśwież swoją stronę na Renderze.")

if __name__ == "__main__":
    migrate()
