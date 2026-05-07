import json
import os
import time
from google import genai
from google.genai import types
import config

def get_client():
    """Inicjalizuje klienta Google GenAI."""
    return genai.Client(api_key=config.GEMINI_API_KEY)

def create_image_batch_job(author_name, author_slug, ideas, model_name="gemini-3-pro-image-preview"):
    """
    Tworzy zadanie batchowe dla zestawu pomysłów na puzzle.
    ideas: lista obiektów pomysłów (z promptami)
    """
    client = get_client()
    timestamp = int(time.time())
    file_name = f"batch_req_{author_slug}_{timestamp}.jsonl"
    file_path = os.path.join(config.BASE_DIR, "scratch", file_name)
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # 1. Przygotowanie pliku JSONL
    requests = []
    for i, idea in enumerate(ideas):
        full_prompt = idea.full_prompt("")
        
        # Tworzymy bezpieczny klucz z tytułu (max 64 znaki, tylko alfanumeryczne)
        safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in idea.title)
        key = f"{i+1:03d}_{safe_title}"[:64]
        
        req = {
            "key": key,
            "request": {
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generation_config": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "imageConfig": {
                        "aspectRatio": config.IMAGE_ASPECT_RATIO,
                        "imageSize": config.IMAGE_SIZE
                    }
                }
            }
        }
        requests.append(req)
        
    with open(file_path, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req) + "\n")
            
    # 2. Upload pliku do Google
    print(f"📦 Wysyłam plik batch do Google: {file_name}")
    uploaded_file = client.files.upload(
        file=file_path,
        config=types.UploadFileConfig(display_name=file_name, mime_type='application/jsonl')
    )
    
    # 3. Utworzenie zadania Batch
    print(f"🚀 Tworzę zadanie Batch w Google dla autora: {author_name}")
    batch_job = client.batches.create(
        model=model_name,
        src=uploaded_file.name,
        config={
            'display_name': f"Puzzles-{author_name}-{timestamp}",
        },
    )
    
    return batch_job

def list_batch_jobs():
    """Pobiera listę zadań z API Google i mapuje na nasz format UI."""
    client = get_client()
    try:
        google_jobs = client.batches.list()
        ui_jobs = []
        for job in google_jobs:
            # Mapowanie statusów Google na nasze statusy UI
            state = getattr(job.state, 'name', str(job.state)) if hasattr(job, 'state') else 'UNKNOWN'
            display_name = getattr(job, 'display_name', "AI Batch")
            
            status_map = {
                'JOB_STATE_PENDING': 'PENDING',
                'JOB_STATE_RUNNING': 'RUNNING',
                'JOB_STATE_SUCCEEDED': 'COMPLETED',
                'JOB_STATE_FAILED': 'FAILED',
                'JOB_STATE_CANCELLED': 'FAILED'
            }
            
            from datetime import timedelta
            created_at_local = (job.create_time + timedelta(hours=2)).strftime("%d.%m %H:%M") if hasattr(job, 'create_time') and job.create_time else "---"
            
            ui_jobs.append({
                "id": job.name,
                "author_name": display_name.split('-')[1] if '-' in display_name else display_name,
                "count": "Batch",
                "status": status_map.get(state, state),
                "progress": 100 if state == 'JOB_STATE_SUCCEEDED' else (50 if state == 'JOB_STATE_RUNNING' else 0),
                "created_at": created_at_local,
                "eta": "W toku" if state == 'JOB_STATE_RUNNING' else ("Gotowe" if state == 'JOB_STATE_SUCCEEDED' else "~24h")
            })
        return ui_jobs
    except Exception as e:
        print(f"⚠️ Błąd pobierania zadań z Google: {e}")
        return []

def get_job_details(job_name):
    """Pobiera szczegóły konkretnego zadania."""
    client = get_client()
    return client.batches.get(name=job_name)

def process_batch_results(job_name):
    """Pobiera wyniki zakończonego zadania i przetwarza obrazy."""
    import base64
    from services.cloudinary_service import upload_image
    from models import load_author
    
    client = get_client()
    job = client.batches.get(name=job_name)
    
    if job.state.name != 'JOB_STATE_SUCCEEDED':
        return {"error": f"Zadanie nie jest jeszcze zakończone (Status: {job.state.name})"}
        
    if not job.dest or not job.dest.file_name:
        return {"error": "Brak pliku wynikowego w zadaniu."}
        
    print(f"📥 Pobieram wyniki dla zadania: {job_name}")
    file_content_bytes = client.files.download(file=job.dest.file_name)
    file_content = file_content_bytes.decode('utf-8')
    
    # Wyciągamy nazwę autora z nazwy zadania (zapisaliśmy ją tam przy tworzeniu)
    display_name = getattr(job, 'display_name', "Unknown")
    author_name = display_name.split('-')[1] if '-' in display_name else "Unknown"
    author = load_author(author_name)
    output_dir = author.output_dir(config.OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    
    results_count = 0
    for i, line in enumerate(file_content.splitlines()):
        if not line: continue
        parsed = json.loads(line)
        
        if 'response' in parsed and parsed['response']:
            # Szukamy części IMAGE w odpowiedzi
            parts = parsed['response']['candidates'][0]['content']['parts']
            key = parsed.get('key', f'image_{i}')
            
            for part in parts:
                if 'inlineData' in part:
                    data = base64.b64decode(part['inlineData']['data'])
                    filename = f"{key}.jpg"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(data)
                    
                    # Wysyłka do Cloudinary
                    print(f"☁️ Wysyłam obraz {i} do Cloudinary...")
                    from services.generation_service import calculate_generation_cost
                    cost = calculate_generation_cost(0, 0, 'batch', model_type='image')
                    upload_image(filepath, folder=f"puzzle_ai/{author.slug}", metadata={"cost": round(cost, 2)})
                    results_count += 1
                    
        elif 'error' in parsed:
            print(f"⚠️ Błąd w linii {i}: {parsed['error']}")
            
    # Jeśli zaimportowano chociaż jeden obraz, usuwamy zadanie z listy Google
    if results_count > 0:
        print(f"🗑️ Usuwam zadanie {job_name} z kolejki Google...")
        client.batches.delete(name=job_name)
            
    return {"success": True, "count": results_count}
