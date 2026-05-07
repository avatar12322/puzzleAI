import json
from flask import Blueprint, request, jsonify, Response
from services.generation_service import start_background_generation, start_manual_pixelation, generation_events

generation_bp = Blueprint('generation_api', __name__)

@generation_bp.route("/upload", methods=["POST"])
def api_upload_manual():
    """Obsługuje ręczny upload obrazka do konwersji."""
    author_name = request.form.get("author")
    pixel_size = int(request.form.get("pixel_size", 50))
    file = request.files.get("file")

    if not author_name or not file:
        return jsonify({"error": "Brak autora lub pliku"}), 400
    
    session_id = start_manual_pixelation(author_name, file, pixel_size)
    return jsonify({"session_id": session_id})

@generation_bp.route("/generate", methods=["POST"])
def api_start_generation():
    """Rozpoczyna generowanie puzzli w tle."""
    data = request.json
    author_name = data.get("author")
    count = int(data.get("count", 3))
    use_gemini = data.get("gemini", True)
    use_flux = data.get("flux", False)
    pixel_size = int(data.get("pixel_size", 50))
    gen_mode = data.get("gen_mode", "standard")

    if not author_name:
        return jsonify({"error": "Wybierz autora"}), 400
    
    session_id = start_background_generation(author_name, count, use_gemini, use_flux, pixel_size, gen_mode)
    return jsonify({"session_id": session_id})

@generation_bp.route("/events/<session_id>")
def stream_events(session_id):
    """Server-Sent Events — streaming postępu generowania."""
    def event_stream():
        import queue
        q = generation_events.get(session_id)
        if not q:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Sesja nie istnieje'})}\n\n"
            return

        while True:
            try:
                event = q.get(timeout=120)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")

@generation_bp.route("/api/download-zip", methods=["POST"])
def api_download_zip():
    """Generuje URL do paczki ZIP."""
    data = request.json
    public_ids = data.get("public_ids", [])
    author_slug = data.get("author_slug", "collection")
    
    if not public_ids:
        return jsonify({"error": "Nie wybrano żadnych obrazków"}), 400
    
    from services.cloudinary_service import get_zip_url
    zip_url = get_zip_url(public_ids, filename=f"{author_slug}_puzzles")
    
    if not zip_url:
        return jsonify({"error": "Błąd generowania paczki ZIP"}), 500
        
    return jsonify({"url": zip_url})

@generation_bp.route("/api/batch-jobs", methods=["GET"])
def api_batch_jobs():
    """Zwraca listę realnych zadań Batch pobranych z Google API."""
    try:
        from services.batch_api_service import list_batch_jobs
        jobs = list_batch_jobs()
        return jsonify(jobs)
    except Exception as e:
        print(f"⚠️ Błąd pobierania zadań z Google: {e}")
        return jsonify([])

@generation_bp.route("/api/batch-results/<path:job_id>", methods=["POST"])
def api_batch_results(job_id):
    """Przetwarza wyniki zakończonego zadania batch w tle (kompatybilność z Render)."""
    import threading
    import queue
    import uuid
    from services.batch_api_service import process_batch_results
    from services.generation_service import generation_events, generation_results

    session_id = request.args.get('session_id') or str(uuid.uuid4())[:8]
    # Używamy Queue, aby SSE (EventSource) mogło poprawnie czytać dane
    generation_events[session_id] = queue.Queue()
    
    def run_import():
        q = generation_events[session_id]
        try:
            q.put({"type": "status", "message": "Rozpoczynam pobieranie obrazków z Google..."})
            result = process_batch_results(job_id)
            generation_results[session_id] = result
            q.put({"type": "done", "success": True, "count": result.get("count", 0), "message": f"Zaimportowano {result.get('count', 0)} obrazków!"})
        except Exception as e:
            q.put({"type": "error", "message": f"Błąd importu: {str(e)}"})

    threading.Thread(target=run_import).start()
    return jsonify({"session_id": session_id})

@generation_bp.route("/api/batch-retry/<path:job_id>", methods=["POST"])
def api_batch_retry(job_id):
    """Ponawia zadanie batch używając zapisanych pomysłów."""
    try:
        # job_id może zawierać 'batches/', wycinamy to
        clean_id = job_id.split('/')[-1]
        from services.batch_api_service import retry_batch_job
        new_job = retry_batch_job(clean_id)
        return jsonify({"success": True, "new_job_id": new_job.name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@generation_bp.route("/api/batch-jobs/<path:job_id>", methods=["GET"])
def api_get_batch_job(job_id):
    """Pobiera najświeższy status pojedynczego zadania."""
    from services.batch_api_service import get_job_details
    try:
        # Upewniamy się, że mamy pełną nazwę batches/ID
        full_name = job_id if job_id.startswith('batches/') else f"batches/{job_id}"
        job = get_job_details(full_name)
        
        # Mapujemy na nasz format UI
        from services.batch_api_service import list_batch_jobs
        all_jobs = list_batch_jobs() 
        for j in all_jobs:
            if j['id'] == full_name or j['id'].endswith(job_id):
                return jsonify(j)
        return jsonify({"error": "Zadanie nieznalezione"}), 404
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@generation_bp.route("/api/batch-jobs/<path:job_id>", methods=["DELETE"])
def api_delete_batch_job(job_id):
    """Anuluje zadanie batch."""
    from services.batch_api_service import cancel_batch_job
    success = cancel_batch_job(job_id)
    return jsonify({"success": success})
