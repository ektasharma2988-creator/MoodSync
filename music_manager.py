from storage import load_json, save_json

DEFAULT_MOODS = ["Happy", "Sad", "Calm", "Angry", "Romantic", "Energetic"]


class ValidationError(ValueError):
    """Raised when song data is invalid."""


def parse_moods(value):
    """Accept a list or a comma-separated string; return unique Title-case moods."""
    if isinstance(value, str):
        value = value.split(",")
    moods = []
    for m in value or []:
        m = str(m).strip().title()
        if m and m not in moods:
            moods.append(m)
    return moods


def _clean(title, artist, genre, year, moods):
    title = str(title or "").strip()
    artist = str(artist or "").strip()
    genre = str(genre or "").strip().title() or "Other"
    moods = parse_moods(moods)
    if not title or not artist:
        raise ValidationError("Title and artist are required.")
    if not moods:
        raise ValidationError("Add at least one mood.")
    try:
        year = int(year)
    except (TypeError, ValueError):
        raise ValidationError("Year must be a number.")
    if not 1000 <= year <= 2100:
        raise ValidationError("Year must be between 1000 and 2100.")
    return title, artist, genre, year, moods


class MusicManager:
    def __init__(self, filename):
        self.filename = filename
        self.songs = [self._migrate(s) for s in load_json(filename, [])]

    @staticmethod
    def _migrate(song):
        """Upgrade old records (single 'mood', no 'year') to the current shape."""
        if "moods" not in song:
            song["moods"] = parse_moods(song.pop("mood", "")) or ["Calm"]
        song.pop("mood", None)
        song.setdefault("year", 2000)
        song.setdefault("genre", "Other")
        return song

    def _save(self):
        save_json(self.filename, self.songs)

    def _next_id(self):
        return max((song["id"] for song in self.songs), default=0) + 1

    def get(self, song_id):
        return next((s for s in self.songs if s["id"] == song_id), None)

    def add_song(self, title, artist, genre, year, moods):
        title, artist, genre, year, moods = _clean(title, artist, genre, year, moods)
        song = {"id": self._next_id(), "title": title, "artist": artist,
                "genre": genre, "year": year, "moods": moods}
        self.songs.append(song)
        self._save()
        return song

    def update_song(self, song_id, title, artist, genre, year, moods):
        song = self.get(song_id)
        if not song:
            return None
        title, artist, genre, year, moods = _clean(title, artist, genre, year, moods)
        song.update(title=title, artist=artist, genre=genre, year=year, moods=moods)
        self._save()
        return song

    def delete_song(self, song_id):
        before = len(self.songs)
        self.songs = [s for s in self.songs if s["id"] != song_id]
        if len(self.songs) != before:
            self._save()
            return True
        return False

    def search(self, q="", mood="", genre=""):
        q, mood, genre = q.lower().strip(), mood.lower().strip(), genre.lower().strip()
        results = []
        for s in self.songs:
            if mood and mood not in [m.lower() for m in s["moods"]]:
                continue
            if genre and genre != s["genre"].lower():
                continue
            haystack = " ".join([s["title"], s["artist"], s["genre"], *s["moods"]]).lower()
            if q and q not in haystack:
                continue
            results.append(s)
        return results

    def all_moods(self):
        extra = sorted({m for s in self.songs for m in s["moods"]} - set(DEFAULT_MOODS))
        return DEFAULT_MOODS + extra

    def all_genres(self):
        return sorted({s["genre"] for s in self.songs})
