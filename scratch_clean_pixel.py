import cv2
import numpy as np
from PIL import Image

def pixelate_clean(input_path, output_path, size=50, num_colors=8):
    # Wczytaj i przekonwertuj
    img = cv2.imread(input_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Krok 1: Wstępne rozmycie żeby pozbyć się detali z AI i mieć płaskie plamy
    blurred = cv2.bilateralFilter(img, d=15, sigmaColor=75, sigmaSpace=75)
    
    # Krok 2: K-Means na 8 kolorów
    pixels = blurred.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    centers = np.uint8(centers)
    
    # Krok 3: Zmniejszenie do 50x50
    quantized_high = centers[labels.flatten()].reshape(blurred.shape)
    small = cv2.resize(quantized_high, (size, size), interpolation=cv2.INTER_AREA)
    
    # Krok 4: Wymuszenie palety na małym obrazku
    small_pixels = small.reshape((-1, 3))
    dists = np.linalg.norm(small_pixels[:, np.newaxis] - centers, axis=2)
    closest_labels = np.argmin(dists, axis=1)
    
    # Krok 5: Clean up (usuwanie pojedynczych pikseli)
    # Zamiast na kolorach RGB, robimy median blur na indeksach (labelkach)!
    # Dzięki temu upewniamy się, że nie powstają nowe kolory
    labels_2d = closest_labels.reshape((size, size)).astype(np.uint8)
    labels_2d_clean = cv2.medianBlur(labels_2d, 3)  # usuwa pojedyncze "brudy"
    
    # Krok 6: Odbudowa obrazu i białe tło na sztywno
    final_small = centers[labels_2d_clean]
    
    # Szukamy najjaśniejszego koloru w palecie i zamieniamy go w czyste 255,255,255
    brightness = np.sum(centers, axis=1)
    bg_idx = np.argmax(brightness)
    mask_bg = (labels_2d_clean == bg_idx)
    final_small[mask_bg] = [255, 255, 255]
    
    # Opcjonalnie najciemniejszy na czarno
    dark_idx = np.argmin(brightness)
    mask_dark = (labels_2d_clean == dark_idx)
    final_small[mask_dark] = [0, 0, 0]
    
    # Zapis
    out_img = Image.fromarray(final_small)
    out_img.save(output_path)
    
    preview = out_img.resize((size*10, size*10), Image.Resampling.NEAREST)
    preview.save(output_path.replace('.png', '_preview.png'))

if __name__ == '__main__':
    pixelate_clean('test_large.jpg', 'test_pixel_clean.png', size=50, num_colors=8)
    print("Zrobione!")
