import os
from openai import OpenAI
from dotenv import load_dotenv
import requests
from io import BytesIO
import base64
from PIL import Image
import imagehash
from collections import defaultdict
from config import (
    MODELS,
    TRANSLATION_SYSTEM_MESSAGES,
    IMAGE_SETTINGS,
    TEXT_SETTINGS,
    COST_PER_TOKEN
)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Keep track of processed image hashes and URLs
processed_hashes = defaultdict(list)
processed_urls = set()

# Keep track of token usage
total_tokens = 0
total_images = 0
total_cost = 0

def get_usage_stats():
    """
    Get the current usage statistics.
    
    Returns:
        dict: Dictionary containing token usage statistics
    """
    return {
        'total_tokens': total_tokens,
        'total_images': total_images,
        'total_cost': total_cost
    }

def reset_usage_stats():
    """Reset all usage statistics to zero."""
    global total_tokens, total_images, total_cost, processed_hashes, processed_urls
    total_tokens = 0
    total_images = 0
    total_cost = 0
    processed_hashes.clear()
    processed_urls.clear()

def optimize_image(image_data, max_size=IMAGE_SETTINGS["max_size"], quality=IMAGE_SETTINGS["quality"]):
    """
    Optimize image by resizing and compressing it.
    
    Args:
        image_data: BytesIO object containing the image
        max_size: Maximum width and height
        quality: JPEG compression quality (1-100)
    
    Returns:
        BytesIO: Optimized image data
    """
    try:
        # Open the image
        img = Image.open(image_data)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Calculate new size while maintaining aspect ratio
        ratio = min(max_size[0] / img.size[0], max_size[1] / img.size[1])
        if ratio < 1:
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Warning: Image optimization failed - {str(e)}")
        return image_data

def is_similar_to_processed(image_data, image_url, threshold=IMAGE_SETTINGS["similarity_threshold"]):
    """
    Check if an image is similar to previously processed ones.
    
    Args:
        image_data: BytesIO object containing the image
        image_url: URL of the image being processed
        threshold: Hash difference threshold for considering images similar
    
    Returns:
        bool: True if similar image was already processed
    """
    try:
        # If we've already processed this exact URL, skip similarity check
        if image_url in processed_urls:
            return False
            
        img = Image.open(image_data)
        hash = str(imagehash.average_hash(img))
        
        # Check against all processed hashes
        for existing_hash in processed_hashes[img.size]:
            if abs(len(hash) - len(existing_hash)) <= threshold:
                return True
        
        # Store the hash and URL for future comparisons
        processed_hashes[img.size].append(hash)
        processed_urls.add(image_url)
        return False
    except Exception as e:
        print(f"Warning: Image similarity check failed - {str(e)}")
        return False

def generate_alt_text(image_url, language='English', min_words=TEXT_SETTINGS["min_words"], max_words=TEXT_SETTINGS["max_words"]):
    """
    Generate alt text for an image in the specified language with word length constraints.
    First generates English description, then translates to target language if needed.
    
    Args:
        image_url (str): URL of the image
        language (str): Target language for the alt text
        min_words (int): Minimum number of words in the description
        max_words (int): Maximum number of words in the description
    
    Returns:
        str: Generated alt text in the specified language
    """
    global total_tokens, total_images, total_cost
    
    try:
        # Download the image
        response = requests.get(image_url)
        response.raise_for_status()
        
        # Create BytesIO object from image data
        image_data = BytesIO(response.content)
        
        # Only check for similarity when processing a new image URL
        if language == 'English':  # Only check similarity for the first language
            # Create a new BytesIO object with the same content for similarity check
            image_data_for_check = BytesIO(response.content)
            if is_similar_to_processed(image_data_for_check, image_url):
                raise Exception("Skipped: Too similar to previously processed image")
        
        # Optimize the image
        optimized_image = optimize_image(image_data)
        
        # Convert optimized image to base64
        base64_image = base64.b64encode(optimized_image.read()).decode('utf-8')
        
        # First, always generate English description
        system_message = f"""You are an expert at describing images.
Generate a detailed description that is between {min_words} and {max_words} words long.
Focus on the key elements, composition, colors, and context of the image."""

        # Create the API request for English description
        response = client.chat.completions.create(
            model=MODELS["image_analysis"],
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Please describe this image using between {min_words} and {max_words} words."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=TEXT_SETTINGS["max_tokens"]
        )
        
        english_description = response.choices[0].message.content.strip()
        
        # Update usage statistics for image analysis
        total_tokens += response.usage.total_tokens
        total_images += 1
        total_cost += response.usage.total_tokens * COST_PER_TOKEN
        
        # If target language is English, return the description
        if language == 'English':
            return english_description
            
        # For other languages, translate the English description
        system_message = TRANSLATION_SYSTEM_MESSAGES.get(
            language,
            f"You are a professional translator. Translate the following text to {language}. Maintain the style and tone while ensuring the translation sounds natural."
        )
        
        # Create the translation request
        response = client.chat.completions.create(
            model=MODELS["translation"],
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": english_description
                }
            ],
            max_tokens=TEXT_SETTINGS["max_tokens"]
        )
        
        # Update usage statistics for translation
        total_tokens += response.usage.total_tokens
        total_cost += response.usage.total_tokens * COST_PER_TOKEN
        
        return response.choices[0].message.content.strip()
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error downloading image: {str(e)}")
    except Exception as e:
        raise Exception(f"Error generating alt text: {str(e)}")
