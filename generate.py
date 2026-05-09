"""
Puzzle AI Agent — Główny skrypt

Użycie:
  python generate.py --author "Kazimierz Grodecki" --count 10
  python generate.py --author "Anna Polna" --count 5 --dry-run
  python generate.py --author "Eleanor Ashford" --count 3 --compare
  python generate.py --list
"""
import argparse
import os
import sys
import time
import json

import config
from models import Author, load_author, list_authors
from core.prompt_engine import generate_puzzle_ideas
from core.image_generator import generate_image
from core.free_generator import generate_image_free


def print_banner():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║        🧩 PUZZLE AI AGENT v1.0 🧩        ║")
    print("  ║    Automatyczny generator puzzli         ║")
    print("  ╚══════════════════════════════════════════╝")
    print()


def run_generation(author: Author, count: int, dry_run: bool = False, compare: bool = False):
    """Główny pipeline generowania puzzli."""
    
    print(f"  👤 Autor:     {author.name}")
    print(f"  🎨 Tematyka:  {author.theme}")
    print(f"  🔢 Ilość:     {count} puzzli")
    print(f"  📂 Folder:    {author.output_dir(config.OUTPUT_DIR)}")
    if dry_run:
        print(f"  ⚡ Tryb:      DRY RUN (tylko prompty, bez obrazów)")
    if compare:
        print(f"  🔀 Tryb:      COMPARE (Gemini + FLUX darmowy)")
    print()
    print("=" * 50)

    # --- KROK 1: Generowanie scen ---
    print("\n📝 KROK 1: Generowanie pomysłów na sceny...\n")
    ideas = generate_puzzle_ideas(author, count)

    # Wyświetl wygenerowane pomysły
    for i, idea in enumerate(ideas, 1):
        print(f"\n  [{i}/{len(ideas)}] 📌 {idea.title}")
        short_scene = idea.scene[:150].replace('\n', ' ')
        print(f"          {short_scene}...")

    if dry_run:
        output_dir = author.output_dir(config.OUTPUT_DIR)
        os.makedirs(output_dir, exist_ok=True)
        prompts_file = os.path.join(output_dir, "_prompts_preview.json")
        
        prompts_data = []
        for idea in ideas:
            full = idea.full_prompt(author.style_template)
            prompts_data.append({
                "title": idea.title,
                "scene": idea.scene,
                "full_prompt": full,
            })
        
        with open(prompts_file, 'w', encoding='utf-8') as f:
            json.dump(prompts_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n\n✅ DRY RUN zakończony!")
        print(f"   Podgląd promptów zapisano w: {prompts_file}")
        return

    # --- KROK 2: Generowanie obrazów ---
    if compare:
        print(f"\n\n🖼️  KROK 2: Generowanie {len(ideas)} obrazów × 2 modele...\n")
    else:
        print(f"\n\n🖼️  KROK 2: Generowanie {len(ideas)} obrazów...\n")
    
    output_dir = author.output_dir(config.OUTPUT_DIR)
    
    if compare:
        gemini_dir = os.path.join(output_dir, "gemini")
        flux_dir = os.path.join(output_dir, "flux")
        os.makedirs(gemini_dir, exist_ok=True)
        os.makedirs(flux_dir, exist_ok=True)
    else:
        os.makedirs(output_dir, exist_ok=True)

    gemini_success = 0
    flux_success = 0
    gemini_fail = 0
    flux_fail = 0

    for i, idea in enumerate(ideas, 1):
        full_prompt = idea.full_prompt(author.style_template)
        
        print(f"\n  [{i}/{len(ideas)}] 🎨 {idea.title}")

        if compare:
            # === GEMINI ===
            gemini_file = f"{i:03d}_{idea.filename}.jpg"
            gemini_path = os.path.join(gemini_dir, gemini_file)
            
            print(f"    💎 Gemini...", end=" ", flush=True)
            if generate_image(full_prompt, gemini_path):
                gemini_success += 1
                print(f"✅ {gemini_file}")
            else:
                gemini_fail += 1
                print(f"❌ failed")

            # === FLUX (darmowy) ===
            flux_file = f"{i:03d}_{idea.filename}.jpg"
            flux_path = os.path.join(flux_dir, flux_file)
            
            print(f"    🆓 FLUX...", end="  ", flush=True)
            if generate_image_free(full_prompt, flux_path):
                flux_success += 1
                print(f"✅ {flux_file}")
            else:
                flux_fail += 1
                print(f"❌ failed")
        else:
            # Tylko Gemini
            filename = f"{i:03d}_{idea.filename}.jpg"
            output_path = os.path.join(output_dir, filename)
            
            if generate_image(full_prompt, output_path):
                gemini_success += 1
                print(f"           ✅ Zapisano: {filename}")
            else:
                gemini_fail += 1
                print(f"           ❌ Nie udało się wygenerować")

        if i < len(ideas):
            time.sleep(2)

    # --- PODSUMOWANIE ---
    print("\n" + "=" * 50)
    print(f"\n  📊 PODSUMOWANIE:")
    
    if compare:
        print(f"     💎 Gemini:  {gemini_success}/{len(ideas)} sukces")
        print(f"     🆓 FLUX:    {flux_success}/{len(ideas)} sukces")
        print(f"     📂 Gemini:  {gemini_dir}")
        print(f"     📂 FLUX:    {flux_dir}")
        print(f"\n     Porównaj obrazki w obu folderach — te same numery = ten sam prompt!")
    else:
        print(f"     ✅ Sukces:   {gemini_success}/{len(ideas)}")
        if gemini_fail:
            print(f"     ❌ Błędy:    {gemini_fail}/{len(ideas)}")
        print(f"     📂 Pliki w:  {output_dir}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="🧩 Puzzle AI Agent — automatyczny generator puzzli",
    )
    parser.add_argument(
        "--author", "-a",
        type=str,
        help="Nazwa autora (musi istnieć plik w authors/)",
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=config.DEFAULT_COUNT,
        help=f"Ile puzzli wygenerować (domyślnie {config.DEFAULT_COUNT})",
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Tylko generuj prompty, nie twórz obrazów (podgląd)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Generuj z Gemini I darmowego FLUX jednocześnie do porównania",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Wyświetl listę dostępnych autorów",
    )

    args = parser.parse_args()

    print_banner()

    if args.list:
        authors = list_authors()
        if not authors:
            print("  Brak autorów! Stwórz plik JSON w folderze authors/")
        else:
            print("  📋 Dostępni autorzy:")
            for name in authors:
                print(f"     • {name}")
        print()
        return

    if not args.author:
        parser.error("Podaj --author lub użyj --list żeby zobaczyć dostępnych autorów")

    try:
        author = load_author(args.author)
    except FileNotFoundError as e:
        print(f"  ❌ {e}")
        sys.exit(1)

    run_generation(author, args.count, args.dry_run, args.compare)


if __name__ == "__main__":
    main()
