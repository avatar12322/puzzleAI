import os
import queue
import threading
import time
import uuid

import config
from models import load_author
from core.prompt_engine import generate_puzzle_ideas
from core.image_generator import generate_image
from core.free_generator import generate_image_free
from core.pixel_converter import convert_to_pixel_art

from services.cloudinary_service import upload_image

# Globalne stany generowania (współdzielone między wątkami)
generation_events = {}
generation_results = {}

def calculate_generation_cost(input_tokens, output_tokens, mode, model_type='image'):
    """
    Oblicza szacunkowy koszt w PLN.
    mode: 'standard' lub 'batch'
    model_type: 'image' (Gemini 3 Pro) lub 'text' (Gemini 2.5 Flash)
    """
    USD_TO_PLN = 4.0
    is_batch = (mode == 'batch')
    multiplier = 0.5 if is_batch else 1.0
    
    if model_type == 'image':
        # Koszt obrazu 2K: $0.067
        base_cost_usd = 0.067 * multiplier
        # Tokeny dla obrazu są zazwyczaj wliczone w cenę jednostkową lub bardzo tanie
        return base_cost_usd * USD_TO_PLN
    else:
        # Koszt Gemini 2.5 Flash
        in_price = (0.15 / 1_000_000) * multiplier
        out_price = (1.25 / 1_000_000) * multiplier
        cost_usd = (input_tokens * in_price) + (output_tokens * out_price)
        return cost_usd * USD_TO_PLN


def _get_preview_path(pixel_path: str) -> str:
    """Zwraca ścieżkę do pliku preview na podstawie ścieżki pixel art."""
    base = os.path.splitext(pixel_path)[0]
    # pixel_converter zapisuje preview jako _pixel_preview.png
    # Obsługuje oba warianty nazewnictwa dla kompatybilności wstecznej
    new_style = base + "_preview.png"
    if base.endswith("_pixel"):
        new_style = base + "_preview.png"
    return new_style


def _upload_pixel_art(path: str, pixel_size: int, author_slug: str, label: str = "") -> str | None:
    """
    Konwertuje obraz do pixel art i uploaduje preview do Cloudinary.
    Zwraca URL preview lub None jeśli coś poszło nie tak.
    """
    print(f"DEBUG{label}: Start konwersji Pixel Art dla {path} (size={pixel_size})")
    pixel_path = convert_to_pixel_art(path, size=pixel_size, colors=16)

    # Zbuduj ścieżkę preview deterministycznie na podstawie tego co zwrócił konwerter
    base = os.path.splitext(pixel_path)[0]
    preview_path = base + "_preview.png"

    if os.path.exists(preview_path):
        print(f"DEBUG{label}: Wysyłam preview: {preview_path}")
        url = upload_image(preview_path, folder=f"puzzle_ai/{author_slug}")
        print(f"DEBUG{label}: Preview URL: {url}")
        return url
    else:
        print(f"DEBUG{label}: ⚠️ Nie znaleziono preview: {preview_path}")
        # Fallback — wyślij mały pixel art zamiast preview
        if os.path.exists(pixel_path) and pixel_path != path:
            print(f"DEBUG{label}: Fallback — wysyłam pixel_path: {pixel_path}")
            return upload_image(pixel_path, folder=f"puzzle_ai/{author_slug}")
    return None


def start_background_generation(author_name, count, use_gemini, use_flux, pixel_size, gen_mode="standard"):
    """Tworzy sesję i uruchamia wątek generowania."""
    session_id = str(uuid.uuid4())[:8]
    generation_events[session_id] = queue.Queue()
    generation_results[session_id] = []

    thread = threading.Thread(
        target=_run_generation_thread,
        args=(session_id, author_name, count, use_gemini, use_flux, pixel_size, gen_mode),
        daemon=True,
    )
    thread.start()
    return session_id


def start_manual_pixelation(author_name, file_storage, pixel_size):
    """Tworzy sesję dla ręcznie przesłanego obrazka i uruchamia przetwarzanie."""
    session_id = str(uuid.uuid4())[:8]
    generation_events[session_id] = queue.Queue()
    generation_results[session_id] = []

    thread = threading.Thread(
        target=_run_manual_pixelation_thread,
        args=(session_id, author_name, file_storage, pixel_size),
        daemon=True,
    )
    thread.start()
    return session_id


def _run_manual_pixelation_thread(session_id, author_name, file_storage, pixel_size):
    """Wątek dla ręcznego uploadu — zapisuje plik i opcjonalnie pixeluje."""
    q = generation_events[session_id]
    results = generation_results[session_id]

    try:
        author = load_author(author_name)
        q.put({"type": "status", "message": "Zapisywanie i wysyłka oryginału..."})

        output_dir = author.output_dir(config.OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = int(time.time())
        filename = f"manual_{timestamp}_{file_storage.filename}"
        path = os.path.join(output_dir, filename)
        file_storage.save(path)

        # Wysyłka oryginału do Cloudinary
        remote_url = upload_image(path, folder=f"puzzle_ai/{author.slug}")

        pixel_url = None
        if author.post_processing == "pixel_art_50x50":
            q.put({"type": "status", "message": f"Konwertuję do pixel art (size={pixel_size})..."})
            pixel_url = _upload_pixel_art(path, pixel_size, author.slug, label=" (MANUAL)")

        result = {
            "id": filename,
            "title": f"Ręczny upload: {file_storage.filename}",
            "model": "MANUAL",
            "url": remote_url or f"/output/{author.slug}/{filename}",
            "preview_url": pixel_url,
            "author_slug": author.slug,
            "index": 0,
        }
        results.append(result)
        q.put({"type": "image_ready", **result})
        q.put({"type": "done", "total_images": 1})

    except Exception as e:
        import traceback
        traceback.print_exc()
        q.put({"type": "error", "message": str(e)})
        q.put({"type": "done", "total_images": 0})


def _run_generation_thread(session_id, author_name, count, use_gemini, use_flux, pixel_size, gen_mode="standard"):
    """Wątek generowania — wysyła eventy przez kolejkę."""
    q = generation_events[session_id]
    results = generation_results[session_id]

    try:
        author = load_author(author_name)
        
        if gen_mode == "batch":
            # PRAWDZIWY TRYB BATCH: Wysyłamy do Google API
            q.put({"type": "status", "message": f"Przygotowywanie i wysyłka zadania Batch ({count} obrazków)..."})
            
            try:
                from services.batch_api_service import create_image_batch_job
                # Musimy wygenerować pomysły przed wysłaniem do Batch
                ideas = generate_puzzle_ideas(author, count, q)
                
                batch_job = create_image_batch_job(author.name, author.slug, ideas)
                
                q.put({"type": "status", "message": f"✅ Zadanie Batch utworzone: {batch_job.name}"})
                time.sleep(1)
                q.put({"type": "done", "total_images": 0})
                return
            except Exception as batch_err:
                print(f"❌ Błąd Batch API: {batch_err}")
                q.put({"type": "error", "message": f"Problem z Gemini: {str(batch_err)}"})
                q.put({"type": "done", "total_images": 0})
                return

        q.put({"type": "status", "message": f"Ładuję autora: {author.name}..."})

        # Przekazujemy 'q' również tutaj dla trybu Standard
        ideas = generate_puzzle_ideas(author, count, q)
        q.put({
            "type": "scenes_ready",
            "count": len(ideas),
            "scenes": [{"title": idea.title, "scene": idea.scene[:200]} for idea in ideas],
        })

        output_dir = author.output_dir(config.OUTPUT_DIR)
        total = len(ideas) * (int(use_gemini) + int(use_flux))
        current = 0
        is_compare = use_gemini and use_flux

        for i, idea in enumerate(ideas):
            full_prompt = idea.full_prompt(author.style_template)

            if author.post_processing == "pixel_art_50x50":
                full_prompt += "\nVisual hint: looks like a children coloring book icon, vector icon style"

            # === GEMINI ===
            if use_gemini:
                current += 1
                q.put({"type": "generating", "current": current, "total": total,
                       "title": idea.title, "model": "Gemini"})

                sub_dir = os.path.join(output_dir, "gemini") if is_compare else output_dir
                os.makedirs(sub_dir, exist_ok=True)
                filename = f"{i+1:03d}_{idea.filename}.jpg"
                path = os.path.join(sub_dir, filename)

                if generate_image(full_prompt, path):
                    q.put({"type": "status", "message": f"Przesyłam do chmury..."})
                    cost = calculate_generation_cost(0, 0, gen_mode, model_type='image')
                    remote_url = upload_image(path, folder=f"puzzle_ai/{author.slug}", metadata={"cost": round(cost, 2)})
                    print(f"DEBUG (Gemini): Oryginał: {remote_url}")

                    pixel_url = None
                    if author.post_processing == "pixel_art_50x50":
                        q.put({"type": "status", "message": f"Konwertuję do pixel art..."})
                        pixel_url = _upload_pixel_art(path, pixel_size, author.slug, label=" (Gemini)")

                    cost = calculate_generation_cost(0, 0, gen_mode, model_type='image')
                    result = {
                        "id": filename, "title": idea.title, 
                        "model": f"Gemini {'(Batch)' if gen_mode == 'batch' else ''}".strip(),
                        "url": remote_url or f"/output/{author.slug}/{filename}",
                        "preview_url": pixel_url,
                        "author_slug": author.slug, "index": i,
                        "cost": round(cost, 2)
                    }
                    results.append(result)
                    q.put({"type": "image_ready", **result})

            # === FLUX ===
            if use_flux:
                current += 1
                q.put({"type": "generating", "current": current, "total": total,
                       "title": idea.title, "model": "FLUX"})

                sub_dir = os.path.join(output_dir, "flux") if is_compare else output_dir
                os.makedirs(sub_dir, exist_ok=True)
                filename = f"{i+1:03d}_{idea.filename}_flux.jpg"
                path = os.path.join(sub_dir, filename)

                if generate_image_free(full_prompt, path):
                    q.put({"type": "status", "message": "Wysyłam oryginał do chmury..."})
                    remote_url = upload_image(path, folder=f"puzzle_ai/{author.slug}")
                    print(f"DEBUG (FLUX): Oryginał: {remote_url}")

                    pixel_url = None
                    if author.post_processing == "pixel_art_50x50":
                        q.put({"type": "status", "message": f"Konwertuję do pixel art..."})
                        pixel_url = _upload_pixel_art(path, pixel_size, author.slug, label=" (FLUX)")

                    result = {
                        "id": filename, "title": idea.title, 
                        "model": f"FLUX {'(Batch)' if gen_mode == 'batch' else ''}".strip(),
                        "url": remote_url or f"/output/{author.slug}/{filename}",
                        "preview_url": pixel_url,
                        "author_slug": author.slug, "index": i,
                    }
                    results.append(result)
                    q.put({"type": "image_ready", **result})

            if i < len(ideas) - 1:
                time.sleep(1)

        q.put({"type": "done", "total_images": len(results)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        q.put({"type": "error", "message": str(e)})
        q.put({"type": "done", "total_images": 0})