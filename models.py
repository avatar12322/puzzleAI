"""
Puzzle AI Agent — Modele danych
"""
import json
import os
import re
from dataclasses import dataclass, field
from config import AUTHORS_DIR


def get_slug(name: str) -> str:
    """Zamienia nazwę na bezpieczny slug (bez spacji, lowercase)."""
    if not name:
        return ""
    s = name.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s]+', '_', s)
    return s


@dataclass
class Author:
    """Profil fikcyjnego autora puzzli."""
    name: str
    theme: str                    # Tematyka: "Mroczne zamki Europy"
    style_template: str           # Zamrożony szablon stylu (stała część promptu)
    scene_instructions: str       # Wskazówki dla AI jak generować sceny
    tags: list[str] = field(default_factory=list)
    negative_prompts: list[str] = field(default_factory=list)  # Czego unikać
    post_processing: str | None = None

    @property
    def slug(self) -> str:
        """Nazwa folderu dla autora (bez spacji, lowercase)."""
        return get_slug(self.name)

    def output_dir(self, base_output_dir: str) -> str:
        """Ścieżka do folderu wyjściowego autora."""
        return os.path.join(base_output_dir, self.slug)


@dataclass
class PuzzleIdea:
    """Wygenerowany pomysł na puzzle — scena + tytuł."""
    title: str          # Krótki tytuł (do nazwy pliku)
    scene: str          # Szczegółowy opis sceny (zmienna część promptu)

    def full_prompt(self, style_template: str) -> str:
        """Skleja stały szablon stylu ze sceną → pełny prompt dla generatora."""
        return f"{style_template}\n\n{self.scene}"

    @property
    def filename(self) -> str:
        """Bezpieczna nazwa pliku z tytułu."""
        name = self.title.lower().strip()
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[\s]+', '_', name)
        return name[:80]  # Limit długości


def load_author(name: str) -> Author:
    """Ładuje profil autora z pliku JSON w authors/."""
    # Szukaj po nazwie pliku
    slug = re.sub(r'[^\w\s-]', '', name.lower().strip())
    slug = re.sub(r'[\s]+', '_', slug)
    filepath = os.path.join(AUTHORS_DIR, f"{slug}.json")

    if not os.path.exists(filepath):
        # Szukaj po polu "name" we wszystkich plikach
        for fname in os.listdir(AUTHORS_DIR):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(AUTHORS_DIR, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('name', '').lower() == name.lower():
                filepath = fpath
                break
        else:
            available = [f.replace('.json', '') for f in os.listdir(AUTHORS_DIR) if f.endswith('.json')]
            raise FileNotFoundError(
                f"Nie znaleziono autora '{name}'.\n"
                f"Dostępni autorzy: {', '.join(available)}\n"
                f"Szukano pliku: {filepath}"
            )

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return Author(**data)


def list_authors() -> list[str]:
    """Zwraca listę dostępnych autorów."""
    if not os.path.exists(AUTHORS_DIR):
        return []
    authors = []
    for fname in os.listdir(AUTHORS_DIR):
        if fname.endswith('.json'):
            fpath = os.path.join(AUTHORS_DIR, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            authors.append(data.get('name', fname.replace('.json', '')))
    return authors
