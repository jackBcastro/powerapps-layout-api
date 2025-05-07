#!/bin/bash

# Move to your project directory
cd /Users/andy/Documents/PythonPlayground || exit

# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate the environment
source venv/bin/activate

# 3. Upgrade pip and install dependencies
pip install --upgrade pip
pip install yt-dlp mutagen

# 4. Run your Python GUI app (replace with your actual script filename if needed)
python youtube_audio_downloader.py

# 5. (Optional) Open VS Code in the folder
if command -v code &> /dev/null; then
  code .
fi
