# Hyundai Music Optimizer

A cross-platform app (Windows/Linux) that processes MP3 files in selected folders, automatically detects albums, and completes metadata using the Spotify Web API. Features include automatic album processing, backup system, and progress tracking.

## Features
- **Automatic Album Detection**: Recognizes albums in folders and processes them as complete units
- **Spotify Integration**: Uses Spotify Web API to fetch accurate metadata and album covers
- **Smart Track Matching**: Intelligent matching of local tracks with Spotify album tracks
- **Backup System**: Creates automatic backups before processing (stored in program directory)
- **Progress Tracking**: Real-time progress display during processing
- **Album Sorting**: Sorts tracks by track number and renames files consistently
- **Cover Art**: Downloads and embeds high-quality album covers
- **Cross-Platform**: Works on Windows and Linux

## Setup Instructions

### 1. Install Dependencies
```bash
pip install spotipy mutagen pyqt5 requests
```

### 2. Configure Spotify API
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Log in with your Spotify account
3. Click "Create an App"
4. Fill in app name and description
5. Copy the **Client ID** and **Client Secret**

### 3. Setup Configuration
1. Copy `config.py.example` to `config.py`
2. Edit `config.py` and replace the placeholder values with your actual Spotify credentials:
   ```python
   SPOTIFY_CLIENT_ID = 'your_actual_client_id_here'
   SPOTIFY_CLIENT_SECRET = 'your_actual_client_secret_here'
   ```

### 4. Run the Application
```bash
python main.py
```

## Usage
1. **Select Folder**: Choose a folder containing your MP3 music collection
2. **Review Detection**: The app will scan and detect albums automatically
3. **Process Automatically**: Click "Process Automatically" to update all detected albums
4. **Backup Safety**: All changes are backed up and can be restored if needed

## File Structure
```
├── main.py                 # Main application
├── config.py              # Your API credentials (keep private!)
├── config.py.example      # Template for configuration
├── hyundai music icon.png # Application icon
├── backups/               # Automatic backups (created during processing)
└── README.md              # This file
```

## Important Notes
- **Keep `config.py` private** - Never share or commit your API credentials
- Backups are automatically created in the `backups/` folder within the program directory
- The app processes entire albums and organizes tracks by track number
- Album covers are downloaded and embedded in high quality
- Compatible with Windows Media Player and other music software

## Troubleshooting
- **"Configuration Error"**: Make sure `config.py` exists with valid Spotify credentials
- **API Rate Limits**: The app is optimized to minimize API calls, but very large collections might need processing in batches
- **Backup Recovery**: Use "Restore Backup" if you need to undo changes
