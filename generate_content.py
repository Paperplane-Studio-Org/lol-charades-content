import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure GenAI
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found in environment. Please set it in .env file.")
    exit(1)

genai.configure(api_key=api_key)

def generate_categories():
    """Generates categories using Gemini."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    Generate a list of 10 diverse and fun charades categories for a mobile game called "LOL Charades".
    Each category must have:
    - id: a unique slug (e.g., "hollywood_hits")
    - title: a catchy title (e.g., "Blockbuster Movies")
    - description: a short description
    - icon: one of [movie_filter, music_note, bolt, pets, public, videogame_asset, restaurant]
    - color: a hex color string starting with 0xFF (e.g., "0xFFFFD700")
    - difficulty: one of [easy, medium, hard]
    - words: a list of 15-20 relevant words or phrases to act out.
    - isLocked: boolean (false for most, true for some hard ones)
    - tag: optional string (e.g., "Hot", "New", "Retro")

    Return the result as a raw JSON list only.
    """
    
    response = model.generate_content(prompt)
    try:
        # Clean up the response text in case it contains markdown code blocks
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:-3]
        elif text.startswith("```"):
            text = text[3:-3]
        
        return json.loads(text)
    except Exception as e:
        print(f"Error parsing GenAI response: {e}")
        print(f"Raw response: {response.text}")
        return None

def update_files(categories):
    """Updates category.json and metadata.json."""
    if not categories:
        return

    # Save category.json
    with open('category.json', 'w') as f:
        json.dump(categories, f, indent=2)
    print("Updated category.json")

    # Update metadata.json
    metadata_file = 'metadata.json'
    version = 1
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
            version = metadata.get('version', 0) + 1
    
    metadata = {
        "version": version,
        "contentUrl": "https://raw.githubusercontent.com/Paperplane-Studio-Org/LOL_Charades_Content/main/category.json"
    }
    
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Updated metadata.json to version {version}")

if __name__ == "__main__":
    print("Generating new charades content...")
    new_categories = generate_categories()
    if new_categories:
        update_files(new_categories)
        print("Success!")
    else:
        print("Failed to generate content.")
