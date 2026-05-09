"""
Puzzle AI Agent — Darmowy generator obrazów (Pollinations.ai / FLUX)

Kompletnie darmowy, bez API key. Używa modeli FLUX.
"""
import os
import time
import urllib.parse
import requests


POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true&seed={seed}"


def generate_image_free(full_prompt: str, output_path: str, retries: int = 3) -> bool:
    """
    Generuje obraz przez Pollinations.ai (FLUX) — darmowe, bez API key.

    Args:
        full_prompt: Kompletny prompt
        output_path: Ścieżka do zapisu pliku
        retries: Liczba prób

    Returns:
        True jeśli sukces, False jeśli niepowodzenie
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Wyczyść prompt z nowych linii i zbędnych spacji
    clean_prompt = " ".join(full_prompt.split())

    # Zakoduj prompt do URL
    encoded_prompt = urllib.parse.quote(clean_prompt[:2000])  # Limit długości URL
    seed = hash(clean_prompt) % 1000000  # Deterministyczny seed z promptu

    # Używamy jawnie modelu flux w wysokiej rozdzielczości
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=2048&height=2048&nologo=true&seed={seed}&model=flux"
    print(f"    🔗 Próbuję: {url[:100]}...")


    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=120)

            if response.status_code == 200 and len(response.content) > 1000:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                print(f"    ⚠️  Błąd HTTP {response.status_code} (próba {attempt}/{retries})")
                if attempt < retries:
                    time.sleep(3)

        except Exception as e:
            print(f"    ⚠️  Błąd (próba {attempt}/{retries}): {str(e)}")
            if attempt < retries:
                wait_time = 5 * attempt
                print(f"    ⏳ Czekam {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    ❌ Nie udało się po {retries} próbach")
                return False

    return False
