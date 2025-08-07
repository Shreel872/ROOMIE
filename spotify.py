import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import os
import subprocess
import threading
import time
from flask import Flask, request

class SpotifyController:
    def __init__(self):
        # Spotify API credentials
        self.client_id = "6b66d4d3a99b46a998c93236c4b22af3"
        self.client_secret = "2c82cc1940844933a38cea2d3b2d1f54"
        
        # IMPORTANT: Replace this with your CURRENT ngrok URL
        self.redirect_uri = "https://341f-2401-d002-ca03-4500-213d-ab28-b44a-2af8.ngrok-free.app/callback"
        
        # Scopes needed for controlling Spotify
        self.scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
        
        # Initialize variables
        self.sp = None
        self.is_authenticated = False
        self.auth_code = None
        self.flask_app = None
        self.server_thread = None
        
    def start_callback_server(self):
        """Start Flask server to handle Spotify callback"""
        self.flask_app = Flask(__name__)
        
        @self.flask_app.route("/")
        def home():
            return "🎵 Spotify Callback Server is running!"
        
        @self.flask_app.route("/callback")
        def callback():
            code = request.args.get("code")
            error = request.args.get("error")
            
            print(f"Callback received - Code: {code is not None}, Error: {error}")
            
            if error:
                return f"❌ Authorization failed: {error}"
            
            if code:
                self.auth_code = code
                print(f"\n✅ Authorization code received!")
                return """
                <html>
                <body style="font-family: Arial; text-align: center; margin-top: 100px;">
                    <h2>✅ Spotify Authorization Successful!</h2>
                    <p>You can close this window and return to your terminal.</p>
                    <p>ROOMIE is now connected to your Spotify account!</p>
                </body>
                </html>
                """
            else:
                return "❌ No authorization code received"
        
        # Start server in background thread
        def run_server():
            self.flask_app.run(host='0.0.0.0', port=8888, debug=False, use_reloader=False)
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        print("🌐 Started callback server on http://localhost:8888")
        time.sleep(2)  # Give server time to start
    
    def authenticate(self):
        """Authenticate with Spotify"""
        try:
            print("🎵 Starting Spotify authentication...")
            
            # Clean start - remove old cache
            if os.path.exists(".spotify_cache"):
                os.remove(".spotify_cache")
                print("🗑️ Cleared old cache")
            
            # Start callback server first
            print("🌐 Starting callback server...")
            self.start_callback_server()
            
            # Create auth manager
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                cache_path=".spotify_cache",
                open_browser=False
            )
            
            # Get authorization URL
            auth_url = auth_manager.get_authorize_url()
            
            print("\n" + "="*60)
            print("🔗 SPOTIFY AUTHORIZATION REQUIRED")
            print("="*60)
            print(f"🔗 Authorization URL: {auth_url}")
            
            # Try to open browser automatically
            try:
                print("🌐 Attempting to open browser...")
                result = subprocess.run([
                    'powershell.exe', '-Command', f'Start-Process "{auth_url}"'
                ], capture_output=True, timeout=5)
                
                if result.returncode == 0:
                    print("✅ Browser should open automatically")
                else:
                    print("⚠️ Auto-open failed - please copy URL above")
            except:
                print("⚠️ Please copy URL above and open manually")
            
            print("\n📋 Instructions:")
            print("1. Browser should open to Spotify login")
            print("2. Log in and click 'Agree' to authorize")
            print("3. Wait for success page")
            print("4. Return here - will complete automatically")
            
            # Wait for callback with progress dots
            print("\n⏳ Waiting for authorization", end="")
            timeout = 120  # 2 minutes
            start_time = time.time()
            
            while self.auth_code is None and (time.time() - start_time) < timeout:
                time.sleep(1)
                print(".", end="", flush=True)
            
            if self.auth_code is None:
                print(f"\n❌ Timeout after {timeout} seconds")
                return False
            
            print(f"\n✅ Got authorization code!")
            
            # Exchange code for token
            token_info = auth_manager.get_access_token(self.auth_code, as_dict=False)
            
            # Create Spotify client
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            
            # Test connection
            user = self.sp.current_user()
            print(f"✅ Authentication successful!")
            print(f"👋 Connected as: {user['display_name']}")
            self.is_authenticated = True
            
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def get_current_track(self):
        """Get currently playing track"""
        if not self.is_authenticated:
            return "Not authenticated"
        
        try:
            current = self.sp.current_playback()
            if current and current['is_playing']:
                track = current['item']
                return f"Playing: {track['name']} by {track['artists'][0]['name']}"
            else:
                return "No music playing"
        except Exception as e:
            return f"Error: {e}"

    def search_and_play(self, query, search_type="track"):
        """Search for music and play it"""
        if not self.is_authenticated:
            return "Not authenticated with Spotify"
        
        try:
            print(f"🔍 Searching for {search_type}: {query}")
            results = self.sp.search(q=query, type=search_type, limit=1)
            
            if search_type == "track" and results['tracks']['items']:
                track = results['tracks']['items'][0]
                track_uri = track['uri']
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                
                # Play the track
                self.sp.start_playback(uris=[track_uri])
                msg = f"Now playing: {track_name} by {artist_name}"
                print(f"🎵 {msg}")
                return msg
                
            elif search_type == "playlist" and results['playlists']['items']:
                playlist = results['playlists']['items'][0]
                playlist_uri = playlist['uri']
                playlist_name = playlist['name']
                
                # Play the playlist
                self.sp.start_playback(context_uri=playlist_uri)
                msg = f"Now playing playlist: {playlist_name}"
                print(f"🎵 {msg}")
                return msg
                
            elif search_type == "artist" and results['artists']['items']:
                artist = results['artists']['items'][0]
                artist_uri = artist['uri']
                artist_name = artist['name']
                
                # Play artist's top tracks
                self.sp.start_playback(context_uri=artist_uri)
                msg = f"Now playing music by: {artist_name}"
                print(f"🎵 {msg}")
                return msg
                
            else:
                msg = f"No {search_type} found for '{query}'"
                print(f"❌ {msg}")
                return msg
                
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 404:
                return "No active Spotify device found. Please open Spotify app and start playing something first."
            else:
                print(f"❌ Spotify error: {e}")
                return f"Spotify error: {e}"
        except Exception as e:
            print(f"❌ Error: {e}")
            return f"Error playing music: {e}"

    def pause_music(self):
        """Pause current playback"""
        if not self.is_authenticated:
            return "Not authenticated with Spotify"
        
        try:
            self.sp.pause_playback()
            print("⏸️ Music paused")
            return "Music paused"
        except Exception as e:
            print(f"❌ Error pausing music: {e}")
            return "Could not pause music. Make sure Spotify is active."

    def resume_music(self):
        """Resume current playback"""
        if not self.is_authenticated:
            return "Not authenticated with Spotify"
        
        try:
            self.sp.start_playback()
            print("▶️ Music resumed")
            return "Music resumed"
        except Exception as e:
            print(f"❌ Error resuming music: {e}")
            return "Could not resume music. Make sure Spotify is active."

    def next_track(self):
        """Skip to next track"""
        if not self.is_authenticated:
            return "Not authenticated with Spotify"
        
        try:
            self.sp.next_track()
            print("⏭️ Skipped to next track")
            return "Skipped to next track"
        except Exception as e:
            print(f"❌ Error skipping track: {e}")
            return "Could not skip track"

    def previous_track(self):
        """Go to previous track"""
        if not self.is_authenticated:
            return "Not authenticated with Spotify"
        
        try:
            self.sp.previous_track()
            print("⏮️ Gone to previous track")
            return "Gone to previous track"
        except Exception as e:
            print(f"❌ Error going to previous track: {e}")
            return "Could not go to previous track"

    def set_volume(self, volume):
        """Set volume (0-100)"""
        if not self.is_authenticated:
            return "Not authenticated with Spotify"
        
        try:
            volume = max(0, min(100, int(volume)))  # Ensure volume is between 0-100
            self.sp.volume(volume)
            print(f"🔊 Volume set to {volume}%")
            return f"Volume set to {volume}%"
        except Exception as e:
            print(f"❌ Error setting volume: {e}")
            return "Could not change volume"

    def shuffle_toggle(self, state=True):
        """Toggle shuffle on/off"""
        if not self.is_authenticated:
            return "Not authenticated with Spotify"
        
        try:
            self.sp.shuffle(state)
            status = "on" if state else "off"
            print(f"🔀 Shuffle turned {status}")
            return f"Shuffle turned {status}"
        except Exception as e:
            print(f"❌ Error toggling shuffle: {e}")
            return "Could not toggle shuffle"

    def process_spotify_command(command):
        """Process voice commands for Spotify"""
        spotify = SpotifyController()
        
        command = command.lower()
        
        if "play" in command:
            if "play " in command:
                query = command.split("play ", 1)[1]
                
                if "playlist" in query:
                    query = query.replace("playlist", "").strip()
                    return spotify.search_and_play(query, "playlist")
                elif "artist" in query or "by" in query:
                    query = query.replace("artist", "").replace("by", "").strip()
                    return spotify.search_and_play(query, "artist")
                else:
                    return spotify.search_and_play(query, "track")
            else:
                return spotify.resume_music()
        
        elif "pause" in command or "stop" in command:
            return spotify.pause_music()
        
        elif "next" in command or "skip" in command:
            return spotify.next_track()
        
        elif "previous" in command or "back" in command:
            return spotify.previous_track()
        
        elif "volume" in command:
            # Extract volume level
            words = command.split()
            for i, word in enumerate(words):
                if word == "volume" and i + 1 < len(words):
                    try:
                        volume = int(words[i + 1])
                        return spotify.set_volume(volume)
                    except ValueError:
                        pass
            return "Please specify a volume level between 0 and 100"
        
        elif "what's playing" in command or "current song" in command:
            return spotify.get_current_track()
        
        elif "shuffle on" in command:
            return spotify.shuffle_toggle(True)
        
        elif "shuffle off" in command:
            return spotify.shuffle_toggle(False)
        
        else:
            return "I didn't understand that Spotify command. Try saying 'play [song name]', 'pause', 'next', or 'volume [number]'"
        
def test_spotify():
    """Test Spotify functionality with music playback"""
    print("🎵 SPOTIFY AUTHENTICATION TEST")
    print("="*40)
    
    spotify = SpotifyController()
    
    if spotify.authenticate():
        print("\n🎉 SUCCESS! Testing API...")
        
        # Test current track
        print("\n1. Current track:")
        print(spotify.get_current_track())
        
        # Wait for user input before playing music
        print("\n" + "="*50)
        print("🎵 MUSIC PLAYBACK TESTS")
        print("="*50)
        
        while True:
            print("\nChoose a test:")
            print("1. Play a song")
            print("2. Play an artist")
            print("3. Play a playlist")
            print("4. Pause music")
            print("5. Resume music")
            print("6. Next track")
            print("7. Previous track")
            print("8. Set volume")
            print("9. Current track info")
            print("0. Exit")
            
            choice = input("\nEnter choice (0-9): ").strip()
            
            if choice == "1":
                song = input("Enter song name: ")
                print(spotify.search_and_play(song, "track"))
                
            elif choice == "2":
                artist = input("Enter artist name: ")
                print(spotify.search_and_play(artist, "artist"))
                
            elif choice == "3":
                playlist = input("Enter playlist name: ")
                print(spotify.search_and_play(playlist, "playlist"))
                
            elif choice == "4":
                print(spotify.pause_music())
                
            elif choice == "5":
                print(spotify.resume_music())
                
            elif choice == "6":
                print(spotify.next_track())
                
            elif choice == "7":
                print(spotify.previous_track())
                
            elif choice == "8":
                volume = input("Enter volume (0-100): ")
                try:
                    print(spotify.set_volume(int(volume)))
                except ValueError:
                    print("Invalid volume. Please enter a number 0-100.")
                    
            elif choice == "9":
                print(spotify.get_current_track())
                
            elif choice == "0":
                print("👋 Goodbye!")
                break
                
            else:
                print("Invalid choice. Please try again.")
    else:
        print("\n❌ FAILED!")

if __name__ == "__main__":
    test_spotify()