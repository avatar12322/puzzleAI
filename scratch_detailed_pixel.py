import cv2
import numpy as np
from PIL import Image

def pixelate_detailed(input_path, output_path, size=64, num_colors=12):
    img = cv2.imread(input_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Krok 1: Wzmocnienie krawędzi w dużej rozdzielczości
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Wykrywanie krawędzi (adaptacyjne lub Canny)
    edges = cv2.Canny(gray, 100, 200)
    
    # Pogrubienie krawędzi, żeby przetrwały zmniejszanie
    kernel = np.ones((3,3), np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=2)
    
    # Nakładamy czarne krawędzie na oryginalny obraz
    img_edges = img.copy()
    img_edges[edges > 0] = [0, 0, 0]
    
    # Krok 2: Lekkie rozmycie kolorów (żeby zbić podobne odcienie, ale zachować krawędzie)
    blurred = cv2.bilateralFilter(img_edges, d=9, sigmaColor=50, sigmaSpace=50)
    
    # 2. Kwantyzacja K-Means
    np.random.seed(42)
    pixels = img.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(pixels, num_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    
    centers = np.uint8(centers)
    quantized_high = centers[labels.flatten()].reshape(blurred.shape)
    
    # Krok 4: Zmniejszanie - INTER_AREA dobrze uśrednia, zachowując grube czarne linie
    small = cv2.resize(quantized_high, (size, size), interpolation=cv2.INTER_AREA)
    
    # Krok 5: Kwantyzacja z powrotem do palety
    small_pixels = small.reshape((-1, 3))
    dists = np.linalg.norm(small_pixels[:, np.newaxis] - centers, axis=2)
    closest_labels = np.argmin(dists, axis=1)
    
    labels_2d = closest_labels.reshape((size, size)).astype(np.uint8)
    
    # Delikatniejszy clean-up (żeby nie zmazać małych detali!)
    # Wcześniej było 3, teraz może nie robimy median blur na całym obrazku,
    # albo robimy go tylko na kolorach, a czarnych konturów nie ruszamy?
    # Sprawdźmy bez median blur lub z bardzo lekkim
    # labels_2d_clean = cv2.medianBlur(labels_2d, 3) 
    labels_2d_clean = labels_2d  # Zostawmy więcej detali
    
    final_small = centers[labels_2d_clean]
    
    # Tło na czysty biały
    brightness = np.sum(centers, axis=1)
    bg_idx = np.argmax(brightness)
    mask_bg = (labels_2d_clean == bg_idx)
    final_small[mask_bg] = [255, 255, 255]
    
    # Czarny kontur na czysty czarny
    dark_idx = np.argmin(brightness)
    mask_dark = (labels_2d_clean == dark_idx)
    final_small[mask_dark] = [0, 0, 0]
    
    # Zapis
    out_img = Image.fromarray(final_small)
    out_img.save(output_path)
    
    preview = out_img.resize((size*10, size*10), Image.Resampling.NEAREST)
    preview.save(output_path.replace('.png', '_preview.png'))

if __name__ == '__main__':
    pixelate_detailed('test_large.jpg', 'test_pixel_detailed.png', size=64, num_colors=12)
    print("Zrobione!")
