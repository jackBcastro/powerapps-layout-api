import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, List, Optional, Tuple
import customtkinter as ctk
from pytube import YouTube

# Set appearance mode and default color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"

class YouTubeAudioDownloader:
    """Main application class for YouTube Audio Downloader."""
    
    def __init__(self, root):
        """
        Initialize the application.
        
        Args:
            root: The root window for the application
        """
        self.root = root
        self.root.title("YouTube Audio Downloader")
        self.root.geometry("600x450")
        self.root.resizable(True, True)
        
        # Default download directory (user's Downloads folder)
        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        
        # YouTube object placeholder
        self.yt = None
        
        # Audio streams from YouTube
        self.audio_streams = []
        
        # Create the UI elements
        self._create_ui()
    
    def _create_ui(self):
        """Create and configure all UI elements."""
        # Create a main frame
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Application title
        title_label = ctk.CTkLabel(
            self.main_frame, 
            text="YouTube Audio Downloader", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # URL Entry Frame
        url_frame = ctk.CTkFrame(self.main_frame)
        url_frame.pack(fill=tk.X, pady=10)
        
        url_label = ctk.CTkLabel(url_frame, text="YouTube URL:")
        url_label.pack(side=tk.LEFT, padx=10)
        
        self.url_entry = ctk.CTkEntry(url_frame, width=350)
        self.url_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        check_button = ctk.CTkButton(
            url_frame, 
            text="Check", 
            command=self.check_url,
            width=80
        )
        check_button.pack(side=tk.RIGHT, padx=10)
        
        # Video Information Frame
        self.info_frame = ctk.CTkFrame(self.main_frame)
        self.info_frame.pack(fill=tk.X, pady=10)
        
        # Video title (initially hidden)
        self.title_var = tk.StringVar()
        self.title_label = ctk.CTkLabel(
            self.info_frame, 
            textvariable=self.title_var,
            font=ctk.CTkFont(weight="bold")
        )
        self.title_label.pack(pady=10, padx=10, anchor=tk.W)
        
        # Audio Quality Selection Frame
        self.quality_frame = ctk.CTkFrame(self.main_frame)
        self.quality_frame.pack(fill=tk.X, pady=10)
        
        quality_label = ctk.CTkLabel(self.quality_frame, text="Audio Quality:")
        quality_label.pack(side=tk.LEFT, padx=10)
        
        self.quality_var = tk.StringVar()
        self.quality_dropdown = ctk.CTkOptionMenu(
            self.quality_frame,
            variable=self.quality_var,
            values=["No audio streams available"],
            state="disabled"
        )
        self.quality_dropdown.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Download Location Frame
        location_frame = ctk.CTkFrame(self.main_frame)
        location_frame.pack(fill=tk.X, pady=10)
        
        location_label = ctk.CTkLabel(location_frame, text="Save to:")
        location_label.pack(side=tk.LEFT, padx=10)
        
        self.location_var = tk.StringVar(value=self.download_dir)
        location_entry = ctk.CTkEntry(
            location_frame, 
            textvariable=self.location_var,
            width=350
        )
        location_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        browse_button = ctk.CTkButton(
            location_frame, 
            text="Browse", 
            command=self.browse_location,
            width=80
        )
        browse_button.pack(side=tk.RIGHT, padx=10)
        
        # Progress Bar
        progress_frame = ctk.CTkFrame(self.main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        self.progress_bar.set(0)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ctk.CTkLabel(
            progress_frame, 
            textvariable=self.status_var
        )
        status_label.pack(pady=5)
        
        # Download Button
        self.download_button = ctk.CTkButton(
            self.main_frame, 
            text="Download", 
            command=self.download_audio,
            state="disabled",
            height=40,
            font=ctk.CTkFont(size=16)
        )
        self.download_button.pack(pady=20)
        
        # Hide information and progress frames initially
        self.info_frame.pack_forget()
        
        # Initialize the UI
        self.url_entry.focus_set()
    
    def browse_location(self):
        """Open a directory browser dialog to select download location."""
        directory = filedialog.askdirectory(initialdir=self.download_dir)
        if directory:  # If a directory was selected (not cancelled)
            self.download_dir = directory
            self.location_var.set(directory)
    
    def validate_youtube_url(self, url: str) -> bool:
        """
        Validate if the provided URL is a valid YouTube URL.
        
        Args:
            url: The URL to validate
            
        Returns:
            bool: True if the URL is valid, False otherwise
        """
        # YouTube URL regex pattern
        youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        
        match = re.match(youtube_regex, url)
        return match is not None
    
    def check_url(self):
        """Validate the URL and fetch video information if valid."""
        url = self.url_entry.get().strip()
        
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL")
            return
        
        if not self.validate_youtube_url(url):
            messagebox.showerror("Error", "Invalid YouTube URL")
            return
        
        # Update status
        self.status_var.set("Fetching video information...")
        self.root.update_idletasks()
        
        # Start a thread to fetch video info to prevent UI freeze
        threading.Thread(target=self._fetch_video_info, args=(url,), daemon=True).start()
    
    def _fetch_video_info(self, url: str):
        """
        Fetch video information in a separate thread.
        
        Args:
            url: The YouTube URL to process
        """
        try:
            # Create YouTube object with retry mechanism
            try_count = 0
            max_retries = 3
            
            while try_count < max_retries:
                try:
                    self.yt = YouTube(
                        url,
                        on_progress_callback=self._on_progress,
                        on_complete_callback=self._on_complete
                    )
                    break  # Success, exit the retry loop
                except Exception as retry_e:
                    try_count += 1
                    if try_count >= max_retries:
                        raise retry_e  # Re-raise if all retries failed
                    # Wait before retrying (increasing delay with each retry)
                    import time
                    time.sleep(1 * try_count)
            
            # Get available audio streams
            self.audio_streams = self._get_audio_streams()
            
            # Update UI on the main thread
            self.root.after(0, self._update_ui_with_video_info)
            
        except Exception as e:
            # Handle exceptions on the main thread
            error_message = str(e)
            if "HTTP Error 400" in error_message:
                error_message = "HTTP Error 400: Bad Request. This could be due to:\n" + \
                                "- YouTube API changes\n" + \
                                "- Network connectivity issues\n" + \
                                "- Invalid or restricted video URL\n\n" + \
                                "Try updating pytube with: pip install --upgrade pytube"
            self.root.after(0, lambda: self._show_error(error_message))
    
    def _get_audio_streams(self) -> List[Tuple[str, str]]:
        """
        Get available audio streams for the video.
        
        Returns:
            List of tuples containing (stream_description, itag)
        """
        streams = []
        
        # Filter audio-only streams
        audio_streams = self.yt.streams.filter(only_audio=True).order_by('abr').desc()
        
        for stream in audio_streams:
            # Get attributes
            abr = stream.abr if stream.abr else "Unknown bitrate"
            mime_type = stream.mime_type if stream.mime_type else "Unknown format"
            
            # Create description
            description = f"{abr} - {mime_type}"
            
            streams.append((description, str(stream.itag)))
        
        return streams
    
    def _update_ui_with_video_info(self):
        """Update UI with fetched video information."""
        if not self.yt or not self.audio_streams:
            self._show_error("Failed to fetch video information")
            return
        
        # Display video title
        self.title_var.set(self.yt.title)
        
        # Show info frame
        self.info_frame.pack(fill=tk.X, pady=10, after=self.url_entry.winfo_parent())
        
        # Update quality dropdown
        if self.audio_streams:
            # Extract descriptions for dropdown
            descriptions = [desc for desc, _ in self.audio_streams]
            self.quality_dropdown.configure(values=descriptions, state="normal")
            self.quality_var.set(descriptions[0])  # Select highest quality by default
        else:
            self.quality_dropdown.configure(values=["No audio streams available"], state="disabled")
            self.quality_var.set("No audio streams available")
        
        # Enable download button
        self.download_button.configure(state="normal")
        
        # Update status
        self.status_var.set("Ready to download")
        self.progress_bar.set(0)
    
    def download_audio(self):
        """Start the audio download process."""
        if not self.yt or not self.audio_streams:
            messagebox.showerror("Error", "No video information available")
            return
        
        # Get selected quality
        selected_quality = self.quality_var.get()
        if selected_quality == "No audio streams available":
            messagebox.showerror("Error", "No audio streams available for this video")
            return
        
        # Find the selected stream itag
        selected_itag = None
        for desc, itag in self.audio_streams:
            if desc == selected_quality:
                selected_itag = itag
                break
        
        if not selected_itag:
            messagebox.showerror("Error", "Failed to find selected audio stream")
            return
        
        # Disable UI controls during download
        self._disable_controls()
        
        # Update status
        self.status_var.set("Starting download...")
        self.progress_bar.set(0)
        
        # Start download in a separate thread
        threading.Thread(
            target=self._download_audio_thread,
            args=(selected_itag,),
            daemon=True
        ).start()
    
    def _download_audio_thread(self, itag: str):
        """
        Download audio in a separate thread.
        
        Args:
            itag: The itag of the stream to download
        """
        try:
            # Get the stream by itag
            stream = self.yt.streams.get_by_itag(int(itag))
            if not stream:
                self.root.after(0, lambda: self._show_error("Selected stream is not available"))
                return
            
            # Get file extension
            extension = stream.mime_type.split('/')[-1]
            
            # Download the audio file
            self.root.after(0, lambda: self.status_var.set("Downloading..."))
            stream.download(
                output_path=self.download_dir,
                filename=f"{self.yt.title}.{extension}"
            )
            
            # Note: The on_complete_callback will handle completion
            
        except Exception as e:
            # Handle exceptions on the main thread
            error_message = str(e)
            self.root.after(0, lambda: self._show_error(error_message))
            self.root.after(0, self._enable_controls)
    
    def _on_progress(self, stream, chunk, bytes_remaining):
        """
        Callback for download progress.
        
        Args:
            stream: The stream being downloaded
            chunk: The chunk that was just downloaded
            bytes_remaining: Bytes remaining to be downloaded
        """
        # Calculate progress percentage
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = bytes_downloaded / total_size
        
        # Update UI on the main thread
        self.root.after(0, lambda: self._update_progress(percentage))
    
    def _update_progress(self, percentage: float):
        """
        Update progress bar on the main thread.
        
        Args:
            percentage: Download progress (0.0 to 1.0)
        """
        self.progress_bar.set(percentage)
        
        # Update status text with percentage
        self.status_var.set(f"Downloading... {int(percentage * 100)}%")
    
    def _on_complete(self, stream, file_path):
        """
        Callback when download is complete.
        
        Args:
            stream: The stream that was downloaded
            file_path: Path to the downloaded file
        """
        # Update UI on the main thread
        self.root.after(0, lambda: self._handle_download_complete(file_path))
    
    def _handle_download_complete(self, file_path: str):
        """
        Handle download completion on the main thread.
        
        Args:
            file_path: Path to the downloaded file
        """
        # Normalize file path for display
        file_path = os.path.normpath(file_path)
        
        # Update progress and status
        self.progress_bar.set(1.0)
        self.status_var.set("Download complete!")
        
        # Re-enable controls
        self._enable_controls()
        
        # Show success message
        messagebox.showinfo(
            "Download Complete",
            f"Audio downloaded successfully to:\n{file_path}"
        )
    
    def _show_error(self, error_message: str):
        """
        Show error message and update status.
        
        Args:
            error_message: The error message to display
        """
        self.status_var.set("Error occurred")
        messagebox.showerror("Error", error_message)
    
    def _disable_controls(self):
        """Disable UI controls during download."""
        self.url_entry.configure(state="disabled")
        self.quality_dropdown.configure(state="disabled")
        self.download_button.configure(state="disabled")
    
    def _enable_controls(self):
        """Re-enable UI controls after download."""
        self.url_entry.configure(state="normal")
        self.quality_dropdown.configure(state="normal")
        self.download_button.configure(state="normal")


def main():
    """Application entry point."""
    # Create root window
    root = ctk.CTk()
    
    # Create application
    app = YouTubeAudioDownloader(root)
    
    # Start the application main loop
    root.mainloop()


if __name__ == "__main__":
    main()