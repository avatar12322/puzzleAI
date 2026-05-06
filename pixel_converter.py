import os
from skimage import io
from pyxelate import Pyx
from PIL import Image

def convert_to_pixel_art(input_path: str, size: int = 50, colors: int = 12) -> str:
    """
    Konwerter na pixel art używający biblioteki Pyxelate.
    """
    try:
        # Wczytanie obrazu przez skimage.io (używamy tej samej konwencji co Pyxelate)
        image = io.imread(input_path)
        
        # Pyxelate ma parametry height, width. Użyjemy ich do wymuszenia docelowego rozmiaru.
        # Włączamy też dither="none" bo kolorowanki nie lubią ditheringu (wzorów szachownicy z kropek).
        pyx = Pyx(height=size, width=size, palette=colors, dither="none")
        
        # Uczenie palety i transformacja w jednym kroku
        new_image = pyx.fit_transform(image)
        
        # Ścieżka wyjściowa (zawsze PNG dla pixel artu)
        base_path = os.path.splitext(input_path)[0]
        pixel_path = base_path + ".png"
        
        # Jeśli wejściowy też był PNG, dodajemy dopisek, żeby nie nadpisać oryginału
        if pixel_path == input_path:
            pixel_path = base_path + "_pixel.png"
            
        # Zapis używając io.imsave
        io.imsave(pixel_path, new_image)
        
        # Tworzenie wersji preview do wyświetlenia (Powiększamy x15 bez antyaliasingu - NEAREST)
        preview_path = pixel_path.replace('.png', '_preview.png')
        out_img = Image.open(pixel_path)
        preview = out_img.resize((size * 15, size * 15), Image.Resampling.NEAREST)
        preview.save(preview_path)
        
        return pixel_path
    except Exception as e:
        import traceback
        print(f"Błąd konwersji pyxelate: {e}")
        traceback.print_exc()
        return input_path

