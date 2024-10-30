import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
import base64
from dotenv import load_dotenv

class APIKeyManager:
    def __init__(self):
        self.key_file = Path.home() / '.calculator_api_key'
        self.key_encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.key_encryption_key)
        
    def _get_or_create_encryption_key(self):
        key_path = Path.home() / '.calculator_key'
        if not key_path.exists():
            key = Fernet.generate_key()
            with open(key_path, 'wb') as f:
                f.write(key)
            return key
        with open(key_path, 'rb') as f:
            return f.read()

    def save_api_key(self, api_key):
        """Encrypt and save API key"""
        encrypted_key = self.fernet.encrypt(api_key.encode())
        with open(self.key_file, 'wb') as f:
            f.write(encrypted_key)

    def load_api_key(self):
        """Load and decrypt API key"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'rb') as f:
                    encrypted_key = f.read()
                return self.fernet.decrypt(encrypted_key).decode()
            return None
        except Exception:
            return None

    def delete_api_key(self):
        """Delete stored API key"""
        if self.key_file.exists():
            self.key_file.unlink()

class APIKeyDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Gemini API Key Setup")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.api_key = None
        self.key_manager = APIKeyManager()
        
        self.create_widgets()
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'+{x}+{y}')

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Instructions
        instructions = ttk.Label(
            main_frame,
            text="Please enter your Gemini API key.\nThis will be stored securely for future use.",
            justify=tk.CENTER,
            wraplength=350
        )
        instructions.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # API Key entry
        self.api_key_var = tk.StringVar()
        api_key_entry = ttk.Entry(main_frame, textvariable=self.api_key_var, width=40)
        api_key_entry.grid(row=1, column=0, columnspan=2, pady=(0, 20))

        # Buttons
        ttk.Button(
            main_frame, 
            text="Test and Save", 
            command=self.test_and_save_key
        ).grid(row=2, column=0, padx=5)
        
        ttk.Button(
            main_frame, 
            text="Cancel", 
            command=self.dialog.destroy
        ).grid(row=2, column=1, padx=5)

        # Status label
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=(20, 0))

    def test_api_key(self, api_key):
        """Test if the API key is valid"""
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": api_key
            }
            data = {
                "contents": [{
                    "parts": [{
                        "text": "Return only the number 1"
                    }]
                }]
            }
            
            response = requests.post(url, headers=headers, json=data)
            return response.status_code == 200
        except Exception:
            return False

    def test_and_save_key(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            self.status_label.config(
                text="Please enter an API key",
                foreground="red"
            )
            return

        self.status_label.config(text="Testing API key...", foreground="black")
        self.dialog.update()

        if self.test_api_key(api_key):
            self.key_manager.save_api_key(api_key)
            self.api_key = api_key
            self.status_label.config(
                text="API key validated and saved successfully!",
                foreground="green"
            )
            self.dialog.after(1500, self.dialog.destroy)
        else:
            self.status_label.config(
                text="Invalid API key. Please check and try again.",
                foreground="red"
            )

class CalculatorAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        
    def call_api(self, num1, num2, operation):
        """Make API call to Gemini"""
        try:
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            data = {
                "contents": [{
                    "parts": [{
                        "text": f"Calculate {num1} {operation} {num2} and return only the numerical result"
                    }]
                }]
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract numerical result from API response
                return float(result['candidates'][0]['content']['parts'][0]['text'])
            else:
                raise Exception(f"API Error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"API call failed: {str(e)}")

class CalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Calculator with Gemini API")
        self.root.geometry("500x600")
        
        self.key_manager = APIKeyManager()
        self.setup_api()

    def setup_api(self):
        # Try to load existing API key
        api_key = self.key_manager.load_api_key()
        
        if not api_key:
            # Show API key dialog
            dialog = APIKeyDialog(self.root)
            self.root.wait_window(dialog.dialog)
            api_key = dialog.api_key
            
            if not api_key:
                messagebox.showerror(
                    "Error",
                    "No valid API key provided. Application will close."
                )
                self.root.destroy()
                return
        
        # Initialize API client and create main UI
        self.api_client = CalculatorAPI(api_key)
        self.create_main_ui()

    def create_main_ui(self):
        # Create main UI (previous calculator UI code)
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # API Status indicator
        self.status_frame = ttk.Frame(main_frame, padding="5")
        self.status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.api_status = ttk.Label(
            self.status_frame, 
            text="API Status: Connected", 
            foreground="green"
        )
        self.api_status.grid(row=0, column=0, pady=5)
        
        ttk.Button(
            self.status_frame,
            text="Change API Key",
            command=self.change_api_key
        ).grid(row=0, column=1, padx=5)
        
        # Input fields
        ttk.Label(main_frame, text="First Number:").grid(
            row=1, column=0, pady=5, sticky=tk.W
        )
        self.num1_entry = ttk.Entry(main_frame, width=20)
        self.num1_entry.grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(main_frame, text="Second Number:").grid(
            row=2, column=0, pady=5, sticky=tk.W
        )
        self.num2_entry = ttk.Entry(main_frame, width=20)
        self.num2_entry.grid(row=2, column=1, pady=5, padx=5)
        
        # Operations frame
        operations_frame = ttk.LabelFrame(main_frame, text="Operations", padding="10")
        operations_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        operations = [("Add", "+"), ("Subtract", "-"), 
                     ("Multiply", "*"), ("Divide", "/")]
        
        for i, (text, op) in enumerate(operations):
            ttk.Button(
                operations_frame,
                text=text,
                command=lambda o=op: self.calculate(o)
            ).grid(row=i//2, column=i%2, padx=5, pady=5)
        
        # Result frame
        result_frame = ttk.LabelFrame(main_frame, text="Result", padding="10")
        result_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.result_label = ttk.Label(result_frame, text="Result will appear here")
        self.result_label.grid(row=0, column=0, pady=5)
        
        self.loading_label = ttk.Label(result_frame, text="")
        self.loading_label.grid(row=1, column=0, pady=5)
        
        # History frame
        history_frame = ttk.LabelFrame(
            main_frame, text="Calculation History", padding="10"
        )
        history_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.history_text = tk.Text(history_frame, height=8, width=40)
        self.history_text.grid(row=0, column=0, pady=5)

    def change_api_key(self):
        """Allow user to change API key"""
        dialog = APIKeyDialog(self.root)
        self.root.wait_window(dialog.dialog)
        if dialog.api_key:
            self.api_client = CalculatorAPI(dialog.api_key)

    def calculate(self, operation):
        """Perform calculation using the API"""
        try:
            num1 = float(self.num1_entry.get())
            num2 = float(self.num2_entry.get())
            
            if operation == "/" and num2 == 0:
                messagebox.showerror("Error", "Cannot divide by zero")
                return
            
            self.loading_label.config(text="Calculating...")
            self.root.update()
            
            result = self.api_client.call_api(num1, num2, operation)
            
            self.result_label.config(text=f"{result:.2f}")
            self.history_text.insert(
                tk.END,
                f"{num1} {operation} {num2} = {result:.2f}\n"
            )
            self.history_text.see(tk.END)
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.loading_label.config(text="")

if __name__ == "__main__":
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()