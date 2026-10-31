from music_manager import MusicManager, ValidationError
from recommender import MusicRecommender
from storage import load_json, save_json

SONGS_FILE = "data/songs.json"
HISTORY_FILE = "data/history.json"

def print_header(title):
    print("\n" + "=" * 60)
    print(f"{title:^60}")
    print("=" * 60)

def show_songs(songs):
    if not songs:
        print("No songs found.")
        return
    for i, song in enumerate(songs, 1):
        print(f"{i}. {song['title']} — {song['artist']} | {', '.join(song['moods'])} | {song['genre']} | {song['year']}")

def get_mood():
    moods = ["Happy", "Sad", "Calm", "Angry", "Romantic", "Energetic"]
    print("\nAvailable moods:")
    for mood in moods:
        print(f"- {mood}")
    return input("Enter your mood: ").strip().title()

def add_song(manager):
    print_header("Add Song")
    title = input("Song title: ").strip()
    artist = input("Artist: ").strip()
    moods = input("Moods (comma-separated): ").strip()
    genre = input("Genre: ").strip().title()
    year = input("Year: ").strip()
    try:
        manager.add_song(title, artist, genre, year, moods)
    except ValidationError as e:
        print(e)
        return
    print("Song added successfully.")

def update_song(manager):
    print_header("Update Song")
    show_songs(manager.songs)
    try:
        index = int(input("Enter song number to update: ")) - 1
        song = manager.songs[index]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    title = input(f"Title [{song['title']}]: ").strip() or song["title"]
    artist = input(f"Artist [{song['artist']}]: ").strip() or song["artist"]
    moods = input(f"Moods [{', '.join(song['moods'])}]: ").strip() or song["moods"]
    genre = input(f"Genre [{song['genre']}]: ").strip().title() or song["genre"]
    year = input(f"Year [{song['year']}]: ").strip() or song["year"]
    try:
        manager.update_song(song["id"], title, artist, genre, year, moods)
    except ValidationError as e:
        print(e)
        return
    print("Song updated successfully.")

def delete_song(manager):
    print_header("Delete Song")
    show_songs(manager.songs)
    try:
        index = int(input("Enter song number to delete: ")) - 1
        song = manager.songs[index]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return
    confirm = input(f"Delete '{song['title']}'? (y/n): ").strip().lower()
    if confirm == "y":
        manager.delete_song(song["id"])
        print("Song deleted successfully.")

def recommend(manager, recommender):
    print_header("Mood-Based Recommendation")
    mood = get_mood()
    recommendations = recommender.recommend(mood, limit=5)
    if not recommendations:
        print("No songs available for this mood.")
        return

    print(f"\nRecommended songs for {mood}:")
    show_songs(recommendations)

    history = load_json(HISTORY_FILE, [])
    history.append({"mood": mood, "recommendations": recommendations})
    save_json(HISTORY_FILE, history)
    print("\nRecommendation saved to history.")

def search_songs(manager):
    print_header("Search Songs")
    keyword = input("Enter title, artist, mood, or genre: ").strip().lower()
    results = [
        s for s in manager.songs
        if keyword in s["title"].lower()
        or keyword in s["artist"].lower()
        or any(keyword in m.lower() for m in s["moods"])
        or keyword in s["genre"].lower()
    ]
    show_songs(results)

def show_history():
    print_header("Recommendation History")
    history = load_json(HISTORY_FILE, [])
    if not history:
        print("No recommendation history yet.")
        return
    for i, item in enumerate(history, 1):
        print(f"\n{i}. Mood: {item['mood']}")
        show_songs(item["recommendations"])

def show_report(manager):
    print_header("MoodSync Summary Report")
    songs = manager.songs
    history = load_json(HISTORY_FILE, [])

    print(f"Total songs: {len(songs)}")
    print(f"Total recommendation sessions: {len(history)}")

    mood_counts = {}
    genre_counts = {}
    for song in songs:
        for m in song["moods"]:
            mood_counts[m] = mood_counts.get(m, 0) + 1
        genre_counts[song["genre"]] = genre_counts.get(song["genre"], 0) + 1

    print("\nSongs by mood:")
    for mood, count in sorted(mood_counts.items()):
        print(f"  {mood}: {count}")

    print("\nSongs by genre:")
    for genre, count in sorted(genre_counts.items()):
        print(f"  {genre}: {count}")

def main():
    manager = MusicManager(SONGS_FILE)
    recommender = MusicRecommender(manager)

    while True:
        print_header("MoodSync – Emotion-Based Music Recommender")
        print("1. Get music recommendations")
        print("2. View all songs")
        print("3. Search songs")
        print("4. Add a song")
        print("5. Update a song")
        print("6. Delete a song")
        print("7. View recommendation history")
        print("8. View summary report")
        print("9. Exit")

        choice = input("\nEnter your choice: ").strip()

        if choice == "1":
            recommend(manager, recommender)
        elif choice == "2":
            print_header("All Songs")
            show_songs(manager.songs)
        elif choice == "3":
            search_songs(manager)
        elif choice == "4":
            add_song(manager)
        elif choice == "5":
            update_song(manager)
        elif choice == "6":
            delete_song(manager)
        elif choice == "7":
            show_history()
        elif choice == "8":
            show_report(manager)
        elif choice == "9":
            print("\nThank you for using MoodSync!")
            break
        else:
            print("Invalid choice. Please try again.")

        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
