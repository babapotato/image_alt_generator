from image_scraper import get_image_urls
from alt_text_generator import generate_alt_text
from ui import create_ui
from config import AVAILABLE_LANGUAGES
import sys

def main(url):
    print(f"\n🔍 Scanning {url} for images...")
    image_urls = get_image_urls(url)
    
    if not image_urls:
        print("❌ No images found on the page!")
        return
    
    print(f"✅ Found {len(image_urls)} images")
    print("\n🤖 Generating alt text for each image...")
    
    image_texts = {}
    for i, img_url in enumerate(image_urls, 1):
        print(f"\n📷 Processing image {i}/{len(image_urls)}: {img_url}")
        texts = {}
        for lang in AVAILABLE_LANGUAGES:
            print(f"  🌐 Generating {lang} description...", end='', flush=True)
            try:
                alt_text = generate_alt_text(img_url, lang)
                texts[lang] = alt_text
                print(" ✅")
            except Exception as e:
                texts[lang] = f"Error: {e}"
                print(f" ❌ Error: {e}")
        image_texts[img_url] = texts
    
    print("\n🖥️ Opening results window...")
    create_ui(image_texts)

def get_url_from_user():
    while True:
        url = input("\n🌐 Enter the website URL (or 'exit' to quit): ").strip()
        if url.lower() == 'exit':
            sys.exit(0)
        if url.startswith(('http://', 'https://')):
            return url
        print("❌ Please enter a valid URL starting with 'http://' or 'https://'")

if __name__ == "__main__":
    create_ui()
