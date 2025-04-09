"""
Configuration settings for the Alt Text Generator application.
Contains model settings, API configurations, and other parameters.
"""

# OpenAI Model Settings
MODELS = {
    "image_analysis": "gpt-4o-mini",  # Model for analyzing images and generating English descriptions
    "translation": "gpt-4o-mini",      # Model for translating descriptions to other languages
}

# Language Settings
TRANSLATION_SYSTEM_MESSAGES = {
    'German': "Du bist ein professioneller Übersetzer. Übersetze den folgenden Text ins Deutsche. Behalte dabei den Stil und Ton bei, aber stelle sicher, dass die Übersetzung natürlich klingt.",
    'French': "Vous êtes un traducteur professionnel. Traduisez le texte suivant en français. Conservez le style et le ton tout en vous assurant que la traduction semble naturelle.",
    'Italian': "Sei un traduttore professionista. Traduci il seguente testo in italiano. Mantieni lo stile e il tono assicurandoti che la traduzione suoni naturale."
}

# Default Languages
AVAILABLE_LANGUAGES = ['English', 'German', 'French', 'Italian']

# Image Processing Settings
IMAGE_SETTINGS = {
    "max_size": (800, 800),  # Maximum dimensions for image optimization
    "quality": 85,          # JPEG compression quality (1-100)
    "similarity_threshold": 5  # Threshold for considering images similar
}

# Word Length Constraints
TEXT_SETTINGS = {
    "min_words": 10,
    "max_words": 50,
    "max_tokens": 300
}

# Cost Tracking
COST_PER_TOKEN = 0.00015  # Cost per token in USD 