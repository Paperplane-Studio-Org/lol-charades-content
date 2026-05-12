import os
import json
import datetime
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
            
        r = int(hex_color_str[0:2], 16)
        g = int(hex_color_str[2:4], 16)
        b = int(hex_color_str[4:6], 16)
        
        # Luminance formula
        luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
        
        return "0xFFFFFFFF" if luminance < 0.5 else "0xFF000000"
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
    model_id = 'gemini-flash-latest'
    
    prompt = """
    Generate a list of 10 diverse and fun charades categories for a mobile game called "LOL Charades". 
    Include Indian flavours like Tamil Comedy Dialogs, Bollywood hits, Kollywood hits etc.
    Each category must have:
    - id: a unique slug (e.g., "hollywood_hits")
    - title: a catchy title (e.g., "Blockbuster Movies")
    - description: a short description
    - icon: one of [movie_filter, music_note, bolt, pets, public, videogame_asset, restaurant]
    - color: a hex color string starting with 0xFF (e.g., "0xFFFFD700")
    - fontColor: a hex color string starting with 0xFF ("0xFFFFFFFF" for dark bg, "0xFF000000" for light bg)
    - difficulty: one of [easy, medium, hard]
    - words: a list of 15-20 relevant words or phrases to act out.
    - isLocked: boolean (false for most, true for some hard ones)
    - tag: optional string (e.g., "Hot", "New", "Retro")

    Return the result as a raw JSON list only.
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
            all_words_map = {w.lower(): w for w in existing_words}
            for nw in new_words:
                if nw.lower() not in all_words_map:
                    all_words_map[nw.lower()] = nw
            
            merged_words = sorted(list(all_words_map.values()))
            category_map[cat_id]['words'] = merged_words
            
            # Update other fields if they were missing or want to refresh (optional)
            # For now, we preserve existing metadata like title/description if they exist
        else:
            # New category
            new_cat['words'] = sorted(list(set(new_cat.get('words', []))))
            category_map[cat_id] = new_cat
            
    return list(category_map.values())

def validate_and_save(categories):
    """Validates structure and saves to category.json and updates metadata.json."""
    if not categories:
        print("No categories to save.")
        return False

    # Basic validation
    for cat in categories:
        required_fields = ['id', 'title', 'description', 'words']
        for field in required_fields:
            if field not in cat:
                print(f"Validation failed: Category {cat.get('id', 'unknown')} missing field {field}")
                return False
        if not isinstance(cat['words'], list) or len(cat['words']) == 0:
            print(f"Validation failed: Category {cat['id']} has no words.")
            return False
        
        # Inject or update fontColor based on background color
        if 'color' in cat:
            cat['fontColor'] = calculate_font_color(cat['color'])

    # Save category.json
    with open(CATEGORY_FILE, 'w') as f:
        json.dump(categories, f, indent=2)
    print(f"Successfully updated {CATEGORY_FILE}")

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
