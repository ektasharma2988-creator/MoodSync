import random

from jamendo_api import get_mood_recommendations


class MusicRecommender:
    """Recommends playable songs from Jamendo."""

    def __init__(self, manager):
        self.manager = manager

    def recommend(self, mood, limit=5, genre="", favorites=(), recent=()):
        try:
            songs = get_mood_recommendations(
                mood=mood,
                limit=limit
            )

            playable = [
                song for song in songs
                if song.get("audio")
            ]

            random.shuffle(playable)

            return playable[:limit]

        except Exception as e:
            print("Jamendo recommendation error:", repr(e))
            return []