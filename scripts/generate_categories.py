import os
import json
import datetime
import re
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure GenAI
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment. Please set it in secrets/env.")
    exit(1)

client = genai.Client(api_key=api_key)

CATEGORY_FILE = 'category.json'
METADATA_FILE = 'metadata.json'
 
def calculate_font_color(hex_color_str):
    """Calculates whether white or black text should be used based on background luminance."""
    try:
        # Expected format: 0xFFRRGGBB
        if hex_color_str.startswith('0x'):
            hex_color_str = hex_color_str[2:]
        
        # Take the last 6 characters (RRGGBB)
        if len(hex_color_str) == 8:
            hex_color_str = hex_color_str[2:]
            
        r_raw = int(hex_color_str[0:2], 16) / 255.0
        g_raw = int(hex_color_str[2:4], 16) / 255.0
        b_raw = int(hex_color_str[4:6], 16) / 255.0
        
        # Proper WCAG luminance calculation with gamma correction
        def adjust(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            
        r = adjust(r_raw)
        g = adjust(g_raw)
        b = adjust(b_raw)
        
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        # Standard WCAG threshold is 0.179. 
        # We use a slightly lower threshold (0.15) to favor black text on medium-grey backgrounds as requested.
        return "0xFF000000" if luminance > 0.15 else "0xFFFFFFFF"
    except Exception as e:
        print(f"Error calculating font color for {hex_color_str}: {e}")
        return "0xFF000000"

def load_existing_categories():
    """Loads existing categories from category.json."""
    if os.path.exists(CATEGORY_FILE):
        try:
            with open(CATEGORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading existing categories: {e}")
    return []

def generate_new_categories():
    """Generates new categories using Gemini."""
    model_id = 'gemini-3.1-flash-lite'

    prompt = """
    Generate words for below mentioned categories for charades game".

    Movies:
    - Bollywood Movies
    - Kollywood Movies
    - Tollywood Movies
    - Mollywood Movies
    - Hollywood Movies

    Cinema Heroes:
    - Bollywood Actors
    - Kollywood Heroes
    - Tollywood Heroes
    - Mollywood Actors
    - Hollywood Actors

    Comedy:
    - Tamil Comedy Dialogs
    - Telugu Comedy Dialogs
    - Hindi Comedy Dialogs
    - Famous Comedy Scenes

    Punch Dialogues
    - Tamil Punch Dialogues
    - Telugu Punch Dialogues
    - Hindi Punch Dialogues
    - Famous Punch Dialogues

        Rules for Punch Dialogues:
        - Each item must be a memorable spoken dialogue, catchphrase, or quote.
        - Do NOT return movie names.
        - Do NOT return actor names.
        - Do NOT return scene descriptions.
        - Do NOT return generic references.
        - Every item must be something a player can act out or say.
        - Maximum 5 words per item.
        - Return only the phrase itself.

    Act It Out:
    - Daily Activities
    - Funny Situations
    - Emotions
    - Jobs and Professions
    - Actions

    Sports Category
    Examples:
    - Cricket
    - Football
    - Kabaddi
    - Tennis
    - Olympics

    Food Category
    Examples:
    - Dosa
    - Pizza
    - Biryani
    - Ice Cream
    - Burger

    Countries Category
    Examples:
    - India
    - Japan
    - USA
    - Australia

    Famous Places Category
    Examples:
    - Taj Mahal
    - Eiffel Tower
    - Great Wall

    Emotions Category
    Examples:
    - Angry
    - Excited
    - Embarrassed
    - Jealous
    - Confused

    Relationships Category
    Examples:
    - Teacher
    - Mother
    - Brother
    - Grandfather
    - Best Friend

    Household Objects Category
    Examples:
    - Fan
    - TV
    - Washing Machine
    - Refrigerator

    Festivals Category
    Examples:
    - Diwali
    - Pongal
    - Christmas
    - Holi

    Mythology Category
    Examples:
    - Hanuman
    - Krishna
    - Ravana
    - Arjuna
    - Ganesha

    Entertainment: Category
    Examples:
    - Web Series
    - Cartoons
    - Superheroes
    - Meme Culture
    - Famous Characters

    Rules:

    - Generate 60-80 words/phrases per category
    - Avoid duplicates across categories
    - Include mix of easy/medium/hard
    - Use culturally relevant items
    - Keep phrases short enough for acting
    - Avoid offensive or copyrighted dialogue lines verbatim
    - Ensure high replay value
    - Do not generate a category if a similar category already exists.
    - Do not generate alternate versions of:
        - Bollywood Movies
        - Hollywood Movies
        - Cartoons
        - Superheroes
        - Daily Activities
        - Jobs
    - Generate completely new category themes instead.

    QUALITY RULES:

    - Every item must be easily actable in charades.
    - Avoid semantic duplicates.
    - Avoid alternate spellings of the same item.
    - Avoid generic phrases.
    - Avoid obscure movie titles.
    - Prefer culturally recognizable items.
    - Ensure at least 90% of players can recognize the item.
    - Generate 60-80 items per category.
    - Maintain replay value.
    - If a category already exists, generate a different category instead.
    - Do not repeat items across categories.
    - For dialogue categories, maximum 5 words.
    - For dialogue categories, only use famous catchphrases.

    Each category must have:
    - id: a unique slug (e.g., "hollywood_hits")
    - title: a catchy title (e.g., "Blockbuster Movies")
    - description: a short description
    - icon: one of [movie_filter, music_note, bolt, pets, public, videogame_asset, restaurant, etc which matches the title]
    - color: a hex color string starting with 0xFF (e.g., "0xFFFFD700")
    - difficulty: one of [easy, medium, hard]
    - isLocked: boolean
    - tag: optional string (e.g., "Hot", "New", "Retro")
    - words: a JSON array of 60-80 unique strings (the charades words/phrases)

    Note: 40% of generated categories should have isLocked: false, and 60% should have isLocked: true.

    Return raw JSON only.
    """
    
    print("Requesting new categories from Gemini...")
    response = client.models.generate_content(
        model=model_id,
        contents=prompt
    )
    
    try:
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        
        categories = json.loads(text)
        if not isinstance(categories, list):
            raise ValueError("Response is not a list")
        return categories
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        # print(f"Raw response: {response.text}")
        return None

def normalize_word(word):
    return re.sub(r'[^a-z0-9]', '', word.lower())

def merge_categories(existing, newly_generated):
    """Merges newly generated categories into existing ones, removing duplicates."""
    category_map = {c['id']: c for c in existing}
    
    for new_cat in newly_generated:
        cat_id = new_cat['id']
        if cat_id in category_map:
            # Merge words
            existing_words = category_map[cat_id].get('words', [])
            new_words = new_cat.get('words', [])
            
            # Combine and deduplicate case-insensitively
            all_words_map = {
                normalize_word(w): w
                for w in existing_words
            }

            for nw in new_words:
                key = normalize_word(nw)
                if key not in all_words_map:
                    all_words_map[key] = nw
            
            merged_words = sorted(list(all_words_map.values()))
            category_map[cat_id]['words'] = merged_words
            
            # Update other fields if they were missing or want to refresh (optional)
            # For now, we preserve existing metadata like title/description if they exist
        else:
            # New category
            new_words = new_cat.get('words', [])
            if not new_words:
                print(f"Warning: Skipping new category {cat_id} because it has no words.")
                continue
                
            new_cat['words'] = sorted(list(set(new_words)))
            category_map[cat_id] = new_cat
            
    return list(category_map.values())

def validate_and_save(categories):
    """Validates structure and saves to category.json and updates metadata.json."""
    if not categories:
        print("No categories to save.")
        return False

    # Basic validation
    valid_categories = []
    for cat in categories:
        cat_id = cat.get('id', 'unknown')
        required_fields = ['id', 'title', 'description', 'words', 'color', 'difficulty', 'isLocked']
        
        missing = [f for f in required_fields if f not in cat]
        if missing:
            print(f"Validation Error: Category {cat_id} is missing fields: {', '.join(missing)}")
            continue
            
        if not isinstance(cat['words'], list) or len(cat['words']) == 0:
            print(f"Validation Error: Category {cat_id} has no words.")
            continue
        
        # Inject or update fontColor based on background color
        cat['fontColor'] = calculate_font_color(cat['color'])
        valid_categories.append(cat)

    if not valid_categories:
        print("Error: No valid categories to save.")
        return False

    if len(valid_categories) < len(categories):
        print(f"Warning: {len(categories) - len(valid_categories)} invalid categories were skipped.")

    # Save category.json
    with open(CATEGORY_FILE, 'w') as f:
        json.dump(valid_categories, f, indent=2)
    print(f"Successfully updated {CATEGORY_FILE} with {len(valid_categories)} categories.")

    # Update metadata.json
    version = 1
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
                version = metadata.get('version', 0) + 1
        except:
            pass
    
    metadata = {
        "version": version,
        "lastUpdated": datetime.datetime.now().isoformat(),
        "contentUrl": "https://raw.githubusercontent.com/Paperplane-Studio-Org/lol-charades-content/main/category.json"
    }
    
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Successfully updated {METADATA_FILE} to version {version}")
    return True

if __name__ == "__main__":
    print("Starting content refresh...")
    
    existing_cats = load_existing_categories()
    print(f"Loaded {len(existing_cats)} existing categories.")
    
    new_cats = generate_new_categories()
    if new_cats:
        print(f"Generated {len(new_cats)} categories from Gemini.")
        merged = merge_categories(existing_cats, new_cats)
        print(f"Total categories after merge: {len(merged)}")
        
        if validate_and_save(merged):
            print("Content refresh completed successfully.")
        else:
            print("Content refresh failed during validation or save.")
            exit(1)
    else:
        print("Failed to generate new categories. Skipping update.")
        exit(1)
