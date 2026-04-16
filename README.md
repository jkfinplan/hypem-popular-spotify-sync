# Hype Machine → Spotify Playlist Sync

Polls the Hype Machine popular chart every 6 hours and keeps a Spotify playlist in sync. Runs in a Docker container on your Mac Mini so Alexa can play it via the Spotify skill.

---

## First-time setup

### 1. Clone the repo

```bash
git clone https://github.com/jkfinplan/hypem-popular-spotify-sync.git
cd hypem-popular-spotify-sync
```

### 2. Create a Spotify Developer app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and create a new app.
2. Copy your **Client ID** and **Client Secret**.
3. Under *Redirect URIs*, add `http://localhost:8888/callback` and save.

### 3. Create the playlist

In Spotify, create a playlist called **"Hype Machine Popular"**. Open it in the desktop app or web player, copy the playlist ID from the URL:

```
https://open.spotify.com/playlist/37i9dQZF1DX...
                                    ^^^^^^^^^^^^^^ this part
```

### 4. Configure `.env`

```bash
cp .env.example .env
```

Fill in all five values:

```
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
SPOTIFY_PLAYLIST_ID=...
SPOTIFY_USERNAME=...
```

### 5. Bootstrap OAuth (one-time, run locally — not in Docker)

```bash
pip install spotipy python-dotenv
python bootstrap_auth.py
```

A browser window opens → log in → authorize the app → you'll be redirected to `localhost:8888` (which will 404 — that's fine). Copy the full redirect URL and paste it back in the terminal. The token cache is written to `./data/.cache`.

### 6. Start the container

```bash
docker compose up -d
docker compose logs -f
```

The first sync runs immediately on startup, then every 6 hours.

---

## Ongoing operations

| Task | Command |
|------|---------|
| View logs | `docker compose logs -f` |
| Restart after code change | `docker compose restart` |
| Stop | `docker compose down` |
| Re-bootstrap token | `python bootstrap_auth.py` |

---

## How it works

1. `sync.py` fetches the top 50 tracks from `https://api.hypem.com/v2/popular?mode=now&count=50`.
2. Tracks that include a `spotify_track` ID (~30–40 of 50) are converted to `spotify:track:{id}` URIs.
3. `playlist_replace_items` swaps the full playlist contents in one API call.
4. If the Hype Machine fetch fails for any reason, the playlist is left untouched.
5. The spotipy token cache at `./data/.cache` (mounted as a Docker volume) handles automatic token refresh.

---

## Alexa

> "Alexa, play my Hype Machine Popular playlist on Spotify"
