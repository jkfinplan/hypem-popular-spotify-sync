"""
One-time OAuth bootstrap — run this locally on your Mac (not in Docker).
Uses a fully manual copy/paste flow (no local callback server).

Usage:
    python bootstrap_auth.py
"""

import os
import pathlib
import webbrowser
from dotenv import load_dotenv, set_key
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

ENV_FILE = pathlib.Path(".env")
cache_path = os.environ.get("SPOTIPY_CACHE_PATH", "./data/.cache")
pathlib.Path(cache_path).parent.mkdir(parents=True, exist_ok=True)

auth_manager = SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
    scope="playlist-read-private playlist-modify-public playlist-modify-private",
    username=os.environ["SPOTIFY_USERNAME"],
    cache_path=cache_path,
    open_browser=False,
)

# Step 1: print the auth URL and open it manually
auth_url = auth_manager.get_authorize_url()
print("\nOpening Spotify login in your browser...")
print(f"\n{auth_url}\n")
webbrowser.open(auth_url)

# Step 2: user pastes back the redirect URL
print("After you approve, your browser will redirect to a URL starting with:")
print(f"  {os.environ['SPOTIFY_REDIRECT_URI']}?code=...\n")
response_url = input("Paste that full URL here and press Enter: ").strip()

# Step 3: extract code and get token
code = auth_manager.parse_response_code(response_url)
token_info = auth_manager.get_access_token(code)

if not token_info:
    print("ERROR: Failed to get access token. Please try again.")
    exit(1)

sp = spotipy.Spotify(auth_manager=auth_manager)
user = sp.current_user()
user_id = user["id"]
print(f"\nAuthenticated as: {user['display_name']} ({user_id})")
print(f"Token cache written to: {cache_path}")

# Step 4: find or create the playlist
PLAYLIST_NAME = "Hype Machine Popular"
existing_id = os.environ.get("SPOTIFY_PLAYLIST_ID", "")

if existing_id and existing_id != "your_playlist_id_here":
    print(f"\nPlaylist ID already set in .env: {existing_id}")
    playlist_id = existing_id
else:
    playlist_id = None
    offset = 0
    while True:
        results = sp.current_user_playlists(limit=50, offset=offset)
        for pl in results["items"]:
            if pl["name"] == PLAYLIST_NAME:
                playlist_id = pl["id"]
                break
        if playlist_id or not results["next"]:
            break
        offset += 50

    if playlist_id:
        print(f"\nFound existing playlist '{PLAYLIST_NAME}': {playlist_id}")
    else:
        pl = sp._post(
            "me/playlists",
            payload={
                "name": PLAYLIST_NAME,
                "public": True,
                "description": "Hype Machine popular chart — synced every 6 hours",
            },
        )
        playlist_id = pl["id"]
        print(f"\nCreated playlist '{PLAYLIST_NAME}': {playlist_id}")

    set_key(str(ENV_FILE), "SPOTIFY_PLAYLIST_ID", playlist_id)
    print(f"Playlist ID saved to .env")

print("\nAll done! You can now start the Docker container.")
