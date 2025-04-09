import tkinter as tk
from tkinter import ttk, messagebox
import pyperclip
from urllib.parse import urlparse
import threading
import queue
import time
from PIL import Image, ImageTk
import requests
from io import BytesIO
import os
from alt_text_generator import get_usage_stats, reset_usage_stats, optimize_image
from config import (
    AVAILABLE_LANGUAGES,
    TEXT_SETTINGS
)
from image_scraper import is_valid_image_url
from update_checker import UpdateChecker

class SetupWizard:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title("Setup - Alt Text Generator")
        self.window.geometry("500x300")
        self.window.transient(parent)
        self.window.grab_set()  # Make the window modal
        
        # Center the window
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'+{x}+{y}')
        
        self.setup_ui()
        
    def setup_ui(self):
        # Welcome message
        welcome_frame = ttk.Frame(self.window, padding="20")
        welcome_frame.pack(fill=tk.X)
        
        ttk.Label(welcome_frame, text="Welcome to Alt Text Generator!", 
                 font=('Helvetica', 16, 'bold')).pack()
        
        ttk.Label(welcome_frame, text="To get started, you'll need an OpenAI API key.",
                 wraplength=400).pack(pady=10)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(self.window, text="How to get an API key:", padding="10")
        instructions_frame.pack(fill=tk.X, padx=20, pady=10)
        
        instructions = [
            "1. Go to platform.openai.com/api-keys",
            "2. Sign in or create an account",
            "3. Click 'Create new secret key'",
            "4. Copy the key and paste it below"
        ]
        
        for instruction in instructions:
            ttk.Label(instructions_frame, text=instruction).pack(anchor='w')
        
        # API Key entry
        key_frame = ttk.Frame(self.window, padding="20")
        key_frame.pack(fill=tk.X)
        
        ttk.Label(key_frame, text="Enter your API key:").pack()
        
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var, width=40, show="*")
        self.api_key_entry.pack(pady=5)
        
        # Buttons
        button_frame = ttk.Frame(self.window, padding="20")
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Open OpenAI Website", 
                  command=lambda: os.system("open https://platform.openai.com/api-keys")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Save & Continue", 
                  command=self.save_api_key).pack(side=tk.RIGHT, padx=5)
    
    def save_api_key(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter an API key.")
            return
            
        try:
            with open('.env', 'w') as f:
                f.write(f"OPENAI_API_KEY={api_key}")
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save API key: {str(e)}")

class ImagePreviewWindow:
    def __init__(self, parent, image_data):
        self.window = tk.Toplevel(parent)
        self.window.title("Image Preview")
        
        # Create a label to display the image
        self.image_label = ttk.Label(self.window)
        self.image_label.pack(padx=10, pady=10)
        
        # Display the image
        self.display_image(image_data)
        
        # Add a close button
        close_btn = ttk.Button(self.window, text="Close", command=self.window.destroy)
        close_btn.pack(pady=(0, 10))
        
    def display_image(self, image_data):
        try:
            # Open and resize image if needed
            img = Image.open(image_data)
            
            # Calculate new size while maintaining aspect ratio
            max_size = (800, 600)
            ratio = min(max_size[0] / img.size[0], max_size[1] / img.size[1])
            if ratio < 1:
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            
            # Update label with new image
            self.image_label.configure(image=photo)
            self.image_label.image = photo  # Keep a reference
        except Exception as e:
            self.image_label.configure(text=f"Error displaying image: {str(e)}")

class AltTextGeneratorUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Multilingual Alt Text Generator")
        self.available_languages = AVAILABLE_LANGUAGES
        self.selected_languages = {lang: tk.BooleanVar(value=True) for lang in self.available_languages}
        
        # Check for updates
        self.update_checker = UpdateChecker(self.root)
        self.root.after(1000, self.check_for_updates)  # Check after UI is loaded
        
        # Check if API key is configured
        if not os.path.exists('.env') or not self.check_api_key():
            SetupWizard(self.root)
        
        self.setup_ui()
        self.website_processing = False
        self.single_processing = False
        self.paused = False
        self.current_website_thread = None
        self.current_single_thread = None
        self.results_queue = queue.Queue()
        self.root.after(100, self.check_queue)
        self.root.after(1000, self.update_usage_stats)
        self.preview_windows = []

    def check_api_key(self):
        """Check if the API key is configured and valid."""
        try:
            with open('.env', 'r') as f:
                content = f.read()
                if 'OPENAI_API_KEY=' in content and len(content.split('=')[1].strip()) > 5:
                    return True
        except:
            pass
        return False

    def setup_ui(self):
        # Create main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create menu bar
        self.setup_menu()

        # Create usage statistics frame at the top
        self.setup_usage_stats_frame()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Website scraping tab
        self.website_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(self.website_frame, text="Website Scraping")

        # Single image tab
        self.single_image_frame = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(self.single_image_frame, text="Single Image")

        # Setup website scraping tab
        self.setup_website_tab()
        
        # Setup single image tab
        self.setup_single_image_tab()

    def setup_menu(self):
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

    def check_for_updates(self):
        """Check for updates and show appropriate dialog."""
        self.update_checker.check_for_updates(silent=False)

    def setup_usage_stats_frame(self):
        """Create a frame to display usage statistics."""
        stats_frame = ttk.LabelFrame(self.main_frame, text="Usage Statistics", padding="5")
        stats_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Token count
        self.token_label = ttk.Label(stats_frame, text="Total Tokens: 0")
        self.token_label.pack(side=tk.LEFT, padx=10)

        # Image count
        self.image_label = ttk.Label(stats_frame, text="Images Processed: 0")
        self.image_label.pack(side=tk.LEFT, padx=10)

        # Estimated cost
        self.cost_label = ttk.Label(stats_frame, text="Estimated Cost: $0.00")
        self.cost_label.pack(side=tk.LEFT, padx=10)

        # Reset button
        reset_btn = ttk.Button(stats_frame, text="Reset Stats", command=self.reset_stats)
        reset_btn.pack(side=tk.RIGHT, padx=10)

    def update_usage_stats(self):
        """Update the usage statistics display."""
        stats = get_usage_stats()
        self.token_label.config(text=f"Total Tokens: {stats['total_tokens']:,}")
        self.image_label.config(text=f"Images Processed: {stats['total_images']:,}")
        self.cost_label.config(text=f"Estimated Cost: ${stats['total_cost']:.2f}")
        self.root.after(1000, self.update_usage_stats)  # Schedule next update

    def reset_stats(self):
        """Reset all usage statistics."""
        reset_usage_stats()
        self.update_usage_stats()

    def setup_options_frame(self, parent):
        # Options frame
        options_frame = ttk.LabelFrame(parent, text="Generation Options", padding="5")
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        # Word length range
        length_frame = ttk.Frame(options_frame)
        length_frame.pack(fill=tk.X, pady=2)

        ttk.Label(length_frame, text="Word Length Range:").pack(side=tk.LEFT, padx=5)
        
        self.min_words_var = tk.StringVar(value=str(TEXT_SETTINGS["min_words"]))
        self.max_words_var = tk.StringVar(value=str(TEXT_SETTINGS["max_words"]))
        
        min_entry = ttk.Entry(length_frame, textvariable=self.min_words_var, width=5)
        min_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(length_frame, text="to").pack(side=tk.LEFT, padx=2)
        
        max_entry = ttk.Entry(length_frame, textvariable=self.max_words_var, width=5)
        max_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(length_frame, text="words").pack(side=tk.LEFT, padx=2)

        # Language selection
        lang_frame = ttk.Frame(options_frame)
        lang_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(lang_frame, text="Languages:").pack(side=tk.LEFT, padx=5)
        
        for lang in self.available_languages:
            cb = ttk.Checkbutton(lang_frame, text=lang, variable=self.selected_languages[lang])
            cb.pack(side=tk.LEFT, padx=5)

    def setup_website_tab(self):
        # Input section
        input_frame = ttk.LabelFrame(self.website_frame, text="Website URL", padding="5")
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(input_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Button frame for controls
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT, padx=5)

        self.process_btn = ttk.Button(button_frame, text="Generate Alt Texts", command=self.start_processing)
        self.process_btn.pack(side=tk.LEFT, padx=2)

        self.pause_btn = ttk.Button(button_frame, text="Pause", command=self.toggle_pause, state="disabled")
        self.pause_btn.pack(side=tk.LEFT, padx=2)

        # Options section
        self.setup_options_frame(self.website_frame)

        # Status section
        self.setup_status_section(self.website_frame)

        # Results section
        self.setup_results_section(self.website_frame)

    def setup_single_image_tab(self):
        # Input section
        input_frame = ttk.LabelFrame(self.single_image_frame, text="Image URL", padding="5")
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        self.single_url_var = tk.StringVar()
        self.single_url_entry = ttk.Entry(input_frame, textvariable=self.single_url_var, width=50)
        self.single_url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        self.single_process_btn = ttk.Button(input_frame, text="Generate Alt Text", 
                                           command=self.process_single_image)
        self.single_process_btn.pack(side=tk.RIGHT, padx=5)

        # Options section
        self.setup_options_frame(self.single_image_frame)

        # Status section for single image
        self.single_status_frame = ttk.Frame(self.single_image_frame)
        self.single_status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.single_status_label = ttk.Label(self.single_status_frame, text="Ready")
        self.single_status_label.pack(side=tk.LEFT)

        # Results section for single image
        self.setup_results_section(self.single_image_frame)

    def get_selected_languages(self):
        return [lang for lang, var in self.selected_languages.items() if var.get()]

    def get_word_length_range(self):
        try:
            min_words = max(1, int(self.min_words_var.get()))
            max_words = max(min_words, int(self.max_words_var.get()))
            return min_words, max_words
        except ValueError:
            return 10, 50  # Default values

    def setup_status_section(self, parent):
        self.status_frame = ttk.Frame(parent)
        self.status_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT)

        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(self.status_frame, textvariable=self.progress_var)
        self.progress_label.pack(side=tk.RIGHT)

    def setup_results_section(self, parent):
        results_frame = ttk.LabelFrame(parent, text="Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create scrollable frame for results
        canvas = tk.Canvas(results_frame)
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
        
        if parent == self.website_frame:
            self.scrollable_frame = ttk.Frame(canvas)
        else:
            self.single_scrollable_frame = ttk.Frame(canvas)
            
        frame_to_bind = self.scrollable_frame if parent == self.website_frame else self.single_scrollable_frame
        
        frame_to_bind.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=frame_to_bind, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mouse wheel events for Mac OS compatibility
        def _on_mousewheel(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            else:
                # For Mac OS (event.delta)
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # Bind for Linux (Button-4/Button-5)
        canvas.bind("<Button-4>", _on_mousewheel)
        canvas.bind("<Button-5>", _on_mousewheel)
        # Bind for Windows/Mac OS (MouseWheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        # Bind for Mac OS (Trackpad)
        canvas.bind("<Button-2>", lambda e: "break")  # Prevent right-click from interfering
        canvas.bind("<B2-Motion>", lambda e: "break")

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

    def process_single_image(self):
        if self.single_processing:
            return

        url = self.single_url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter an image URL")
            return
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Error", "Please enter a valid URL starting with http:// or https://")
            return
            
        # Validate image format
        if not is_valid_image_url(url):
            messagebox.showerror("Error", "Invalid image format. Only jpg, jpeg, png, gif, webp, bmp, and ico files are supported.")
            return

        self.single_processing = True
        self.single_process_btn.config(text="Processing...", state="disabled")
        self.clear_single_results()
        self.update_single_status("Processing...")
        
        # Start processing in a separate thread
        self.current_single_thread = threading.Thread(target=self.process_single_url, args=(url,))
        self.current_single_thread.daemon = True
        self.current_single_thread.start()

    def process_single_url(self, url):
        try:
            from alt_text_generator import generate_alt_text

            selected_langs = self.get_selected_languages()
            if not selected_langs:
                self.results_queue.put(("single_error", "Please select at least one language"))
                return

            # Download and optimize the image first
            response = requests.get(url)
            response.raise_for_status()
            image_data = BytesIO(response.content)
            optimized_image = optimize_image(image_data)
            
            # Show image preview
            self.results_queue.put(("show_preview", optimized_image))

            min_words, max_words = self.get_word_length_range()
            texts = {}
            
            for lang in selected_langs:
                try:
                    alt_text = generate_alt_text(url, lang, min_words, max_words)
                    texts[lang] = alt_text
                except Exception as e:
                    texts[lang] = f"Error: {str(e)}"
            
            self.results_queue.put(("single_result", (url, texts)))
            self.results_queue.put(("single_done", None))

        except Exception as e:
            self.results_queue.put(("single_error", str(e)))

    def clear_single_results(self):
        for widget in self.single_scrollable_frame.winfo_children():
            widget.destroy()

    def update_single_status(self, text, is_error=False):
        self.single_status_label.config(text=text)
        if is_error:
            self.single_status_label.config(foreground="red")
        else:
            self.single_status_label.config(foreground="black")

    def toggle_pause(self):
        if not self.website_processing:
            return
        
        self.paused = not self.paused
        if self.paused:
            self.pause_btn.config(text="Resume")
            self.update_status("Paused")
        else:
            self.pause_btn.config(text="Pause")
            self.update_status("Resuming...")

    def clear_results(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def update_status(self, text, is_error=False):
        self.status_label.config(text=text)
        if is_error:
            self.status_label.config(foreground="red")
        else:
            self.status_label.config(foreground="black")

    def start_processing(self):
        if self.website_processing:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a URL")
            return
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Error", "Please enter a valid URL starting with http:// or https://")
            return

        self.website_processing = True
        self.paused = False
        self.process_btn.config(text="Processing...", state="disabled")
        self.pause_btn.config(state="normal", text="Pause")
        self.clear_results()
        self.update_status("Processing...")
        
        # Start processing in a separate thread
        self.current_website_thread = threading.Thread(target=self.process_url, args=(url,))
        self.current_website_thread.daemon = True
        self.current_website_thread.start()

    def process_url(self, url):
        try:
            from image_scraper import get_image_urls
            from alt_text_generator import generate_alt_text

            selected_langs = self.get_selected_languages()
            if not selected_langs:
                self.results_queue.put(("error", "Please select at least one language"))
                return

            min_words, max_words = self.get_word_length_range()

            self.results_queue.put(("status", "🔍 Scanning for images..."))
            image_urls = get_image_urls(url)

            if not image_urls:
                self.results_queue.put(("error", "No images found on the page!"))
                return

            self.results_queue.put(("status", f"Found {len(image_urls)} images"))

            for i, img_url in enumerate(image_urls, 1):
                while self.paused and self.website_processing:
                    time.sleep(0.1)  # Pause processing
                    continue
                    
                self.results_queue.put(("progress", f"Processing image {i}/{len(image_urls)}"))
                texts = {}
                for lang in selected_langs:
                    try:
                        while self.paused and self.website_processing:
                            time.sleep(0.1)  # Pause processing
                            continue
                            
                        alt_text = generate_alt_text(img_url, lang, min_words, max_words)
                        texts[lang] = alt_text
                    except Exception as e:
                        texts[lang] = f"Error: {str(e)}"
                
                self.results_queue.put(("result", (img_url, texts)))

            self.results_queue.put(("done", None))

        except Exception as e:
            self.results_queue.put(("error", str(e)))

    def add_result(self, img_url, texts, is_single=False):
        frame_to_use = self.single_scrollable_frame if is_single else self.scrollable_frame
        
        # Image frame
        img_frame = ttk.LabelFrame(frame_to_use, text="Image", padding="5")
        img_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # URL display with copy button
        url_frame = ttk.Frame(img_frame)
        url_frame.pack(fill=tk.X, pady=(0, 5))
        
        url_label = ttk.Label(url_frame, text=f"URL: {img_url}", wraplength=600)
        url_label.pack(side=tk.LEFT)
        
        copy_url_btn = ttk.Button(url_frame, text="Copy URL", 
                                command=lambda u=img_url: pyperclip.copy(u))
        copy_url_btn.pack(side=tk.RIGHT)
        
        # Alt texts
        for lang, text in texts.items():
            text_frame = ttk.Frame(img_frame)
            text_frame.pack(fill=tk.X, pady=2)
            
            lang_label = ttk.Label(text_frame, text=f"{lang}:", width=10)
            lang_label.pack(side=tk.LEFT)
            
            text_label = ttk.Label(text_frame, text=text, wraplength=500)
            text_label.pack(side=tk.LEFT, padx=(5, 0))
            
            copy_btn = ttk.Button(text_frame, text="Copy",
                                command=lambda t=text: pyperclip.copy(t))
            copy_btn.pack(side=tk.RIGHT)

    def show_image_preview(self, image_data):
        # Create new preview window
        preview_window = ImagePreviewWindow(self.root, image_data)
        self.preview_windows.append(preview_window)
        
        # Clean up closed windows
        self.preview_windows = [w for w in self.preview_windows if w.window.winfo_exists()]

    def check_queue(self):
        try:
            while True:
                msg_type, data = self.results_queue.get_nowait()
                
                if msg_type == "status":
                    self.update_status(data)
                elif msg_type == "error":
                    self.update_status(data, is_error=True)
                    self.process_btn.config(text="Generate Alt Texts", state="normal")
                    self.pause_btn.config(state="disabled")
                    self.website_processing = False
                elif msg_type == "progress":
                    self.progress_var.set(data)
                elif msg_type == "result":
                    img_url, texts = data
                    self.add_result(img_url, texts, is_single=False)
                elif msg_type == "show_preview":
                    self.show_image_preview(data)
                elif msg_type == "done":
                    self.update_status("Done!")
                    self.progress_var.set("")
                    self.process_btn.config(text="Generate Alt Texts", state="normal")
                    self.pause_btn.config(state="disabled")
                    self.website_processing = False
                elif msg_type == "single_result":
                    img_url, texts = data
                    self.add_result(img_url, texts, is_single=True)
                elif msg_type == "single_done":
                    self.update_single_status("Done!")
                    self.single_process_btn.config(text="Generate Alt Text", state="normal")
                    self.single_processing = False
                elif msg_type == "single_error":
                    self.update_single_status(data, is_error=True)
                    self.single_process_btn.config(text="Generate Alt Text", state="normal")
                    self.single_processing = False
                
                self.results_queue.task_done()
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)

    def run(self):
        self.root.mainloop()

def create_ui(image_texts=None):
    app = AltTextGeneratorUI()
    if image_texts:
        for img_url, texts in image_texts.items():
            app.add_result(img_url, texts)
    app.run()
