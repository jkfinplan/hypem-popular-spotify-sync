FROM python:3.12-slim

# Playlist replace needs spotipy>=2.26 (uses /items). Version is pinned in requirements.txt.
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sync.py .

CMD ["python", "sync.py"]
