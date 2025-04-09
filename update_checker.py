import requests
import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from packaging import version

CURRENT_VERSION = "1.0.1"  # Updated version number to reflect recent changes
GITHUB_REPO = "babapotato/image_alt_generator"  # Updated with your GitHub username
VERSION_CHECK_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

class UpdateChecker:
    def __init__(self, parent=None):
        self.parent = parent

    def check_for_updates(self, silent=False):
        """
        Check for updates by comparing current version with latest release on GitHub.
        If silent is True, only show a message if an update is available.
        """
        try:
            response = requests.get(VERSION_CHECK_URL, timeout=5)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release['tag_name'].lstrip('v')
            
            if version.parse(latest_version) > version.parse(CURRENT_VERSION):
                if self.parent:
                    self._show_update_dialog(latest_version, latest_release['html_url'])
                return True, latest_version
            elif not silent:
                if self.parent:
                    messagebox.showinfo("No Updates", "You are running the latest version!")
                return False, CURRENT_VERSION
                
        except Exception as e:
            if not silent:
                if self.parent:
                    messagebox.showwarning("Update Check Failed", 
                                         f"Could not check for updates: {str(e)}")
                print(f"Update check failed: {str(e)}")
            return False, CURRENT_VERSION

    def _show_update_dialog(self, new_version, download_url):
        """Show a dialog informing the user about the available update."""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Update Available")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the window
        dialog.update_idletasks()
        width = 400
        height = 200
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, 
                 text=f"A new version ({new_version}) is available!",
                 font=('Helvetica', 12, 'bold')).pack(pady=(0, 10))
        
        ttk.Label(frame, 
                 text="Would you like to download the update?",
                 wraplength=350).pack(pady=(0, 20))
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, 
                  text="Download", 
                  command=lambda: self._open_download_page(download_url, dialog)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, 
                  text="Remind Me Later", 
                  command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, 
                  text="Skip This Version", 
                  command=lambda: self._skip_version(new_version, dialog)).pack(side=tk.RIGHT, padx=5)

    def _open_download_page(self, url, dialog):
        """Open the download page in the default web browser."""
        webbrowser.open(url)
        dialog.destroy()

    def _skip_version(self, version_to_skip, dialog):
        """Save the skipped version to a config file."""
        try:
            config = {'skipped_version': version_to_skip}
            with open('update_config.json', 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Failed to save skipped version: {str(e)}")
        dialog.destroy()

def check_for_updates_on_startup(parent_window=None):
    """
    Check for updates when the application starts.
    Only show a dialog if an update is available.
    """
    checker = UpdateChecker(parent_window)
    return checker.check_for_updates(silent=True) 