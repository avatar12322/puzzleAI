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

    if not author_name:
        return jsonify({"error": "Wybierz autora"}), 400
    
    session_id = start_background_generation(author_name, count, use_gemini, use_flux, pixel_size)
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
