import requests
import json

class MusicBrainzAPI:
    def __init__(self, base_url='https://musicbrainz.org/ws/2/'):
        self.base_url = base_url

    def search_releases(self, query):
        """Search for releases."""
        url = f'{self.base_url}release/?query={query}&fmt=json'
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if 'releases' in data and len(data['releases']) > 0:
                release_id = data['releases'][0]['id']
                cover_art_url = f'https://coverartarchive.org/release/{release_id}'
                try:
                    cover_art_response = requests.get(cover_art_url)
                    cover_art_response.raise_for_status()
                    return cover_art_response.json()
                except requests.exceptions.RequestException as e:
                    print(f"Error retrieving cover art: {e}")
                    return None
            else:
                print("No releases found.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error making request: {e}")
            return None

# Example usage
# api = MusicBrainzAPI()
# title = "What Difference Does It Make"
# artist = "The Smiths"
# search_results = api.search_releases(f'release:{title} AND artist:{artist}')