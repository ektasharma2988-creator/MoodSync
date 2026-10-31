import os
import requests
from dotenv import load_dotenv

load_dotenv()

JAMENDO_CLIENT_ID = os.getenv("JAMENDO_CLIENT_ID")
BASE_URL = "https://api.jamendo.com/v3.0"


def get_tracks(limit=10, offset=0):
    """Get playable tracks directly from Jamendo."""

    url = f"{BASE_URL}/tracks/"

    params = {
        "client_id": JAMENDO_CLIENT_ID,
        "format": "json",
        "limit": limit,
        "offset": offset,
        "audioformat": "mp31"
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()

    return data.get("results", [])


def format_track(track, mood=""):
    """Convert Jamendo track into MoodSync song format."""

    return {
        "id": f"jamendo_{track.get('id')}",
        "title": track.get("name", "Unknown Title"),
        "artist": track.get("artist_name", "Unknown Artist"),
        "genre": "",
        "year": track.get("releasedate", "")[:4],
        "moods": [mood] if mood else [],
        "source": "Jamendo",
        "audio": track.get("audio"),
        "artwork": track.get("album_image"),
        "link": track.get("shareurl")
    }


def get_mood_recommendations(mood, limit=5):
    """
    Get playable Jamendo songs.

    Jamendo's search endpoint may return zero results
    for mood words such as 'happy' or 'sad', so we
    retrieve tracks directly instead.
    """

    tracks = get_tracks(limit=limit)

    return [
        format_track(track, mood)
        for track in tracks
        if track.get("audio")
    ]