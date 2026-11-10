def parse_pgn_file(file_path):
    # Master dictionary: {"YYYY.MM": [game1_dict, game2_dict, ...]}
    games_by_month = {}

    current_game = {}
    in_moves_section = False

    ##turn the pgn game headers into easily readable dictionaries
    with open(file_path, "r", encoding="utf-8") as pgn_file:
        for line in pgn_file:
            line = line.strip()

            # 1. Parsing Header Lines (e.g., [Date "2023.05.14"])
            if line.startswith("[") and line.endswith("]"):
                # Strip the brackets "[" and "]"
                content = line[1:-1]

                # e.g., 'Date "2023.05.14"' -> key='Date', val='"2023.05.14"'
                key = content.split()[0]
                raw_value = content[len(key):]
                # Clean up the quote marks around the value
                value = raw_value.strip().strip('"')

                # Store in our current game's temporary dictionary
                current_game[key] = value

            # 2. Detecting Move Lines
            elif line and not line.startswith("["):
                in_moves_section = True
                # Optional: accumulate move text if you want to store moves
                current_game["Moves"] = current_game.get("Moves", "") + " " + line

            # 3. End of a Game Block (Blank line after reading moves)
            elif line == "" and in_moves_section:
                # Extract month for grouping (e.g., "2023.05" from "2023.05.14")
                date_str = current_game.get("Date", "Unknown.Month")
                month_key = date_str[:7]  # Takes "YYYY.MM"

                # Add to master dictionary
                if month_key not in games_by_month:
                    games_by_month[month_key] = []

                games_by_month[month_key].append(current_game)

                # Reset temporary variables for the next game
                current_game = {}
                in_moves_section = False

    # Handle any remaining game at the very end of the file (there is no empty line after so we need to save this way)
    if current_game and in_moves_section:
        month_key = current_game.get("Date", "Unknown.Month")[:7]
        if month_key not in games_by_month:
            games_by_month[month_key] = []
        games_by_month[month_key].append(current_game)

    print(f"Parsed {sum(len(g) for g in games_by_month.values())} games manually across {len(games_by_month)} months!")

    return games_by_month