import sys
import os
import re
import json
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QComboBox, QFileDialog, QProgressBar, QMessageBox,
    QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap

# Google API client libraries
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import pickle

# For downloading
import yt_dlp

# YouTube API constants
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secrets.json"

class AuthManager:
    """Manages authentication with YouTube API"""
    
    def __init__(self):
        self.credentials = None
        self.youtube = None
        
    def get_authenticated_service(self):
        """Authenticates with YouTube API and returns the service"""
        # Load saved credentials if they exist
        if os.path.exists("token.pickle"):
            with open("token.pickle", "rb") as token:
                self.credentials = pickle.load(token)
                
        # If credentials don't exist or are invalid, get new ones
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                # Check if client secrets file exists
                if not os.path.exists(CLIENT_SECRETS_FILE):
                    return None, "Client secrets file not found. Please set up OAuth 2.0 credentials."
                
                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, SCOPES)
                self.credentials = flow.run_local_server(port=0)
                
            # Save the credentials for future use
            with open("token.pickle", "wb") as token:
                pickle.dump(self.credentials, token)
                
        # Build the YouTube API service
        self.youtube = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=self.credentials)
            
        return self.youtube, None


class VideoDownloadThread(QThread):
    """Thread for downloading videos"""
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, url, format_id, save_path):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.save_path = save_path
        
    def progress_hook(self, d):
        """Process progress updates from yt-dlp"""
        if d['status'] == 'downloading':
            # Calculate percentage
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            
            if total > 0:
                percentage = int(downloaded / total * 100)
                self.progress_signal.emit(
                    percentage, 
                    f"Downloading: {percentage}% ({self.format_human_size(downloaded)} of {self.format_human_size(total)})"
                )
        elif d['status'] == 'finished':
            self.progress_signal.emit(100, "Processing downloaded file...")
            
    def format_human_size(self, size):
        """Formats byte size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024
        
    def run(self):
        """Main download function"""
        try:
            # yt-dlp options
            ydl_opts = {
                'format': self.format_id,
                'outtmpl': os.path.join(self.save_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
            }
            
            # Start download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                filename = ydl.prepare_filename(info)
                
            self.finished_signal.emit(f"Download complete: {os.path.basename(filename)}")
            
        except Exception as e:
            self.error_signal.emit(f"Error: {str(e)}")


class YouTubeDataAPIDownloader(QWidget):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Data API Downloader")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        self.auth_manager = AuthManager()
        self.youtube = None
        self.video_info = None
        self.video_formats = []
        
        self.setup_ui()
        self.check_api_credentials()
        
    def setup_ui(self):
        """Set up the user interface"""
        main_layout = QVBoxLayout()
        
        # Title and intro section
        title_label = QLabel("YouTube Data API Downloader")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        intro_text = QLabel("This application uses the official YouTube Data API and yt-dlp to download videos.")
        
        # URL input section
        url_layout = QHBoxLayout()
        url_label = QLabel("YouTube URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        analyze_btn = QPushButton("Analyze")
        analyze_btn.clicked.connect(self.analyze_video)
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(analyze_btn)
        
        # Video info section
        info_layout = QVBoxLayout()
        info_label = QLabel("Video Information:")
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(200)
        
        info_layout.addWidget(info_label)
        info_layout.addWidget(self.info_text)
        
        # Format selection section
        format_layout = QHBoxLayout()
        format_label = QLabel("Select Format:")
        self.format_combo = QComboBox()
        self.format_combo.setEnabled(False)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        
        # Download section
        download_layout = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.start_download)
        
        download_layout.addStretch()
        download_layout.addWidget(self.download_btn)
        
        # Progress section
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.status_label = QLabel("Ready")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        
        # Add all layouts to main layout
        main_layout.addWidget(title_label)
        main_layout.addWidget(intro_text)
        main_layout.addSpacing(10)
        main_layout.addLayout(url_layout)
        main_layout.addSpacing(10)
        main_layout.addLayout(info_layout)
        main_layout.addLayout(format_layout)
        main_layout.addLayout(download_layout)
        main_layout.addLayout(progress_layout)
        
        self.setLayout(main_layout)
        
    def check_api_credentials(self):
        """Check if API credentials are available"""
        if not os.path.exists(CLIENT_SECRETS_FILE):
            QMessageBox.warning(
                self, 
                "API Credentials Missing", 
                f"Please download and place your OAuth 2.0 client credentials as '{CLIENT_SECRETS_FILE}' "
                "in the same directory as this application.\n\n"
                "See: https://developers.google.com/youtube/v3/quickstart/python"
            )
    
    def extract_video_id(self, url):
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Standard and shared URLs
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',  # Short URLs
            r'(?:embed\/)([0-9A-Za-z_-]{11})',  # Embed URLs
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        return None
        
    def analyze_video(self):
        """Fetch and display video information from YouTube Data API"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return
            
        video_id = self.extract_video_id(url)
        if not video_id:
            QMessageBox.warning(self, "Error", "Invalid YouTube URL format")
            return
            
        self.status_label.setText("Authenticating with YouTube API...")
        QApplication.processEvents()
        
        # Authenticate with YouTube API
        if not self.youtube:
            self.youtube, error = self.auth_manager.get_authenticated_service()
            if error:
                QMessageBox.critical(self, "Authentication Error", error)
                return
                
        # Fetch video information
        self.status_label.setText("Fetching video information...")
        QApplication.processEvents()
        
        try:
            # Get video details from YouTube Data API
            request = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                QMessageBox.warning(self, "Error", "Video not found or is private")
                return
                
            video_data = response['items'][0]
            self.video_info = {
                'id': video_data['id'],
                'title': video_data['snippet']['title'],
                'channel': video_data['snippet']['channelTitle'],
                'published': video_data['snippet']['publishedAt'],
                'views': video_data['statistics'].get('viewCount', 'N/A'),
                'likes': video_data['statistics'].get('likeCount', 'N/A'),
                'duration': video_data['contentDetails']['duration'],
                'url': f"https://www.youtube.com/watch?v={video_id}"
            }
            
            # Show video information
            info_text = (
                f"Title: {self.video_info['title']}\n"
                f"Channel: {self.video_info['channel']}\n"
                f"Published: {self.video_info['published']}\n"
                f"Views: {self.video_info['views']}\n"
                f"Likes: {self.video_info['likes']}\n"
                f"Duration: {self.video_info['duration']}\n"
                f"Video ID: {self.video_info['id']}"
            )
            self.info_text.setText(info_text)
            
            # Now get download formats from yt-dlp
            self.status_label.setText("Fetching available formats...")
            QApplication.processEvents()
            
            # Get available formats using yt-dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Update video info with thumbnail
                if 'thumbnail' in info:
                    self.video_info['thumbnail'] = info['thumbnail']
                    
                # Filter and organize formats
                self.video_formats = []
                
                # Add combined formats first (video+audio)
                for f in info.get('formats', []):
                    if f.get('vcodec', 'none') != 'none' and f.get('acodec', 'none') != 'none':
                        format_note = f.get('format_note', '')
                        file_size = self.format_human_size(f.get('filesize') or f.get('filesize_approx', 0))
                        resolution = f"{f.get('width', '?')}x{f.get('height', '?')}"
                        ext = f.get('ext', '?')
                        
                        format_name = f"{resolution} - {format_note} ({ext}, {file_size})"
                        self.video_formats.append({
                            'format_id': f['format_id'],
                            'name': format_name,
                            'quality': f.get('quality', 0)
                        })
                
                # Add best audio only as an option
                audio_formats = [f for f in info.get('formats', []) if 
                                f.get('vcodec', '') == 'none' and f.get('acodec', 'none') != 'none']
                if audio_formats:
                    best_audio = max(audio_formats, key=lambda x: x.get('quality', 0))
                    format_name = f"Audio only - {best_audio.get('format_note', '')} ({best_audio.get('ext', '?')})"
                    self.video_formats.append({
                        'format_id': best_audio['format_id'],
                        'name': format_name,
                        'quality': -1  # Place at the end
                    })
                
                # Sort formats by quality (highest first)
                self.video_formats.sort(key=lambda x: x['quality'], reverse=True)
                
                # Populate format combo box
                self.format_combo.clear()
                for fmt in self.video_formats:
                    self.format_combo.addItem(fmt['name'])
                
                self.format_combo.setEnabled(True)
                self.download_btn.setEnabled(True)
                self.status_label.setText("Ready to download")
            
        except googleapiclient.errors.HttpError as e:
            error_content = json.loads(e.content)
            error_message = error_content['error']['message']
            QMessageBox.critical(self, "YouTube API Error", f"API Error: {error_message}")
            self.status_label.setText(f"Error: {error_message}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error analyzing video: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")
            
    def format_human_size(self, size):
        """Formats byte size to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024 or unit == 'GB':
                return f"{size:.1f} {unit}"
            size /= 1024
            
    def start_download(self):
        """Initiate the download process"""
        if not self.video_formats:
            return
            
        idx = self.format_combo.currentIndex()
        if idx < 0 or idx >= len(self.video_formats):
            return
            
        selected_format = self.video_formats[idx]
        
        # Ask user for save location
        save_path = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        
        if not save_path:
            return  # User canceled
            
        # Start download thread
        self.download_thread = VideoDownloadThread(
            self.video_info['url'], 
            selected_format['format_id'], 
            save_path
        )
        
        # Connect signals
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.error_signal.connect(self.download_error)
        
        # Disable UI elements during download
        self.download_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.format_combo.setEnabled(False)
        
        # Start the thread
        self.status_label.setText("Downloading...")
        self.download_thread.start()
        
    def update_progress(self, percentage, status_text):
        """Update progress bar and status"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(status_text)
        
    def download_finished(self, message):
        """Handle download completion"""
        self.status_label.setText(message)
        self.progress_bar.setValue(100)
        
        # Re-enable UI elements
        self.download_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.format_combo.setEnabled(True)
        
        QMessageBox.information(self, "Success", message)
        
    def download_error(self, error_message):
        """Handle download errors"""
        self.status_label.setText(error_message)
        
        # Re-enable UI elements
        self.download_btn.setEnabled(True)
        self.url_input.setEnabled(True)
        self.format_combo.setEnabled(True)
        
        QMessageBox.critical(self, "Error", error_message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # For development only
    window = YouTubeDataAPIDownloader()
    window.show()
    sys.exit(app.exec_())