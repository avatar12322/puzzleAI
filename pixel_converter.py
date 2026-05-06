import os
import numpy as np
from skimage import io
from pyxelate import Pyx
from PIL import Image


def convert_to_pixel_art(input_path: str, size: int = 50, colors: int = 12) -> str:
    """
    Konwerter na pixel art używający biblioteki Pyxelate.
    Zwraca ścieżkę do pliku pixel art (PNG).
    Preview (powiększony x15) zapisywany jest obok jako _pixel_preview.png.
    """
    try:
        # Wczytanie obrazu
        image = io.imread(input_path)

        # Pyxelate height/width to FACTOR (dzielnik), nie rozmiar docelowy!
        # Żeby dostać ~size x size pikseli, dzielimy wymiary przez factor.
        h, w = image.shape[:2]
        factor_h = max(1, round(h / size))
        factor_w = max(1, round(w / size))

        pyx = Pyx(height=factor_h, width=factor_w, palette=colors, dither="none")
        new_image = pyx.fit_transform(image)

        # Pyxelate może zwrócić float64 (0.0–1.0) — konwertuj do uint8
        if new_image.dtype != np.uint8:
            new_image = (new_image * 255).clip(0, 255).astype(np.uint8)

        # Ścieżki wyjściowe — zawsze PNG, nigdy nie nadpisuj oryginału
        base_path = os.path.splitext(input_path)[0]
        pixel_path = base_path + "_pixel.png"
        preview_path = base_path + "_pixel_preview.png"

        # Zapis pixel art (mały)
        out_img = Image.fromarray(new_image)
        out_img.save(pixel_path)

        # Zapis preview (powiększony x15, ostre piksele NEAREST)
        out_h, out_w = new_image.shape[:2]
        preview = out_img.resize((out_w * 15, out_h * 15), Image.Resampling.NEAREST)
        preview.save(preview_path)

        print(f"  ✅ Pixel art: {pixel_path} ({out_w}x{out_h}px)")
        print(f"  ✅ Preview:   {preview_path} ({out_w*15}x{out_h*15}px)")

        return pixel_path

    except Exception as e:
        import traceback
        print(f"❌ Błąd konwersji pyxelate: {e}")
        traceback.print_exc()
        return input_path  # fallback — zwróć oryginał