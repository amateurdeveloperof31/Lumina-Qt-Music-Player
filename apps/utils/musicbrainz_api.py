import requests
import json

class MusicBrainzAPI:
        MB_BASE = "https://musicbrainz.org/ws/2/"
        CAA_BASE = "https://coverartarchive.org"
        HEADERS = {"User-Agent": "Lumina/1.0"}

        def _get_cover_for_release(self, release_id):
            r = requests.get(f"{self.CAA_BASE}/release/{release_id}", headers=self.HEADERS, timeout=5)
            if r.ok:
                return r.json()

            rg = requests.get(f"{self.MB_BASE}release/{release_id}", params={"inc": "release-groups", "fmt": "json"},
                headers=self.HEADERS, timeout=5)
            if not rg.ok:
                return None

            rg_id = rg.json().get("release-group", {}).get("id")
            if not rg_id:
                return None

            r2 = requests.get(f"{self.CAA_BASE}/release-group/{rg_id}", headers=self.HEADERS, timeout=5)
            return r2.json() if r2.ok else None

        def search_releases(self, song_title, song_artist, album_title=None):
            queries = []

            if album_title:
                queries += [
                    f'recording:"{song_title}" AND artist:"{song_artist}" AND release:"{album_title}"',
                    f'recording:"{song_title}" AND release:"{album_title}"',
                ]

            queries += [
                f'recording:"{song_title}" AND artist:"{song_artist}"',
                f'"{song_title}" "{song_artist}"',
                f'{song_title} {song_artist}',
                f'{song_title}'
            ]

            for query in queries:
                try:
                    response = requests.get(f"{self.MB_BASE}recording/", params={"query": query, "fmt": "json"},
                                                headers=self.HEADERS, timeout=5)
                    response.raise_for_status()
                    recordings = response.json().get("recordings", [])

                    for recording in recordings:
                        # Skip low-confidence matches
                        if int(recording.get("score", 0)) < 60:
                            continue

                        for release in recording.get("releases", []):
                            release_id = release.get("id")
                            release_title = release.get("title", "").lower()
                            if album_title and album_title.lower() not in release_title:
                                continue

                            if not release_id:
                                continue

                            art = self._get_cover_for_release(release_id)
                            if art:
                                release_url = f"https://musicbrainz.org/release/{release_id}"
                                print(f"Cover found: {release_url}")
                                print(art)
                                return art

                except Exception as e:
                    print(f"Query failed: {query!r} — {e}")

            return None

        def get_front_image_url(self, song_title, song_artist):
            data = self.search_releases(song_title, song_artist)
            if not data:
                return None
            for image in data.get("images", []):
                if image.get("front"):
                    return image.get("image")
            return None

# # Example usage
# api = MusicBrainzAPI()
# title = "Ambition"
# artist = "Nao Sato"
# album = "Resident Evil Requiem Original Soundtrack"
# search_results = api.search_releases(title, artist, album)