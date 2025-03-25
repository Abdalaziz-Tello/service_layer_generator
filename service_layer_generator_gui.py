import sys
import os
import requests
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from service_layer_generator import ServiceLayerGenerator

class SwaggerDownloader(Thread):
    def __init__(self, url, progress_callback, finished_callback, error_callback):
        super().__init__()
        self.url = url
        self.progress_callback = progress_callback
        self.finished_callback = finished_callback
        self.error_callback = error_callback

    def run(self):
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
            
            # Get total size for progress calculation
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            downloaded = 0
            
            with open(temp_file.name, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    if total_size:
                        progress = int((downloaded / total_size) * 100)
                        self.progress_callback(progress)
            
            self.finished_callback(temp_file.name)
        except Exception as e:
            self.error_callback(str(e))

class ServiceLayerGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Flutter Service Layer Generator")
        self.root.geometry("800x600")
        
        # Variables
        self.file_path = None
        self.url_var = tk.StringVar()
        
        # Create main container
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Local file tab
        local_file_frame = ttk.Frame(notebook, padding="10")
        notebook.add(local_file_frame, text="Local File")
        
        # Drag and drop area (simulated with a button)
        self.file_label = ttk.Label(
            local_file_frame,
            text="Click to select OpenAPI JSON file",
            padding=20,
            relief="solid",
            borderwidth=1
        )
        self.file_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.file_label.bind('<Button-1>', self.select_file)
        
        # Online URL tab
        url_frame = ttk.Frame(notebook, padding="10")
        notebook.add(url_frame, text="Online URL")
        
        # URL input
        ttk.Label(url_frame, text="Swagger URL:").grid(row=0, column=0, sticky=tk.W)
        url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=50)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            url_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.progress_bar.grid_remove()  # Hide initially
        
        # Output directory selection
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky=tk.W)
        self.output_path = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "flutter_service_layer"))
        output_entry = ttk.Entry(output_frame, textvariable=self.output_path, width=50)
        output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        browse_button = ttk.Button(output_frame, text="Browse", command=self.select_output_directory)
        browse_button.grid(row=0, column=2, padx=5)
        
        # Generate button
        self.generate_button = ttk.Button(
            main_frame,
            text="Generate Service Layer",
            command=self.generate_service_layer
        )
        self.generate_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=2)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Bind URL entry changes
        self.url_var.trace_add('write', self.on_url_changed)

    def select_file(self, event=None):
        file_path = filedialog.askopenfilename(
            title="Select OpenAPI JSON File",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            self.file_path = file_path
            self.file_label.config(text=f"Selected: {os.path.basename(file_path)}")
            self.update_generate_button()

    def select_output_directory(self):
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_path.get()
        )
        if directory:
            self.output_path.set(directory)
            self.update_generate_button()

    def on_url_changed(self, *args):
        url = self.url_var.get().strip()
        if url and not self.file_path:
            self.download_swagger(url)

    def download_swagger(self, url):
        self.progress_bar.grid()  # Show progress bar
        self.progress_var.set(0)
        self.generate_button.state(['disabled'])
        self.status_label.config(text="Downloading Swagger specification...")
        
        downloader = SwaggerDownloader(
            url,
            self.update_progress,
            self.on_download_finished,
            self.on_download_error
        )
        downloader.start()

    def update_progress(self, value):
        self.progress_var.set(value)
        self.root.update_idletasks()

    def on_download_finished(self, file_path):
        self.progress_bar.grid_remove()  # Hide progress bar
        self.file_path = file_path
        self.file_label.config(text=f"Downloaded: {os.path.basename(file_path)}")
        self.status_label.config(text="Swagger specification downloaded successfully!")
        self.update_generate_button()

    def on_download_error(self, error_message):
        self.progress_bar.grid_remove()  # Hide progress bar
        self.status_label.config(text=f"Error: {error_message}")
        messagebox.showerror("Error", f"Failed to download Swagger specification: {error_message}")

    def generate_service_layer(self):
        if not self.file_path:
            messagebox.showwarning("Error", "Please select an OpenAPI JSON file or enter a Swagger URL")
            return
            
        if not self.output_path.get():
            messagebox.showwarning("Error", "Please select an output directory")
            return
            
        try:
            generator = ServiceLayerGenerator(
                self.file_path,
                self.output_path.get()
            )
            generator.generate()
            self.status_label.config(text="Service layer generated successfully!")
            messagebox.showinfo(
                "Success",
                f"Service layer generated successfully in:\n{self.output_path.get()}"
            )
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}")
            messagebox.showerror("Error", str(e))

    def update_generate_button(self):
        has_file = bool(self.file_path)
        has_output = bool(self.output_path.get())
        self.generate_button.state(['!disabled' if has_file and has_output else 'disabled'])

def main():
    root = tk.Tk()
    app = ServiceLayerGeneratorGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main() 