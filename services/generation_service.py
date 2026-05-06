import os
import json
import queue
import threading
import time
import uuid

import config
from models import load_author
from prompt_engine import generate_puzzle_ideas
from image_generator import generate_image
from free_generator import generate_image_free
from pixel_converter import convert_to_pixel_art

from services.cloudinary_service import upload_image

# Globalne stany generowania (współdzielone między wątkami)
generation_events = {}
generation_results = {}

def start_background_generation(author_name, count, use_gemini, use_flux, pixel_size):
    """Tworzy sesję i uruchamia wątek generowania."""
    session_id = str(uuid.uuid4())[:8]
    generation_events[session_id] = queue.Queue()
    generation_results[session_id] = []

    thread = threading.Thread(
        target=_run_generation_thread,
        args=(session_id, author_name, count, use_gemini, use_flux, pixel_size),
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
            q.put({"type": "status", "message": f"Konwertuję i wysyłam pixel art..."})
            pixel_path = convert_to_pixel_art(path, size=pixel_size, colors=16)
            pixel_url = upload_image(pixel_path, folder=f"puzzle_ai/{author.slug}")

        result = {
            "id": filename,
            "title": f"Ręczny upload: {file_storage.filename}",
            "model": "MANUAL",
            "url": remote_url or f"/output/{author.slug}/{filename}",
            "preview_url": pixel_url,
            "author_slug": author.slug,
            "index": 0
        }
        results.append(result)
        q.put({"type": "image_ready", **result})
        q.put({"type": "done", "total_images": 1})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        q.put({"type": "error", "message": str(e)})
        q.put({"type": "done", "total_images": 0})

def _run_generation_thread(session_id, author_name, count, use_gemini, use_flux, pixel_size):
    """Wątek generowania — wysyła eventy przez kolejkę."""
    q = generation_events[session_id]
    results = generation_results[session_id]

    try:
        author = load_author(author_name)
        q.put({"type": "status", "message": f"Ładuję autora: {author.name}..."})
        
        ideas = generate_puzzle_ideas(author, count)
        q.put({"type": "scenes_ready", "count": len(ideas),
               "scenes": [{"title": idea.title, "scene": idea.scene[:200]} for idea in ideas]})

        output_dir = author.output_dir(config.OUTPUT_DIR)
        total = len(ideas) * (int(use_gemini) + int(use_flux))
        current = 0

        for i, idea in enumerate(ideas):
            full_prompt = idea.full_prompt(author.style_template)
            
            if author.post_processing == "pixel_art_50x50":
                full_prompt += "\nVisual hint: looks like a children coloring book icon, vector icon style"

            # Gemini
            if use_gemini:
                current += 1
                q.put({"type": "generating", "current": current, "total": total, "title": idea.title, "model": "Gemini"})
                
                if use_gemini and use_flux:
                    gemini_dir = os.path.join(output_dir, "gemini")
                    os.makedirs(gemini_dir, exist_ok=True)
                    filename = f"{i+1:03d}_{idea.filename}.jpg"
                    path = os.path.join(gemini_dir, filename)
                else:
                    os.makedirs(output_dir, exist_ok=True)
                    filename = f"{i+1:03d}_{idea.filename}.jpg"
                    path = os.path.join(output_dir, filename)

                if generate_image(full_prompt, path):
                    q.put({"type": "status", "message": "Wysyłam do chmury..."})
                    remote_url = upload_image(path, folder=f"puzzle_ai/{author.slug}")
                    
                    pixel_url = None
                    if author.post_processing == "pixel_art_50x50":
                        pixel_path = convert_to_pixel_art(path, size=pixel_size, colors=16)
                        pixel_url = upload_image(pixel_path, folder=f"puzzle_ai/{author.slug}")

                    result = {
                        "id": filename, "title": idea.title, "model": "Gemini", 
                        "url": remote_url or f"/output/{author.slug}/{filename}", 
                        "preview_url": pixel_url, 
                        "author_slug": author.slug, "index": i
                    }
                    results.append(result)
                    q.put({"type": "image_ready", **result})

            # FLUX
            if use_flux:
                current += 1
                q.put({"type": "generating", "current": current, "total": total, "title": idea.title, "model": "FLUX"})
                
                os.makedirs(output_dir, exist_ok=True)
                filename = f"{i+1:03d}_{idea.filename}_flux.jpg"
                path = os.path.join(output_dir, filename)

                if generate_image_free(full_prompt, path):
                    q.put({"type": "status", "message": "Wysyłam do chmury..."})
                    remote_url = upload_image(path, folder=f"puzzle_ai/{author.slug}")
                    
                    pixel_url = None
                    if author.post_processing == "pixel_art_50x50":
                        pixel_path = convert_to_pixel_art(path, size=pixel_size, colors=16)
                        pixel_url = upload_image(pixel_path, folder=f"puzzle_ai/{author.slug}")
                            
                    result = {
                        "id": filename, "title": idea.title, "model": "FLUX", 
                        "url": remote_url or f"/output/{author.slug}/{filename}", 
                        "preview_url": pixel_url,
                        "author_slug": author.slug, "index": i
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
