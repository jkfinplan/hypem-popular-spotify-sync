import os
import time
import logging
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

HYPEM_URL = "https://api.hypem.com/v2/popular"
HYPEM_PARAMS = {"mode": "now", "count": 50}
HYPEM_HEADERS = {
    # HM blocks requests without a browser User-Agent
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

SYNC_INTERVAL_SECONDS = 6 * 60 * 60  # 6 hours


def build_spotify_client() -> spotipy.Spotify:
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIFY_CLIENT_ID"],
        client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
        scope="playlist-read-private playlist-modify-public playlist-modify-private",
        username=os.environ["SPOTIFY_USERNAME"],
        cache_path=os.environ.get("SPOTIPY_CACHE_PATH", "./data/.cache"),
        open_browser=False,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def fetch_hypem_popular() -> list[dict]:
    response = requests.get(HYPEM_URL, params=HYPEM_PARAMS, headers=HYPEM_HEADERS, timeout=15)
    response.raise_for_status()
    tracks = response.json()
    if not isinstance(tracks, list):
        raise ValueError(f"Unexpected HM response: {tracks}")
    return tracks


def search_spotify_track(sp: spotipy.Spotify, artist: str, title: str) -> str | None:
    """Return the Spotify URI for the best match, or None if not found."""
    query = f"artist:{artist} track:{title}"
    try:
        results = sp.search(q=query, type="track", limit=1)
        items = results["tracks"]["items"]
        if items:
            return items[0]["uri"]
    except Exception as exc:
        log.warning("Spotify search failed for '%s - %s': %s", artist, title, exc)
    return None


def resolve_spotify_uris(sp: spotipy.Spotify, tracks: list[dict]) -> list[str]:
    """Search Spotify for each HM track and return matched URIs in chart order."""
    uris = []
    not_found = []
    for track in tracks:
        artist = track.get("artist", "")
        title = track.get("title", "")
        uri = search_spotify_track(sp, artist, title)
        if uri:
            uris.append(uri)
        else:
            not_found.append(f"{artist} - {title}")

    if not_found:
        log.info("No Spotify match for %d track(s):", len(not_found))
        for t in not_found:
            log.info("  - %s", t)

    return uris


def sync_playlist(sp: spotipy.Spotify, playlist_id: str, track_uris: list[str]) -> None:
    # Spotify's replace endpoint accepts max 100 tracks; we have ≤50 so one call is fine
    sp.playlist_replace_items(playlist_id, track_uris)


def run_sync() -> None:
    playlist_id = os.environ["SPOTIFY_PLAYLIST_ID"]
    log.info("=== Sync run started ===")

    try:
        tracks = fetch_hypem_popular()
        log.info("Fetched %d tracks from Hype Machine", len(tracks))
    except Exception as exc:
        log.error("Failed to fetch Hype Machine chart — skipping sync to preserve playlist: %s", exc)
        return

    try:
        sp = build_spotify_client()
        track_uris = resolve_spotify_uris(sp, tracks)
        log.info("Resolved %d / %d tracks to Spotify URIs", len(track_uris), len(tracks))
    except Exception as exc:
        log.error("Spotify lookup failed: %s", exc)
        return

    if not track_uris:
        log.warning("No Spotify matches found — skipping sync to preserve playlist")
        return

    try:
        sync_playlist(sp, playlist_id, track_uris)
        log.info("Playlist updated successfully with %d tracks", len(track_uris))
    except Exception as exc:
        log.error("Spotify playlist update failed: %s", exc)
        return

    log.info("=== Sync complete at %s ===", datetime.now(timezone.utc).isoformat())


def main() -> None:
    log.info(
        "Hype Machine → Spotify sync service starting (interval: %dh)",
        SYNC_INTERVAL_SECONDS // 3600,
    )
    while True:
        run_sync()
        log.info("Sleeping %d seconds until next sync…", SYNC_INTERVAL_SECONDS)
        time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
