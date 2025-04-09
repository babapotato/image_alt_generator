from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin, urlparse
import time
import re

def is_valid_image_url(url):
    """Check if the URL points to a valid image format (excluding SVG)."""
    # List of valid image extensions (excluding .svg)
    valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.ico')
    
    # Check if URL is a data URL
    if url.startswith('data:image/'):
        image_type = url.split(';')[0].split('/')[1].lower()
        return image_type != 'svg+xml'
    
    # Check URL path extension
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(path.endswith(ext) for ext in valid_extensions)

def get_image_urls(url):
    print(f"🌐 Setting up headless browser...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-allow-origins=*")
    
    try:
        print(f"🚀 Launching browser...")
        # Initialize ChromeDriver with automatic version detection
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print(f"📥 Loading page: {url}")
        driver.get(url)
        
        # Wait for JavaScript to load content
        print("⏳ Waiting for page to load completely...")
        time.sleep(5)  # Give the page time to load
        
        print("🔍 Finding images...")
        # Get all image elements
        images = driver.find_elements("tag name", "img")
        
        image_urls = []
        skipped_count = 0
        for img in images:
            try:
                src = img.get_attribute('src')
                if src:
                    full_url = urljoin(url, src)
                    if is_valid_image_url(full_url):
                        image_urls.append(full_url)
                        print(f"  ✓ Found image: {full_url}")
                    else:
                        print(f"  ⚠️ Skipped unsupported format: {full_url}")
                        skipped_count += 1
            except Exception as e:
                print(f"  ⚠️ Skipped an image due to: {e}")
                skipped_count += 1
        
        print(f"✅ Found {len(image_urls)} valid images (skipped {skipped_count} unsupported/invalid images)")
        
        driver.quit()
        return image_urls
        
    except Exception as e:
        print(f"❌ Error during web scraping: {e}")
        if 'driver' in locals():
            driver.quit()
        return []
