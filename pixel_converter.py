import os
import numpy as np
from skimage import io
from pyxelate import Pyx
from PIL import Image

def convert_to_pixel_art(input_path: str, size: int = 50, colors: int = 12) -> str:
    """
    Konwerter na pixel art używający biblioteki Pyxelate.
    Optymalizowany pod kątem wydajności i poprawności typów danych.
    """
    try:
        # Wczytanie obrazu
        image = io.imread(input_path)
        img_height, img_width = image.shape[:2]
        
        # OBLICZENIA DLA PYXELATE v2:
        # height i width to faktory (dzielniki), nie piksele.
        # Żeby dostać docelowe 'size', dzielimy obecny rozmiar przez 'size'.
        downsample_factor = max(1, img_height // size)
        
        print(f"DEBUG: Przetwarzam obraz {img_width}x{img_height} z faktorem {downsample_factor} -> cel ok. {size}px")
        
        # Inicjalizacja Pyxelate
        # dither="none" dla czystych ikon
        pyx = Pyx(height=downsample_factor, width=downsample_factor, palette=colors, dither="none")
        
        # Transformacja
        new_image = pyx.fit_transform(image)
        
        # ZABEZPIECZENIE TYPU DANYCH:
        # Pyxelate może zwrócić float64 (0.0-1.0). Musimy mieć uint8 (0-255).
        if new_image.dtype != np.uint8:
            new_image = (new_image * 255).clip(0, 255).astype(np.uint8)
            
        # Ścieżki wyjściowe
        base_path = os.path.splitext(input_path)[0]
        pixel_path = base_path + ".png"
        if pixel_path == input_path:
            pixel_path = base_path + "_pixel.png"
            
        preview_path = base_path + "_preview.png"
        
        # OPTYMALIZACJA I/O:
        # Tworzymy obiekt Image bezpośrednio z tablicy numpy
        out_img = Image.fromarray(new_image)
        
        # Zapisujemy plik główny (mały pixel art)
        out_img.save(pixel_path)
        
        # Tworzenie wersji preview (powiększenie NEAREST)
        # Obliczamy realny rozmiar po konwersji (może się różnić o 1-2px od 'size')
        p_width, p_height = out_img.size
        preview = out_img.resize((p_width * 15, p_height * 15), Image.Resampling.NEAREST)
        preview.save(preview_path)
        
        print(f"✅ Konwersja zakończona: {pixel_path} oraz {preview_path}")
        return pixel_path
        
    except Exception as e:
        import traceback
        print(f"❌ Błąd krytyczny konwersji: {e}")
        traceback.print_exc()
        return input_path
