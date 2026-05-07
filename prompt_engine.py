"""
Puzzle AI Agent — Silnik generowania promptów (scen)

Kluczowa zasada: STYL jest zamrożony w szablonie autora.
AI generuje TYLKO opisy scen, nigdy nie dotyka stylu.
"""
import json
import re
from google import genai
from google.genai import types

import config
from models import Author, PuzzleIdea


client = genai.Client(api_key=config.GEMINI_API_KEY)


SCENE_GENERATION_PROMPT = """You are an expert jigsaw puzzle art director. Your job is to create unique, detailed SCENE DESCRIPTIONS for puzzle illustrations.

CRITICAL RULES:
1. You generate ONLY the scene content (what is depicted). NEVER include style directives, rendering instructions, or technical specifications — those are handled separately.
2. Each scene must be UNIQUE and DIFFERENT from the others — vary the setting, objects, composition, mood, time of day, and focal elements.
3. Scenes must be HIGHLY DETAILED with many discoverable elements (this is for jigsaw puzzles — busy, rich scenes work best).
4. Include humorous or charming small details that make each scene special.
5. Structure each scene description with clear sections: Main Scene, Key Elements, Humorous/Charming Details, Environment Details, Background.

AUTHOR PROFILE:
- Name: {author_name}
- Theme: {theme}
- Scene guidance: {scene_instructions}
{negative_section}

Generate exactly {count} unique scene descriptions for this author's puzzle collection.

IMPORTANT: Respond ONLY with valid JSON in this exact format:
[
  {{
    "title": "Short English Title For Filename",
    "scene": "Detailed multi-paragraph scene description in English..."
  }},
  ...
]

Do NOT wrap the JSON in markdown code blocks. Output raw JSON only."""


def generate_puzzle_ideas(author: Author, count: int) -> list[PuzzleIdea]:
    """
    Generuje unikalne pomysły na sceny puzzli dla danego autora.
    Dzieli proces na mniejsze paczki, aby uniknąć limitów tokenów Gemini.
    """
    all_ideas = []
    chunk_size = 5
    
    negative_section = ""
    if author.negative_prompts:
        negative_section = f"- Things to AVOID: {', '.join(author.negative_prompts)}"

    total_chunks = (count + chunk_size - 1) // chunk_size
    
    for chunk_idx in range(total_chunks):
        current_chunk_count = min(chunk_size, count - len(all_ideas))
        if current_chunk_count <= 0: break
        
        prompt = SCENE_GENERATION_PROMPT.format(
            author_name=author.name,
            theme=author.theme,
            scene_instructions=author.scene_instructions,
            negative_section=negative_section,
            count=current_chunk_count,
        )

        max_retries = 2
        chunk_success = False
        
        for attempt in range(max_retries + 1):
            try:
                print(f"  🧠 Generuję paczkę {chunk_idx + 1}/{total_chunks} ({current_chunk_count} pomysłów, próba {attempt+1})...")

                response = client.models.generate_content(
                    model=config.TEXT_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=1.0,
                        max_output_tokens=8192,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )

                if not response.candidates or not response.text:
                    raise ValueError("Gemini zwrócił pustą odpowiedź")

                raw_text = response.text.strip()
                
                # Wyciąganie JSON-a (tablicy)
                json_match = re.search(r'\[\s*\{.*\}\s*\]', raw_text, re.DOTALL)
                if json_match:
                    raw_text = json_match.group(0)
                else:
                    raw_text = re.sub(r'^```(?:json)?\s*\n?', '', raw_text, flags=re.MULTILINE)
                    raw_text = re.sub(r'\n?```\s*$', '', raw_text, flags=re.MULTILINE)
                
                # Czyszczenie markdown (gwiazdki)
                raw_text = raw_text.replace("**", "")
                
                ideas_data = json.loads(raw_text)
                
                for item in ideas_data:
                    if "title" not in item or "scene" not in item:
                        continue
                    all_ideas.append(PuzzleIdea(title=item["title"], scene=item["scene"]))

                print(f"  ✅ Dodano {len(ideas_data)} pomysłów (łącznie: {len(all_ideas)})")
                chunk_success = True
                break

            except (json.JSONDecodeError, ValueError) as e:
                print(f"  ⚠️ Błąd paczki {chunk_idx + 1} ({e}), ponawiam...")
                if attempt < max_retries:
                    import time
                    time.sleep(1)
        
        if not chunk_success:
            print(f"  ❌ Nie udało się wygenerować paczki {chunk_idx + 1} po {max_retries+1} próbach.")

    return all_ideas