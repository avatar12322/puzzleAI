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
    
    Używa modelu tekstowego Gemini do wymyślenia szczegółowych opisów scen.
    Styl NIE jest generowany — pochodzi z szablonu autora.
    """
    negative_section = ""
    if author.negative_prompts:
        negative_section = f"- Things to AVOID: {', '.join(author.negative_prompts)}"

    prompt = SCENE_GENERATION_PROMPT.format(
        author_name=author.name,
        theme=author.theme,
        scene_instructions=author.scene_instructions,
        negative_section=negative_section,
        count=count,
    )

    print(f"  🧠 Generuję {count} pomysłów na sceny dla '{author.name}'...")

    response = client.models.generate_content(
        model=config.TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=1.0,       # Wysoka kreatywność
            max_output_tokens=8192,
        ),
    )

    raw_text = response.text.strip()
    
    # Wyczyść ewentualne markdown code blocks
    raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
    raw_text = re.sub(r'\s*```$', '', raw_text)
    
    try:
        ideas_data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"  ❌ Błąd parsowania JSON z odpowiedzi AI: {e}")
        print(f"  Surowa odpowiedź (pierwsze 500 znaków):\n{raw_text[:500]}")
        raise

    ideas = []
    for item in ideas_data:
        idea = PuzzleIdea(
            title=item["title"],
            scene=item["scene"],
        )
        ideas.append(idea)

    print(f"  ✅ Wygenerowano {len(ideas)} pomysłów na sceny")
    return ideas
