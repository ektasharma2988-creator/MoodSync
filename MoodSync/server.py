"""MoodSync web server.

Run:
    python server.py

Then open:
    http://localhost:8000
"""

import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from music_manager import MusicManager, ValidationError
from recommender import MusicRecommender
from user_store import UserStore


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")

manager = MusicManager(os.path.join(DATA_DIR, "songs.json"))
users = UserStore(os.path.join(DATA_DIR, "users.json"))
recommender = MusicRecommender(manager)

# One request touches the JSON files at a time.
lock = threading.RLock()


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ----------------------------------------------------------------------
# SONG HELPERS
# ----------------------------------------------------------------------

def songs_for(ids):
    """
    Resolve local song IDs.

    Jamendo songs are not stored in songs.json, so they are skipped here.
    They are handled separately when returned by recommendations.
    """
    result = []

    for song_id in ids:
        try:
            song = manager.get(song_id)
        except (TypeError, ValueError):
            song = None

        if song:
            result.append(song)

    return result


def get_song_by_id(song_id):
    """
    Find a song by ID.

    Supports:
        Local songs: 1, 2, 12, ...
        Jamendo songs: jamendo_168, jamendo_169, ...

    Jamendo songs are reconstructed from the recommendation API.
    """

    if song_id is None:
        return None

    song_id = str(song_id)

    # --------------------------------------------------------------
    # LOCAL SONG
    # --------------------------------------------------------------
    try:
        local_song = manager.get(int(song_id))

        if local_song:
            return local_song

    except (TypeError, ValueError):
        pass

    # --------------------------------------------------------------
    # JAMENDO SONG
    # --------------------------------------------------------------
    if song_id.startswith("jamendo_"):
        try:
            jamendo_id = int(song_id.replace("jamendo_", "", 1))
        except ValueError:
            return None

        try:
            from jamendo_api import get_tracks

            # Search through a reasonable number of tracks for the ID.
            # Jamendo's current API endpoint returns the track ID.
            offset = 0

            for _ in range(10):
                tracks = get_tracks(limit=50, offset=offset)

                if not tracks:
                    break

                for track in tracks:
                    if str(track.get("id")) == str(jamendo_id):
                        return {
                            "id": f"jamendo_{track.get('id')}",
                            "title": track.get("name", "Unknown Title"),
                            "artist": track.get(
                                "artist_name",
                                "Unknown Artist"
                            ),
                            "genre": "",
                            "year": track.get(
                                "releasedate",
                                ""
                            )[:4],
                            "moods": [],
                            "source": "Jamendo",
                            "audio": track.get("audio"),
                            "artwork": track.get("album_image"),
                            "link": track.get("shareurl"),
                        }

                offset += 50

        except Exception as e:
            print("Jamendo song lookup error:", repr(e))

    return None


def need_song(song_id):
    """
    Require a valid song.

    Supports both local and Jamendo song IDs.
    """
    song = get_song_by_id(song_id)

    if not song:
        raise ApiError("Song not found.", 404)

    return song


# ----------------------------------------------------------------------
# USER DATA
# ----------------------------------------------------------------------

def user_payload(name):
    user = users.get(name)

    history = user["history"]

    stats = {}

    for h in history:
        mood = h.get("mood", "Unknown")
        stats[mood] = stats.get(mood, 0) + 1

    return {
        "favorites": user["favorites"],
        "favorite_songs": songs_for(user["favorites"]),
        "playlists": {
            pl: songs_for(ids)
            for pl, ids in user["playlists"].items()
        },
        "total_plays": len(history),
        "stats": stats,
        "history": list(reversed(history[-50:])),
    }


# ----------------------------------------------------------------------
# HTTP HANDLER
# ----------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    server_version = "MoodSync/1.0"

    # --------------------------------------------------------------
    # LOGGING
    # --------------------------------------------------------------

    def log_message(self, fmt, *args):
        print(
            f"{self.address_string()} - "
            f"{fmt % args}"
        )

    # --------------------------------------------------------------
    # JSON RESPONSE
    # --------------------------------------------------------------

    def send_json(self, payload, status=200):

        body = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

        self.wfile.write(body)

    # --------------------------------------------------------------
    # REQUEST BODY
    # --------------------------------------------------------------

    def read_body(self):

        length = int(
            self.headers.get("Content-Length") or 0
        )

        if not length:
            return {}

        try:
            return json.loads(
                self.rfile.read(length).decode("utf-8")
            )

        except (ValueError, UnicodeDecodeError):
            raise ApiError(
                "Invalid JSON body."
            )

    # --------------------------------------------------------------
    # STATIC FILES
    # --------------------------------------------------------------

    def serve_static(self, path):

        if path in ("", "/"):
            path = "/index.html"

        full = os.path.normpath(
            os.path.join(
                STATIC_DIR,
                unquote(path).lstrip("/")
            )
        )

        if (
            not full.startswith(STATIC_DIR + os.sep)
            or not os.path.isfile(full)
        ):
            return self.send_json(
                {"error": "Not found."},
                404
            )

        ctype = (
            mimetypes.guess_type(full)[0]
            or "application/octet-stream"
        )

        with open(full, "rb") as f:
            body = f.read()

        self.send_response(200)

        if ctype.startswith("text/"):
            self.send_header(
                "Content-Type",
                f"{ctype}; charset=utf-8"
            )
        else:
            self.send_header(
                "Content-Type",
                ctype
            )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(body)

    # --------------------------------------------------------------
    # REQUEST DISPATCH
    # --------------------------------------------------------------

    def dispatch(self, method):

        url = urlparse(self.path)

        # Normal website files
        if not url.path.startswith("/api/"):

            if method == "GET":
                return self.serve_static(url.path)

            return self.send_json(
                {"error": "Not found."},
                404
            )

        try:

            query = {
                k: v[0]
                for k, v in parse_qs(
                    url.query,
                    keep_blank_values=True
                ).items()
            }

            body = (
                self.read_body()
                if method in ("POST", "PUT")
                else {}
            )

            with lock:
                result = self.route(
                    method,
                    url.path,
                    query,
                    body
                )

            self.send_json(result)

        except ApiError as e:

            self.send_json(
                {"error": str(e)},
                e.status
            )

        except (ValidationError, ValueError) as e:

            self.send_json(
                {"error": str(e)},
                400
            )

        except Exception as e:

            print(
                "Server error:",
                repr(e)
            )

            self.send_json(
                {"error": "Internal server error."},
                500
            )

    # --------------------------------------------------------------
    # HTTP METHODS
    # --------------------------------------------------------------

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_DELETE(self):
        self.dispatch("DELETE")

    # --------------------------------------------------------------
    # API ROUTES
    # --------------------------------------------------------------

    def route(self, method, path, q, b):

        parts = path.strip("/").split("/")[1:]

        key = (
            method,
            "/".join(parts)
        )

        # ----------------------------------------------------------
        # META
        # ----------------------------------------------------------

        if key == ("GET", "meta"):

            return {
                "moods": manager.all_moods(),
                "genres": manager.all_genres(),
                "users": users.names()
            }

        # ----------------------------------------------------------
        # LOCAL SONGS
        # ----------------------------------------------------------

        if key == ("GET", "songs"):

            return {
                "songs": manager.search(
                    q.get("q", ""),
                    q.get("mood", ""),
                    q.get("genre", "")
                )
            }

        if key == ("POST", "songs"):

            return {
                "song": manager.add_song(
                    b.get("title"),
                    b.get("artist"),
                    b.get("genre"),
                    b.get("year"),
                    b.get("moods")
                )
            }

        # ----------------------------------------------------------
        # UPDATE / DELETE LOCAL SONG
        # ----------------------------------------------------------

        if (
            parts
            and parts[0] == "songs"
            and len(parts) == 2
            and method in ("PUT", "DELETE")
        ):

            song = need_song(parts[1])

            # Jamendo songs cannot be edited or deleted
            # from the local database.
            if str(song["id"]).startswith("jamendo_"):

                raise ApiError(
                    "Jamendo songs cannot be edited or deleted.",
                    400
                )

            if method == "PUT":

                return {
                    "song": manager.update_song(
                        song["id"],
                        b.get("title"),
                        b.get("artist"),
                        b.get("genre"),
                        b.get("year"),
                        b.get("moods")
                    )
                }

            manager.delete_song(song["id"])

            users.purge_song(
                song["id"]
            )

            return {
                "deleted": True
            }

        # ----------------------------------------------------------
        # USER
        # ----------------------------------------------------------

        if key == ("GET", "user"):

            return user_payload(
                q.get("user")
            )

        # ----------------------------------------------------------
        # RECOMMENDATIONS
        # ----------------------------------------------------------

        if key == ("GET", "recommend"):

            name = q.get("user")

            user = users.get(name)

            try:
                limit = max(
                    1,
                    min(
                        20,
                        int(q.get("limit", 5))
                    )
                )

            except ValueError:
                limit = 5

            songs = recommender.recommend(
                q.get("mood", ""),
                limit=limit,
                genre=q.get("genre", ""),
                favorites=user["favorites"],
                recent=users.recent_song_ids(name)
            )

            return {
                "songs": songs
            }

        # ----------------------------------------------------------
        # PLAY
        # ----------------------------------------------------------

        if key == ("POST", "play"):

            song = need_song(
                b.get("song_id")
            )

            users.log_play(
                b.get("user"),
                song,
                b.get("mood")
            )

            return {
                "ok": True
            }

        # ----------------------------------------------------------
        # FAVORITE
        # ----------------------------------------------------------

        if key == ("POST", "favorite"):

            song = need_song(
                b.get("song_id")
            )

            return {
                "favorite": users.toggle_favorite(
                    b.get("user"),
                    song["id"]
                )
            }

        # ----------------------------------------------------------
        # CREATE PLAYLIST
        # ----------------------------------------------------------

        if key == ("POST", "playlists"):

            users.create_playlist(
                b.get("user"),
                b.get("name")
            )

            return {
                "ok": True
            }

        # ----------------------------------------------------------
        # ADD TO PLAYLIST
        # ----------------------------------------------------------

        if key == ("POST", "playlists/add"):

            song = need_song(
                b.get("song_id")
            )

            return {
                "added": users.add_to_playlist(
                    b.get("user"),
                    b.get("playlist"),
                    song["id"]
                )
            }

        # ----------------------------------------------------------
        # REMOVE FROM PLAYLIST
        # ----------------------------------------------------------

        if key == ("POST", "playlists/remove"):

            users.remove_from_playlist(
                b.get("user"),
                b.get("playlist"),
                b.get("song_id")
            )

            return {
                "ok": True
            }

        # ----------------------------------------------------------
        # DELETE PLAYLIST
        # ----------------------------------------------------------

        if key == ("POST", "playlists/delete"):

            users.delete_playlist(
                b.get("user"),
                b.get("name")
            )

            return {
                "ok": True
            }

        # ----------------------------------------------------------
        # CLEAR HISTORY
        # ----------------------------------------------------------

        if key == ("POST", "history/clear"):

            users.clear_history(
                b.get("user")
            )

            return {
                "ok": True
            }

        # ----------------------------------------------------------
        # UNKNOWN ENDPOINT
        # ----------------------------------------------------------

        raise ApiError(
            "Unknown endpoint.",
            404
        )


# ----------------------------------------------------------------------
# SERVER START
# ----------------------------------------------------------------------

def main(port=None):

    port = port or int(
        os.environ.get(
            "PORT",
            8000
        )
    )

    httpd = ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(
        f"MoodSync running at "
        f"http://localhost:{port}  "
        f"(Ctrl+C to stop)"
    )

    try:
        httpd.serve_forever()

    except KeyboardInterrupt:

        print("\nStopped.")


if __name__ == "__main__":
    main()