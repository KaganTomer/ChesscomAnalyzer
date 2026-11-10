import json
import urllib
import urllib.request
import urllib.error
from time import sleep


def download_data(username, file_path="test.txt", status_callback=None):
    """
    Downloads all monthly PGN archives for a Chess.com username into a single file.

    status_callback: optional function(str) -> None, called with progress messages.
    Falls back to print() if not provided, so this still works when run standalone.
    """
    def log(msg):
        if status_callback:
            status_callback(msg)
        else:
            print(msg)

    headers = {
        "User-Agent": "ChessProject/1.0 (Learning Python Project)"
    }
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"

    try:
        req = urllib.request.Request(archives_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"No Chess.com account found for username '{username}'. Double-check the spelling.")
        raise ValueError(f"Chess.com API error ({e.code}) while fetching archives for '{username}'.")
    except urllib.error.URLError as e:
        raise ValueError(f"Could not reach Chess.com: {e.reason}")

    monthly_urls = data.get("archives", [])
    if not monthly_urls:
        raise ValueError(f"'{username}' has no game archives on Chess.com.")

    with open(file_path, "w", encoding="utf-8") as games_file:
        for i, url in enumerate(monthly_urls, start=1):
            pgn_url = f"{url}/pgn"
            label = f"{url.split('/')[-2]}/{url.split('/')[-1]}"
            log(f"Downloading games from {label}  ({i}/{len(monthly_urls)})")

            try:
                pgn_req = urllib.request.Request(pgn_url, headers=headers)
                with urllib.request.urlopen(pgn_req) as response:
                    games_file.write(response.read().decode("utf-8"))
                    games_file.write("\n\n")
            except urllib.error.HTTPError as e:
                log(f"  Skipped {label}: HTTP {e.code}")
            except urllib.error.URLError as e:
                log(f"  Skipped {label}: {e.reason}")

            sleep(0.5)

    log(f"Finished downloading {len(monthly_urls)} monthly archive(s).")
    return file_path
