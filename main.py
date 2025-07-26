import os
import re
import sys
import requests
import shutil
import json
from datetime import datetime
from PyQt5 import QtWidgets
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

# Import API credentials from config file
try:
    from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
except ImportError:
    print("Error: config.py file not found!")
    print("Please create a config.py file with your Spotify API credentials.")
    print("See config.py.example for the required format.")
    SPOTIFY_CLIENT_ID = None
    SPOTIFY_CLIENT_SECRET = None

class Mp3MetadataApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # Check if API credentials are available
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET or SPOTIFY_CLIENT_ID == 'YOUR_CLIENT_ID_HERE':
            QtWidgets.QMessageBox.critical(
                self, 'Configuration Error',
                'Spotify API credentials not configured!\n\n'
                'Please edit config.py and add your Spotify API credentials.\n'
                'Visit https://developer.spotify.com/dashboard/ to get your credentials.'
            )
            sys.exit(1)
        
        self.spotify = Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))

    def init_ui(self):
        self.setWindowTitle('Hyundai Music Optimizer')
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), 'hyundai music icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
            # For custom icon, we need QtGui
            from PyQt5 import QtGui
            self.setWindowIcon(QtGui.QIcon(icon_path))
        
        self.setMinimumSize(800, 600)  # Enlarge window
        self.layout = QtWidgets.QVBoxLayout()
        self.folder_btn = QtWidgets.QPushButton('Select Folder')
        self.folder_btn.clicked.connect(self.select_folder)
        self.folder_tree = QtWidgets.QTreeWidget()
        self.folder_tree.setHeaderLabels(['Folder/File', 'Album Detected', 'Status'])
        self.folder_tree.setColumnWidth(0, 400)  # Wider for longer names
        self.folder_tree.setColumnWidth(1, 120)
        self.folder_tree.setColumnWidth(2, 150)
        self.apply_btn = QtWidgets.QPushButton('Process Automatically')
        self.apply_btn.clicked.connect(self.auto_process_albums)
        self.restore_btn = QtWidgets.QPushButton('Restore Backup')
        self.restore_btn.clicked.connect(self.restore_backup)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        self.layout.addWidget(self.folder_btn)
        self.layout.addWidget(QtWidgets.QLabel('Found music folders and files:'))
        self.layout.addWidget(self.folder_tree)
        
        # Buttons side by side
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.restore_btn)
        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.progress)
        self.setLayout(self.layout)

    def select_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')
        if folder:
            self.folder_tree.clear()
            self.selected_folder = folder
            
            # Show progress during loading
            self.progress.setVisible(True)
            self.progress.setRange(0, 0)  # Indeterminate progress
            QtWidgets.QApplication.processEvents()  # Update UI
            
            self.populate_tree(folder)
            
            self.progress.setVisible(False)

    def populate_tree(self, root_folder):
        self._add_folder_item(self.folder_tree, root_folder)

    def _add_folder_item(self, parent, folder_path):
        mp3_files = self.find_mp3_files(folder_path, only_current=True)
        if not mp3_files:
            return
            
        # Sammle Spotify-Daten für alle MP3s in diesem Ordner
        spotify_albums = set()  # Album-Namen sammeln
        spotify_artists = set()  # Künstler sammeln
        for mp3_path in mp3_files:
            try:
                # Versuche zuerst existierende Metadaten zu lesen
                audio = MP3(mp3_path, ID3=EasyID3)
                existing_album = audio.get('album', [''])[0]
                existing_artist = audio.get('artist', [''])[0]
                if existing_album and existing_artist:
                    spotify_albums.add(existing_album)
                    spotify_artists.add(existing_artist)
                    print(f"Album from metadata: '{existing_artist} - {existing_album}'")
                else:
                    # Search Spotify for the track
                    filename = os.path.splitext(os.path.basename(mp3_path))[0]
                    clean_name = re.sub(r'\s*\([^)]*\)|\s*\[[^]]*\]', '', filename)
                    clean_name = clean_name.strip()
                    
                    # Try Artist-Title separation
                    if ' - ' in clean_name:
                        parts = clean_name.split(' - ', 1)
                        artist = parts[0].strip()
                        title = parts[1].strip()
                        query = f"artist:{artist} track:{title}"
                    else:
                        query = clean_name
                    
                    # Spotify search
                    results = self.spotify.search(q=query, type='track', limit=3)
                    if results['tracks']['items']:
                        # Take first result for album detection
                        track = results['tracks']['items'][0]
                        album_name = track['album']['name']
                        artist_name = track['artists'][0]['name'] if track['artists'] else ''
                        if album_name and artist_name:
                            spotify_albums.add(album_name)
                            spotify_artists.add(artist_name)
                            print(f"Album found via Spotify: '{artist_name} - {album_name}'")
            except Exception as e:
                print(f"Error retrieving Spotify data for {mp3_path}: {e}")
                pass
        
        # Check if it's an album
        # New logic: Album detected if same album name, even with different artists (featured artists)
        is_album = len(spotify_albums) == 1 and len(mp3_files) >= 2
        album_name = list(spotify_albums)[0] if spotify_albums else ""
        
        # With different artists: Take the most common base artist
        if spotify_artists:
            # Determine base artists (without features)
            base_artists = []
            for artist in spotify_artists:
                # Take only the first part before comma or "feat."
                base_artist = re.split(r'[,&]|feat\.?|ft\.?', artist, 1)[0].strip()
                base_artists.append(base_artist)
            
            # Take the most common base artist
            from collections import Counter
            most_common_artist = Counter(base_artists).most_common(1)[0][0] if base_artists else ""
            artist_name = most_common_artist
        else:
            artist_name = ""
        
        # Debugging
        print(f"Folder: {folder_path}")
        print(f"Album detected: {is_album}, Artist: {artist_name}, Album: {album_name}")
        
        folder_item = QtWidgets.QTreeWidgetItem(parent, [os.path.basename(folder_path) or folder_path,
                                                        f'Yes ({artist_name} - {album_name})' if is_album else 'No',
                                                        'Ready' if is_album else 'Skipped'])
        folder_item.setData(0, 1, folder_path)  # Folder path
        if is_album:
            folder_item.setData(0, 2, album_name)  # Album name
            folder_item.setData(0, 3, artist_name)  # Artist name (new data field)
        
        # Show files
        for mp3_path in mp3_files:
            file_item = QtWidgets.QTreeWidgetItem(folder_item, [os.path.basename(mp3_path), '', ''])
            file_item.setData(0, 1, mp3_path)
        # Subfolders recursively
        for name in sorted(os.listdir(folder_path)):
            sub_path = os.path.join(folder_path, name)
            if os.path.isdir(sub_path):
                self._add_folder_item(folder_item, sub_path)

    def create_backup(self, folder_path):
        """Creates a complete backup of the folder"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Create backup in program folder, not in music folder
            program_dir = os.path.dirname(os.path.abspath(__file__))
            backups_dir = os.path.join(program_dir, "backups")
            
            # Create backup folder if it doesn't exist
            if not os.path.exists(backups_dir):
                os.makedirs(backups_dir)
            
            backup_folder = os.path.join(backups_dir, f"BACKUP_{os.path.basename(folder_path)}_{timestamp}")
            
            print(f"Creating backup in: {backup_folder}")
            shutil.copytree(folder_path, backup_folder)
            
            # Save backup info in JSON
            backup_info = {
                "original_folder": folder_path,
                "backup_folder": backup_folder,
                "timestamp": timestamp,
                "files": []
            }
            
            # List all MP3 files
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.mp3'):
                        rel_path = os.path.relpath(os.path.join(root, file), folder_path)
                        backup_info["files"].append(rel_path)
            
            info_file = os.path.join(backup_folder, "backup_info.json")
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            return backup_folder
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None

    def auto_process_albums(self):
        """Automatically processes all detected albums"""
        # Collect all album folders
        album_folders = []
        
        def collect_albums(item):
            for i in range(item.childCount()):
                child = item.child(i)
                folder_path = child.data(0, 1)
                album_name = child.data(0, 2)
                artist_name = child.data(0, 3)
                
                if os.path.isdir(folder_path) and album_name and artist_name:  # Is album folder
                    album_folders.append((child, folder_path, album_name, artist_name))
                
                collect_albums(child)  # Recursive
        
        # Start with root items
        for i in range(self.folder_tree.topLevelItemCount()):
            collect_albums(self.folder_tree.topLevelItem(i))
        
        if not album_folders:
            QtWidgets.QMessageBox.information(self, 'Info', 'No album folders found to process!')
            return
        
        # Show progress
        self.progress.setVisible(True)
        self.progress.setMaximum(len(album_folders))
        
        processed_count = 0
        
        for i, (item, folder_path, album_name, artist_name) in enumerate(album_folders):
            self.progress.setValue(i + 1)
            QtWidgets.QApplication.processEvents()
            
            try:
                # Update status
                item.setText(2, 'Processing...')
                QtWidgets.QApplication.processEvents()
                
                # Create backup
                backup_folder = self.create_backup(folder_path)
                if not backup_folder:
                    item.setText(2, 'Backup Error')
                    continue
                
                # Process album
                success = self.process_album_folder(folder_path, album_name, artist_name)
                
                if success:
                    # Rename folder to "Artist - Album" with album artist
                    new_folder_name = self.get_artist_album_name_from_spotify(album_name, artist_name)
                    if new_folder_name:
                        new_folder_path = os.path.join(os.path.dirname(folder_path), new_folder_name)
                        try:
                            if folder_path != new_folder_path:
                                os.rename(folder_path, new_folder_path)
                                print(f"Folder renamed: {folder_path} -> {new_folder_path}")
                        except Exception as e:
                            print(f"Error renaming folder: {e}")
                    
                    item.setText(2, 'Success')
                    processed_count += 1
                else:
                    item.setText(2, 'Error')
                    
            except Exception as e:
                print(f"Error processing {folder_path}: {e}")
                item.setText(2, 'Error')
        
        self.progress.setVisible(False)
        
        QtWidgets.QMessageBox.information(self, 'Finished', 
                                        f'{processed_count} of {len(album_folders)} albums processed successfully!\n\n'
                                        f'Backups have been created and can be restored via "Restore Backup".')
        
        # Update tree
        self.folder_tree.clear()
        self.populate_tree(self.selected_folder)

    def get_artist_album_name_from_spotify(self, album_name, artist_name):
        """Determines artist-album name directly from Spotify album (album artist, not track artist)"""
        try:
            # Find album on Spotify to get correct album artist
            album_id = self.find_album_id(album_name, artist_name)
            if album_id:
                # Use already loaded album info from cache if available
                if hasattr(self, '_album_info_cache') and album_id in self._album_info_cache:
                    album_info = self._album_info_cache[album_id]
                else:
                    album_info = self.spotify.album(album_id)
                    # Cache for later use
                    if not hasattr(self, '_album_info_cache'):
                        self._album_info_cache = {}
                    self._album_info_cache[album_id] = album_info
                    
                if album_info and album_info.get('artists'):
                    # Take first album artist (main artist of the album)
                    album_artist = album_info['artists'][0]['name']
                    album_clean = self.sanitize_filename(album_name)
                    album_artist_clean = self.sanitize_filename(album_artist)
                    folder_name = f"{album_artist_clean} - {album_clean}"
                    print(f"Album artist for folder renaming: '{album_artist}' (Album: '{album_name}')")
                    return folder_name
                    
        except Exception as e:
            print(f"Error determining album artist: {e}")
        
        # Fallback: Use already known artist
        try:
            album_clean = self.sanitize_filename(album_name)
            artist_clean = self.sanitize_filename(artist_name)
            return f"{artist_clean} - {album_clean}"
        except Exception:
            return None

    def get_artist_album_name(self, folder_path, album_name):
        """Old method - no longer used, but kept for compatibility"""
        try:
            mp3_files = self.find_mp3_files(folder_path, only_current=True)
            if mp3_files:
                # Take first MP3 and get artist
                audio = MP3(mp3_files[0], ID3=EasyID3)
                artist = audio.get('artist', [''])[0]
                if artist:
                    # Remove leading numbers from artist
                    artist_clean = re.sub(r'^\d{1,2}\s*-\s*', '', artist).strip()
                    album_clean = self.sanitize_filename(album_name)
                    return f"{artist_clean} - {album_clean}"
        except Exception as e:
            print(f"Error determining artist-album name: {e}")
        
        return None

    def restore_backup(self):
        """Restores a backup"""
        # Search in program's backup folder by default
        program_dir = os.path.dirname(os.path.abspath(__file__))
        default_backup_dir = os.path.join(program_dir, "backups")
        
        backup_folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select Backup Folder', 
            default_backup_dir if os.path.exists(default_backup_dir) else ''
        )
        
        if not backup_folder:
            return
        
        # Check if it's a valid backup folder
        info_file = os.path.join(backup_folder, "backup_info.json")
        if not os.path.exists(info_file):
            QtWidgets.QMessageBox.warning(self, 'Error', 'Invalid backup folder! backup_info.json not found.')
            return
        
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                backup_info = json.load(f)
            
            original_folder = backup_info["original_folder"]
            timestamp = backup_info["timestamp"]
            
            # Confirm restoration
            reply = QtWidgets.QMessageBox.question(
                self, 'Restore Backup',
                f'Restore backup from {timestamp}?\n\n'
                f'Target: {original_folder}\n'
                f'All current changes will be lost!',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                # Delete current folder (if exists)
                if os.path.exists(original_folder):
                    shutil.rmtree(original_folder)
                
                # Copy backup back (without backup_info.json)
                shutil.copytree(backup_folder, original_folder, ignore=shutil.ignore_patterns('backup_info.json'))
                
                QtWidgets.QMessageBox.information(self, 'Success', 'Backup restored successfully!')
                
                # Update tree
                if hasattr(self, 'selected_folder'):
                    self.folder_tree.clear()
                    self.populate_tree(self.selected_folder)
                    
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Error restoring backup: {e}')

    def process_album_folder(self, folder_path, album_name, artist_name):
        """Processes an album folder automatically"""
        try:
            mp3_files = self.find_mp3_files(folder_path, only_current=True)
            if not mp3_files:
                return False
            
            print(f"Processing album: {artist_name} - {album_name} in {folder_path}")
            
            # Find album ID
            album_id = self.find_album_id(album_name, artist_name)
            if not album_id:
                print(f"Could not find album ID for '{artist_name} - {album_name}'")
                return False
            
            # Load album tracks
            album_tracks, album_cover_url = self.load_album_data(album_id)
            if not album_tracks:
                return False
            
            # Match tracks and set track numbers
            for mp3_path in mp3_files:
                self.match_and_update_track(mp3_path, album_tracks, album_cover_url)
            
            # Sort by track numbers and final renaming
            self.finalize_album_tracks(mp3_files, folder_path)
            
            return True
            
        except Exception as e:
            print(f"Error processing album: {e}")
            return False

    def find_album_id(self, album_name, artist_name):
        """Finds album ID via direct search with artist and album"""
        search_queries = [
            f'artist:"{artist_name}" album:"{album_name}"',  # Best search with both
            f'"{artist_name}" "{album_name}"',               # Simple combination
            f'album:"{album_name}"',                         # Album only (fallback)
            album_name                                       # Album name only (last fallback)
        ]
        
        for query in search_queries:
            try:
                print(f"Searching album with query: {query}")
                results = self.spotify.search(q=query, type='album', limit=10)
                for album in results['albums']['items']:
                    # Album name must match
                    album_match = album['name'].lower() == album_name.lower()
                    
                    if album_match:
                        # Check if album artist is substring of song artist
                        for album_artist in album['artists']:
                            album_artist_name = album_artist['name'].lower()
                            song_artist_name = artist_name.lower()
                            
                            # Exact match (best priority)
                            if album_artist_name == song_artist_name:
                                print(f"Exact match found: {album_artist['name']} - {album['name']} (ID: {album['id']})")
                                return album['id']
                            
                            # Album artist is substring of song artist (e.g. "Drake" in "Drake feat. Rihanna")
                            elif album_artist_name in song_artist_name:
                                print(f"Substring match found: Album artist '{album_artist['name']}' in song artist '{artist_name}' - {album['name']} (ID: {album['id']})")
                                return album['id']
                            
                            # Song artist is substring of album artist (rare case)
                            elif song_artist_name in album_artist_name:
                                print(f"Reverse substring match found: Song artist '{artist_name}' in album artist '{album_artist['name']}' - {album['name']} (ID: {album['id']})")
                                return album['id']
                
            except Exception as e:
                print(f"Error with query '{query}': {e}")
                continue
        
        print(f"No matching album found for '{artist_name} - {album_name}'")
        return None

    def load_album_data(self, album_id):
        """Loads album tracks and cover URL with only one API call"""
        try:
            # Only ONE album call for all data (incl. tracks and cover)
            album_info = self.spotify.album(album_id, market='DE')
            album_tracks = {}
            album_cover_url = None
            
            if not album_info:
                return None, None
            
            # Album cover URL
            if album_info.get('images'):
                album_cover_url = album_info['images'][0]['url']
            
            # Collect tracks from album object (instead of separate album_tracks() call)
            self._current_album_tracks_full = album_info['tracks']['items']  # For later use
            for track in album_info['tracks']['items']:
                track_name = track['name'].lower()
                track_number = track['track_number']
                album_tracks[track_name] = track_number
                print(f"Album Track: #{track_number} - {track['name']}")
            
            return album_tracks, album_cover_url
            
        except Exception as e:
            print(f"Error loading album data: {e}")
            return None, None

    def match_and_update_track(self, mp3_path, album_tracks, album_cover_url):
        """Matches a track with album data and updates all metadata"""
        try:
            filename = os.path.splitext(os.path.basename(mp3_path))[0]
            
            # Determine track name (as before)
            real_track_name = self.get_real_track_name(mp3_path, filename)
            
            # Find best match
            track_number = 999
            best_match = None
            best_ratio = 0
            
            import difflib
            for album_track_name, album_track_number in album_tracks.items():
                ratio = difflib.SequenceMatcher(None, real_track_name.lower(), album_track_name).ratio()
                if ratio > best_ratio and ratio > 0.6:
                    best_ratio = ratio
                    best_match = album_track_name
                    track_number = album_track_number
            
            if best_match:
                print(f"Match: '{real_track_name}' -> Track #{track_number} ({best_ratio:.2f})")
            
            # Set all metadata in one go
            audio = MP3(mp3_path, ID3=EasyID3)
            audio['tracknumber'] = str(track_number)
            
            # Set other metadata if found
            if best_match:
                # Use track name from Spotify
                proper_track_name = None
                for orig_name, num in album_tracks.items():
                    if num == track_number:
                        # Find original name (not lowercase)
                        for track in self._current_album_tracks_full:
                            if track['track_number'] == track_number:
                                proper_track_name = track['name']
                                break
                        break
                
                if proper_track_name:
                    audio['title'] = proper_track_name
                    
            audio.save()
            
            # Add cover (only once)
            if album_cover_url:
                try:
                    self.add_album_cover(mp3_path, album_cover_url)
                    print(f"Cover added: {filename}")
                except Exception as e:
                    print(f"Cover error: {e}")
                    
        except Exception as e:
            print(f"Error matching {mp3_path}: {e}")

    def get_real_track_name(self, mp3_path, filename):
        """Determines the real track name (as in the original function)"""
        real_track_name = None
        
        try:
            audio = MP3(mp3_path, ID3=EasyID3)
            existing_title = audio.get('title', [''])[0]
            if existing_title:
                real_track_name = re.sub(r'^\d{1,2}\s*-\s*', '', existing_title).strip()
                return real_track_name
        except Exception:
            pass
        
        # Fallback: Spotify search or filename
        try:
            clean_name = re.sub(r'\s*\([^)]*\)|\s*\[[^]]*\]', '', filename)
            clean_name = clean_name.strip()
            clean_name = re.sub(r'^\d{1,2}\s*-\s*', '', clean_name).strip()
            
            if ' - ' in clean_name:
                parts = clean_name.split(' - ', 1)
                artist = parts[0].strip()
                title = parts[1].strip()
                query = f"artist:{artist} track:{title}"
            else:
                query = clean_name
            
            results = self.spotify.search(q=query, type='track', limit=5)
            if results['tracks']['items']:
                return results['tracks']['items'][0]['name']
            else:
                return clean_name.split(' - ', 1)[1].strip() if ' - ' in clean_name else clean_name
                
        except Exception:
            return filename

    def finalize_album_tracks(self, mp3_files, folder_path):
        """Sorts tracks by track number and final renaming"""
        def get_tracknum(mp3):
            try:
                audio = MP3(mp3, ID3=EasyID3)
                tn = audio.get('tracknumber', ['999'])[0]
                return int(tn.split('/')[0])
            except:
                return 999
        
        mp3_files.sort(key=get_tracknum)
        
        for i, mp3_path in enumerate(mp3_files, 1):
            try:
                # Update metadata
                self.update_metadata(mp3_path, track_num=i)
                
                # Final renaming
                audio = MP3(mp3_path, ID3=EasyID3)
                title = audio.get('title', [''])[0]
                artist = audio.get('artist', [''])[0]
                
                title_clean = re.sub(r'^\d{1,2}\s*-\s*', '', title).strip()
                artist_clean = re.sub(r'^\d{1,2}\s*-\s*', '', artist).strip()
                
                new_title = f"{i:02d} - {title_clean}"
                audio['title'] = new_title
                audio.save()
                
                new_name = f"{i:02d} - {artist_clean} - {title_clean}.mp3"
                new_name = self.sanitize_filename(new_name)
                new_path = os.path.join(folder_path, new_name)
                
                if mp3_path != new_path:
                    os.rename(mp3_path, new_path)
                    
            except Exception as e:
                print(f"Error finalizing {mp3_path}: {e}")

    def find_mp3_files(self, folder, only_current=False):
        mp3_files = []
        if only_current:
            for file in os.listdir(folder):
                if file.lower().endswith('.mp3'):
                    mp3_files.append(os.path.join(folder, file))
        else:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.mp3'):
                        mp3_files.append(os.path.join(root, file))
        return mp3_files

    def sanitize_filename(self, name):
        return re.sub(r'[\\/:*?"<>|]', '', name)

    def add_album_cover(self, mp3_path, cover_url):
        """Downloads album cover from URL and adds it to MP3"""
        try:
            # Download image from URL
            response = requests.get(cover_url, timeout=10)
            response.raise_for_status()
            image_data = response.content
            
            # Determine MIME type based on first bytes
            if image_data.startswith(b'\xff\xd8\xff'):
                mime_type = 'image/jpeg'
            elif image_data.startswith(b'\x89PNG'):
                mime_type = 'image/png'
            else:
                mime_type = 'image/jpeg'  # Fallback
            
            # Add cover to MP3
            audio_file = MP3(mp3_path)
            
            # Ensure ID3 tags exist
            if audio_file.tags is None:
                audio_file.add_tags()
            
            # Remove existing covers
            audio_file.tags.delall('APIC')
            
            # Add new cover
            audio_file.tags.add(
                APIC(
                    encoding=3,  # UTF-8
                    mime=mime_type,
                    type=3,  # Cover (front)
                    desc='Cover',
                    data=image_data
                )
            )
            
            # Save with v2.3 for better compatibility
            audio_file.save(v2_version=3)
            
        except Exception as e:
            print(f"Error adding album cover: {e}")
            raise

    def update_metadata(self, mp3_path, track_num=None):
        """Simplified metadata update - uses already loaded album data"""
        try:
            # Since we already have album_tracks, we don't need additional API calls
            audio = MP3(mp3_path, ID3=EasyID3)
            
            # Use already set track number if available
            if track_num:
                current_tracknum = audio.get('tracknumber', [str(track_num)])[0]
                # Track number is already set in match_and_update_track
                pass
            
            # Album cover is already added in match_and_update_track
            # No additional API calls needed
            
        except Exception as e:
            print(f"Error updating metadata for {os.path.basename(mp3_path)}: {e}")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Mp3MetadataApp()
    window.show()
    sys.exit(app.exec_())
