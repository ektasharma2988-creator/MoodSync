# MoodSync – Emotion-Based Music Recommender

MoodSync recommends music according to your current mood. It ships as a full-stack web app (HTML/CSS/JS frontend + Python backend + JSON storage) and also keeps the original terminal version.

## Features
- Mood-based recommendations (favorites rank higher, recently played rank lower)
- Songs can have several moods; filter by genre
- Add, edit, delete and search songs
- Per-user favorites, custom playlists and listening history
- Mood breakdown stats
- Persistent JSON storage, no external packages

## Project Structure
```text
MoodSync/
├── server.py          # Backend: HTTP server + REST API (web app entry point)
├── music_manager.py   # Song CRUD, validation, search
├── recommender.py     # Mood scoring
├── user_store.py      # Favorites, playlists, history per user
├── storage.py         # JSON load/save helpers
├── main.py            # Terminal version (optional)
├── requirements.txt
├── README.md
├── static/
│   └── index.html     # Frontend
└── data/
    ├── songs.json
    ├── history.json   # Used by the terminal version
    └── users.json     # Created automatically by the web app
```

## How to Run

1. Install Python 3.9 or newer.
2. Open a terminal inside the MoodSync folder.
3. Start the web app:

```bash
python server.py
```

4. Open http://localhost:8000 and enter a name to sign in.

Use another port with `PORT=9000 python server.py` (Windows PowerShell: `$env:PORT=9000; python server.py`).

Terminal version: `python main.py`

## REST API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/meta` | Moods, genres, known users |
| GET | `/api/songs?q=&mood=&genre=` | Search songs |
| POST | `/api/songs` | Add a song |
| PUT / DELETE | `/api/songs/<id>` | Edit / delete a song |
| GET | `/api/recommend?user=&mood=&genre=&limit=` | Recommendations |
| GET | `/api/user?user=` | Favorites, playlists, history, stats |
| POST | `/api/play` | Log a play |
| POST | `/api/favorite` | Toggle favorite |
| POST | `/api/playlists`, `/add`, `/remove`, `/delete` | Manage playlists |
| POST | `/api/history/clear` | Clear history |

## Future Enhancements
- Spotify/YouTube Music API integration for real audio playback
- Passwords / real authentication
- Mood detection using text sentiment analysis
- Song ratings and feedback
- SQLite database
