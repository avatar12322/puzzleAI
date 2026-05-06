import cv2
import numpy as np
from PIL import Image

def pixelate_smart(input_path, output_path, size=50, num_colors=12):
    # 1. Wczytaj obraz
    img = cv2.imread(input_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 2. Kwantyzacja w wysokiej rozdzielczości K-Means
    np.random.seed(42) # Powtarzalność wyników
    pixels = img.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    # KMEANS_PP_CENTERS jest bardziej stabilny niż RANDOM
    _, labels, centers = cv2.kmeans(pixels, num_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    
    centers = np.uint8(centers)
    quantized_high_res = centers[labels.flatten()].reshape(img.shape)
    
    # Znajdź indeks koloru który jest najbliżej białego i zrób go idealnie białym (tło)
    white_dist = np.sum((centers - [255, 255, 255])**2, axis=1)
    bg_idx = np.argmin(white_dist)
    centers[bg_idx] = [255, 255, 255]
    
    # Znajdź najciemniejszy kolor i zrób z niego idealnie czarny (kontury)
    dark_dist = np.sum((centers - [0, 0, 0])**2, axis=1)
    outline_idx = np.argmin(dark_dist)
    centers[outline_idx] = [0, 0, 0]
    
    # Przypisz poprawione kolory
    quantized_high_res = centers[labels.flatten()].reshape(img.shape)
    
    # 3. Zmniejszanie (Area interpolation jest świetna do downsamplingu)
    small = cv2.resize(quantized_high_res, (size, size), interpolation=cv2.INTER_AREA)
    
    # 4. Ponowna twarda kwantyzacja małego obrazka do tej samej palety 'centers'
    # Obliczamy odległości małych pikseli od naszej palety
    small_pixels = small.reshape((-1, 3))
    
    # Dla każdego piksela znajdź najbliższy kolor w palecie
    dists = np.linalg.norm(small_pixels[:, np.newaxis] - centers, axis=2)
    closest_labels = np.argmin(dists, axis=1)
    
    final_small = centers[closest_labels].reshape(small.shape)
    
    # 5. Zapisz
    out_img = Image.fromarray(final_small)
    out_img.save(output_path)
    
    # Preview
    preview = out_img.resize((size*10, size*10), Image.Resampling.NEAREST)
    preview.save(output_path.replace('.png', '_preview.png'))

if __name__ == '__main__':
    pixelate_smart('test_large.jpg', 'test_pixel_new.png', size=50, num_colors=8)
    print("Zrobione!")
