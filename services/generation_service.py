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
        q.put({"type": "status", "message": "Zapisywanie przesłanego pliku..."})
        
        output_dir = author.output_dir(config.OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        
        # Generuj nazwę pliku na podstawie daty/czasu
        timestamp = int(time.time())
        filename = f"manual_{timestamp}_{file_storage.filename}"
        path = os.path.join(output_dir, filename)
        
        # Zapisz oryginał
        file_storage.save(path)
        
        url_path = f"{author.slug}/{filename}"
        pixel_url = None
        
        # Jeśli autor ma włączony pixel art, konwertuj od razu
        if author.post_processing == "pixel_art_50x50":
            q.put({"type": "status", "message": f"Konwertuję do pixel art ({pixel_size}x{pixel_size})..."})
            pixel_path = convert_to_pixel_art(path, size=pixel_size, colors=16)
            preview_filename = os.path.basename(pixel_path).replace('.png', '_preview.png')
            pixel_url = f"/output/{author.slug}/{preview_filename}"

        result = {
            "id": filename,
            "title": f"Ręczny upload: {file_storage.filename}",
            "model": "MANUAL",
            "url": f"/output/{url_path}",
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
        # Załaduj autora
        author = load_author(author_name)
        q.put({"type": "status", "message": f"Ładuję autora: {author.name}..."})

        # Generuj sceny
        q.put({"type": "status", "message": f"Wymyślam {count} scen..."})
        ideas = generate_puzzle_ideas(author, count)
        q.put({"type": "scenes_ready", "count": len(ideas),
               "scenes": [{"title": idea.title, "scene": idea.scene[:200]} for idea in ideas]})

        # Generuj obrazy
        output_dir = author.output_dir(config.OUTPUT_DIR)
        total = len(ideas) * (int(use_gemini) + int(use_flux))
        current = 0

        for i, idea in enumerate(ideas):
            full_prompt = idea.full_prompt(author.style_template)
            
            # PRO TIPY dla pixel artu
            if author.post_processing == "pixel_art_50x50":
                if pixel_size <= 50:
                    full_prompt += "\nEXTREME SIMPLIFICATION: use only 2-3 large shapes, remove all small features"
                elif pixel_size <= 85:
                    full_prompt += "\nMODERATE DETAIL: allow simple features like eyes, ears, but keep shapes bold"
                else:
                    full_prompt += "\nSLIGHTLY MORE DETAIL: allow simple patterns, but still keep strong shapes"
                
                full_prompt += "\nVisual hint: looks like a children coloring book icon, vector icon style"

            # Model Gemini
            if use_gemini:
                current += 1
                q.put({"type": "generating", "current": current, "total": total,
                       "title": idea.title, "model": "Gemini"})

                if use_gemini and use_flux:
                    gemini_dir = os.path.join(output_dir, "gemini")
                    os.makedirs(gemini_dir, exist_ok=True)
                    filename = f"{i+1:03d}_{idea.filename}.jpg"
                    path = os.path.join(gemini_dir, filename)
                    url_path = f"{author.slug}/gemini/{filename}"
                else:
                    os.makedirs(output_dir, exist_ok=True)
                    filename = f"{i+1:03d}_{idea.filename}.jpg"
                    path = os.path.join(output_dir, filename)
                    url_path = f"{author.slug}/{filename}"

                if generate_image(full_prompt, path):
                    pixel_url = None
                    if author.post_processing == "pixel_art_50x50":
                        pixel_path = convert_to_pixel_art(path, size=pixel_size, colors=16)
                        preview_filename = os.path.basename(pixel_path).replace('.png', '_preview.png')
                        sub = "gemini/" if (use_gemini and use_flux) else ""
                        pixel_url = f"/output/{author.slug}/{sub}{preview_filename}"

                    result = {
                        "id": filename, "title": idea.title, "model": "Gemini", 
                        "url": f"/output/{url_path}", "preview_url": pixel_url, 
                        "author_slug": author.slug, "index": i
                    }
                    results.append(result)
                    q.put({"type": "image_ready", **result})

            # Model FLUX
            if use_flux:
                current += 1
                q.put({"type": "generating", "current": current, "total": total,
                       "title": idea.title, "model": "FLUX"})

                if use_gemini and use_flux:
                    flux_dir = os.path.join(output_dir, "flux")
                    os.makedirs(flux_dir, exist_ok=True)
                    filename = f"{i+1:03d}_{idea.filename}.jpg"
                    path = os.path.join(flux_dir, filename)
                    url_path = f"{author.slug}/flux/{filename}"
                else:
                    os.makedirs(output_dir, exist_ok=True)
                    filename = f"{i+1:03d}_{idea.filename}_flux.jpg"
                    path = os.path.join(output_dir, filename)
                    url_path = f"{author.slug}/{filename}"

                if generate_image_free(full_prompt, path):
                    pixel_url = None
                    if author.post_processing == "pixel_art_50x50":
                        pixel_path = convert_to_pixel_art(path, size=pixel_size, colors=16)
                        preview_filename = os.path.basename(pixel_path).replace('.png', '_preview.png')
                        sub = "flux/" if (use_gemini and use_flux) else ""
                        pixel_url = f"/output/{author.slug}/{sub}{preview_filename}"
                            
                    result = {
                        "id": filename, "title": idea.title, "model": "FLUX", 
                        "url": f"/output/{url_path}", "preview_url": pixel_url,
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
