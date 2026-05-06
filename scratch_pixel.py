from PIL import Image

def convert_to_pixel_art(input_path, output_path, size=50, colors=16):
    img = Image.open(input_path).convert('RGB')
    
    # Krok 1: Zmniejszenie z użyciem średniej (LANCZOS/BILINEAR) dla gładkich kolorów bazowych
    img_small = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Krok 2: Kwantyzacja (zmniejszenie palety)
    # Zmieniamy na tryb P (paleta), ograniczając kolory
    img_quantized = img_small.quantize(colors=colors, dither=Image.Dither.NONE)
    
    # Zapis
    img_quantized.save(output_path)
    
    # Krok 3: Opcjonalnie powiększenie z powrotem do np. 500x500 z NEAREST, żeby było widać ostre piksele (dla podglądu)
    img_upscaled = img_quantized.convert('RGB').resize((500, 500), Image.Resampling.NEAREST)
    img_upscaled.save(output_path.replace('.png', '_preview.png').replace('.jpg', '_preview.jpg'))

if __name__ == '__main__':
    # Wygenerujmy jakiś obrazek z pollinations na szybko w dużej rozdzielczości jako test
    import requests
    r = requests.get('https://image.pollinations.ai/prompt/cute%20unicorn%20vector%20art%20white%20background%20flat%20colors')
    with open('test_large.jpg', 'wb') as f:
        f.write(r.content)
        
    convert_to_pixel_art('test_large.jpg', 'test_pixel_50x50.png', size=50, colors=16)
    print("Zrobione!")
