"""
Puzzle AI Agent — Generator obrazów przez Gemini API

Łączy zamrożony szablon stylu + wygenerowaną scenę → pełny prompt → obraz.

Obsługuje zarówno Imagen (generate_images) jak i Gemini Flash Image (generate_content).
"""
import os
import time
from PIL import Image
from io import BytesIO
from google import genai
from google.genai import types

import config


client = genai.Client(api_key=config.GEMINI_API_KEY)


def _is_imagen_model(model: str) -> bool:
    """Sprawdza czy model to Imagen (używa innego API niż Gemini)."""
    return "imagen" in model.lower()


def _generate_with_imagen(full_prompt: str, output_path: str) -> bool:
    """Generuje obraz przez Imagen API (generate_images)."""
    response = client.models.generate_images(
        model=config.IMAGE_MODEL,
        prompt=full_prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type=config.IMAGE_FORMAT,
            aspect_ratio="1:1",
            image_config=types.ImageConfig(
                image_size="2K"
            )
        ),
    )

    if not response.generated_images:
        return False

    image = response.generated_images[0].image
    image.save(output_path)
    return True


def _generate_with_gemini(full_prompt: str, output_path: str) -> bool:
    """Generuje obraz przez Gemini Image API (generate_content)."""
    response = client.models.generate_content(
        model=config.IMAGE_MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],  # Tylko IMAGE — TEXT obniża rozdzielczość
            image_config=types.ImageConfig(
                aspect_ratio=config.IMAGE_ASPECT_RATIO,
            ),
        ),
    )

    if not response.candidates:
        print("    ⚠️  Brak kandydatów (możliwe blokowanie przez safety filters)")
        return False

    candidate = response.candidates[0]
    finish_reason = getattr(candidate, "finish_reason", None)
    if finish_reason and str(finish_reason) not in ("STOP", "FinishReason.STOP", "1"):
        print(f"    ⚠️  Finish reason: {finish_reason}")

    if not candidate.content or not candidate.content.parts:
        return False

    for part in candidate.content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            image_data = part.inline_data.data
            image = Image.open(BytesIO(image_data))
            if image.mode != "RGB":
                image = image.convert("RGB")
            image.save(output_path, "JPEG", quality=95)
            return True

    return False


def generate_image(full_prompt: str, output_path: str, retries: int = 3) -> bool:
    """
    Generuje obraz na podstawie pełnego promptu i zapisuje go na dysku.
    
    Automatycznie wybiera API na podstawie modelu (Imagen vs Gemini).
    
    Args:
        full_prompt: Kompletny prompt (szablon stylu + scena)
        output_path: Ścieżka do zapisu pliku JPEG
        retries: Liczba prób w razie błędu
        
    Returns:
        True jeśli sukces, False jeśli niepowodzenie
    """
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    use_imagen = _is_imagen_model(config.IMAGE_MODEL)

    for attempt in range(1, retries + 1):
        try:
            if use_imagen:
                success = _generate_with_imagen(full_prompt, output_path)
            else:
                success = _generate_with_gemini(full_prompt, output_path)

            if success:
                return True
            
            print(f"    ⚠️  Brak obrazu w odpowiedzi (próba {attempt}/{retries})")
            if attempt < retries:
                time.sleep(2)

        except Exception as e:
            error_msg = str(e)
            print(f"    ⚠️  Błąd (próba {attempt}/{retries}): {error_msg}")
            if attempt < retries:
                wait_time = 5 * attempt
                print(f"    ⏳ Czekam {wait_time}s przed ponowną próbą...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Nie udało się po {retries} próbach")
                return False

    return False