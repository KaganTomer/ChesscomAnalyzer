# Chess.com Stats Analyzer (Desktop GUI)

A Tkinter desktop app that downloads your Chess.com game history, parses it,
and shows your stats in a dark, chess.com-styled interface.

## Files

- `main.py` — run this to launch the app
- `app.py` — the Tkinter GUI
- `game_downloader.py` — downloads your PGN archives from the Chess.com API
- `parser.py` — parses PGN files into per-month game dictionaries
- `analyzer.py` — computes win/loss/draw rates, openings, time controls, Elo trend

## Setup

1. Install Python 3.9+.
2. Install the one extra dependency (everything else — tkinter, urllib, json — is
   in the standard library):

   ```bash
   pip install matplotlib
   ```

   Note: on Linux, if `tkinter` isn't already available, install it via your
   package manager first, e.g. `sudo apt install python3-tk`.

3. Run it:

   ```bash
   python main.py
   ```

## Using it

1. Type a Chess.com username and click **Analyze** (or press Enter).
2. The app downloads your monthly archives into a `data/` folder next to the
   app, parses them, and crunches your stats — status updates show at the top.
3. Pick **All Time** or any month from the left sidebar to see:
   - **Overview** — games, wins/losses/draws, win/loss/draw rate, top opening
   - **Colors** — results broken down by White vs Black
   - **Openings** — your top 10 openings
   - **Time Controls** — your top 10 time controls
   - **Elo Trend** — a line chart of your rating across games

Downloaded PGN files are cached in `data/<username>_games.pgn` so you can
re-run the analysis offline later by re-importing `parser`/`analyzer` directly.
