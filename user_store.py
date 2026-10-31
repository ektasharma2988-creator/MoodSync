from datetime import datetime

from storage import load_json, save_json


class UserStore:
    """Per-user favorites, playlists and listening history (data/users.json)."""

    def __init__(self, filename):
        self.filename = filename
        self.data = load_json(filename, {})
        if not isinstance(self.data, dict):
            self.data = {}

    def _save(self):
        save_json(self.filename, self.data)

    def _user(self, name):
        name = (name or "").strip()
        if not name:
            raise ValueError("Please sign in with a name first.")
        if name not in self.data:
            self.data[name] = {"favorites": [], "playlists": {}, "history": []}
        return self.data[name]

    def names(self):
        return sorted(self.data)

    def get(self, name):
        return self._user(name)

    # favorites -------------------------------------------------------
    def toggle_favorite(self, name, song_id):
        user = self._user(name)
        if song_id in user["favorites"]:
            user["favorites"].remove(song_id)
            result = False
        else:
            user["favorites"].append(song_id)
            result = True
        self._save()
        return result

    # playlists -------------------------------------------------------
    def create_playlist(self, name, playlist):
        playlist = (playlist or "").strip()
        if not playlist:
            raise ValueError("Give the playlist a name.")
        user = self._user(name)
        if playlist in user["playlists"]:
            raise ValueError("You already have a playlist with that name.")
        user["playlists"][playlist] = []
        self._save()

    def add_to_playlist(self, name, playlist, song_id):
        user = self._user(name)
        if playlist not in user["playlists"]:
            raise ValueError("Playlist not found.")
        ids = user["playlists"][playlist]
        if song_id in ids:
            return False
        ids.append(song_id)
        self._save()
        return True

    def remove_from_playlist(self, name, playlist, song_id):
        user = self._user(name)
        if playlist == "__favorites__":
            if song_id in user["favorites"]:
                user["favorites"].remove(song_id)
        elif playlist in user["playlists"] and song_id in user["playlists"][playlist]:
            user["playlists"][playlist].remove(song_id)
        else:
            raise ValueError("Playlist not found.")
        self._save()

    def delete_playlist(self, name, playlist):
        user = self._user(name)
        if user["playlists"].pop(playlist, None) is None:
            raise ValueError("Playlist not found.")
        self._save()

    # history ---------------------------------------------------------
    def log_play(self, name, song, mood):
        user = self._user(name)
        user["history"].append({
            "song_id": song["id"], "title": song["title"], "artist": song["artist"],
            "mood": mood or song["moods"][0],
            "played_at": datetime.now().isoformat(timespec="seconds"),
        })
        user["history"] = user["history"][-500:]
        self._save()

    def clear_history(self, name):
        self._user(name)["history"] = []
        self._save()

    def recent_song_ids(self, name, n=5):
        return [h["song_id"] for h in self._user(name)["history"][-n:]]

    # housekeeping ----------------------------------------------------
    def purge_song(self, song_id):
        for user in self.data.values():
            if song_id in user["favorites"]:
                user["favorites"].remove(song_id)
            for ids in user["playlists"].values():
                if song_id in ids:
                    ids.remove(song_id)
        self._save()
