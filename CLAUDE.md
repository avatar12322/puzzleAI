# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

Puzzle AI is a Flask web application that generates jigsaw puzzle illustrations using AI. Users pick an **author profile** (a creative persona with a defined visual style), specify a count, and the app generates scene descriptions via Gemini then renders images via Gemini Image or FLUX (Pollinations.ai). Results are stored in Cloudinary and displayed in a gallery.

## Running the App

```bash
# Install dependencies (Python 3.11.9)
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Run dev server
python app.py               # http://localhost:5000

# Run production server
gunicorn --worker-class gthread --threads 4 --timeout 120 "app:create_app()"

# CLI generation (standalone, no web server needed)
python generate.py --author "Eleanor Ashford" --count 5
python generate.py --list                          # list all authors
python generate.py --author "Captain Sky" --dry-run  # prompts only, no images
```

No build step, no test suite, no linter is configured.

## Architecture

### Generation Pipeline

```
Author profile (JSON) → Gemini 2.5 Flash generates scene descriptions (PuzzleIdea objects)
  → Image generator (Gemini Image or Pollinations.ai FLUX)
  → Optional: Pyxelate pixel art conversion
  → Cloudinary upload
  → SSE stream to browser
```

The entire pipeline runs in a **background daemon thread** per session. Progress events are pushed via a `queue.Queue` and consumed by a Server-Sent Events endpoint (`GET /events/<session_id>`). This is the mechanism that drives the real-time UI updates.

### Author Profiles

Each author is a JSON file in `authors/`. The schema (see `models.py` → `Author`) includes:
- `style_template` — frozen base style injected into every prompt
- `scene_instructions` — what kinds of scenes to generate
- `negative_prompts` — what to avoid
- `post_processing: "pixel_art_50x50"` — optional pixel art conversion trigger

Authors can be created/edited via the web UI or by directly editing JSON files. On startup, `author_sync_service.py` syncs local profiles with Cloudinary metadata.

### Two Image Generation Modes

| Mode | Service | Quality | Cost |
|---|---|---|---|
| Gemini | `core/image_generator.py` | High | Paid |
| FLUX (free) | `core/free_generator.py` | Good | Free (Pollinations.ai) |
| Google Batch API | `services/batch_api_service.py` | High | Cost-efficient async |

Batch API mode creates JSONL request files, submits them to Google, and polls for completion. Batch job state is tracked in `output/.batch_metadata/` and `output/.hidden_batches.json`.

### Key Config (`config.py`)

- `GEMINI_TEXT_MODEL` — Gemini 2.5 Flash (scene generation)
- `GEMINI_IMAGE_MODEL` — Gemini 3 Pro (image generation)
- `OUTPUT_DIR` — local image cache directory
- `AUTHORS_DIR` — path to author JSON files
- Cloudinary credentials are currently hardcoded here (not in env)

### Directory Structure

```
puzzleAI/
├── app.py              # Flask app factory, blueprint registration
├── config.py           # Central configuration, env vars
├── models.py           # Author and PuzzleIdea dataclasses
├── generate.py         # CLI entry point (python generate.py --author ...)
├── core/               # Generation engine
│   ├── prompt_engine.py    # Scene descriptions via Gemini Flash
│   ├── image_generator.py  # Image generation via Gemini Image API
│   ├── free_generator.py   # Image generation via Pollinations.ai FLUX
│   └── pixel_converter.py  # Pixel art conversion via Pyxelate
├── routes/             # Flask blueprints (HTTP layer)
│   ├── views.py            # Page rendering, local image serving
│   ├── generation.py       # /generate, /events/<id>, /api/batch-*
│   └── authors.py          # CRUD /api/author/<name>
├── services/           # Business logic and external integrations
│   ├── generation_service.py   # Pipeline orchestration, background threads
│   ├── batch_api_service.py    # Google Batch API submission and polling
│   ├── cloudinary_service.py   # Cloudinary upload/list
│   ├── author_sync_service.py  # Local ↔ Cloudinary author sync
│   └── history_service.py      # Image history retrieval
├── scripts/            # One-off utilities (not part of the web app)
│   └── migrate_to_cloud.py     # Migrate local files to Cloudinary
├── templates/          # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   └── components/
│       ├── sidebar.html
│       ├── gallery.html
│       └── author_modal.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── authors/            # Author profile JSON files
├── output/             # Generated images (local cache, git-ignored)
└── pyxelate-2.0.2/     # Vendored pixel art library (do not remove)
```

### Route Structure

| Blueprint | File | Responsibility |
|---|---|---|
| Views | `routes/views.py` | Render pages, serve local images |
| Generation | `routes/generation.py` | `/generate`, `/events/<id>`, `/api/batch-*` |
| Authors | `routes/authors.py` | CRUD for `/api/author/<name>` |

### Frontend

Single-page feel using Jinja2 templates + vanilla JS (`static/js/app.js`). Three tabs: Generator, Authors, Queue. No JS framework or bundler — just plain fetch + EventSource. Templates use component includes (`templates/components/`).

## Environment Variables

Required:
- `GEMINI_API_KEY` — Google Gemini API key

Optional (Cloudinary — currently hardcoded in `config.py`, should eventually move to env):
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

Copy `.env.example` to `.env` for local development.

## Vendored Dependency

`pyxelate-2.0.2/` is a vendored local package (not on PyPI in this version). It is installed via `requirements.txt` as `./pyxelate-2.0.2`. Do not delete or move it.

## Deployment

Deployed to Heroku/Render via `Procfile`. Python version pinned in `runtime.txt` (3.11.9). The app is stateless except for:
- Local `output/` directory (ephemeral on Heroku)
- Cloudinary (persistent image store)
- Author JSON files in `authors/` (synced to/from Cloudinary on startup)
