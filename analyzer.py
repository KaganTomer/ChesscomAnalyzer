def analyze_user_stats(games_by_month, target_user):
    target_user = target_user.lower()

    stats_by_month = {}
    all_time_stats = {
        "total_games_played" : 0,
        "total_wins" : 0,
        "total_losses" : 0,
        "total_draws" : 0,
        "total_wins_on_white" : 0,
        "total_losses_on_white" : 0,
        "total_wins_on_black" : 0,
        "total_losses_on_black" : 0,
        "total_draws_on_white" : 0,
        "total_draws_on_black" : 0,
        "total_win_rate" : 0,
        "total_loss_rate" : 0,
        "total_draws_rate" : 0,
        "total_openings" : {}, # {"op1" : count, "op2" : count, ...}
        "total_time_controls" : {}, # {"time1" : count, "time2" : count, ...}
        "total_elo_overtime_alltime" : [] # [elo1, elo1, elo3, ...] all time

    }
    for month_key, game_list in games_by_month.items():
        games_this_month = 0
        month_wins = 0
        month_losses = 0
        month_draws = 0
        wins_on_white = 0
        losses_on_white = 0
        wins_on_black = 0
        losses_on_black = 0
        draws_on_white = 0
        draws_on_black = 0

        month_openings = {} # {"op1" : count, "op2" : count, ...}
        time_controls = {} # {"time1" : count, "time2" : count, ...}
        elo_overtime_month = [] # [elo1, elo1, elo3, ...] for the month


        for game in game_list:
            white = game.get("White", "").lower() # lowering to match
            black = game.get("Black", "").lower()
            result = game.get("Result", "*")
            opening = game.get("ECOUrl", "https://www.chess.com/openings/Unknown-Opening")
            time_control = game.get("TimeControl", "Unknown")

            if white == target_user:
                user_color = "White"
            elif black == target_user:
                user_color = "Black"
            else:
                continue #skips the game if the user is not any of the players (could happen due to errors and problems in downloading and processing data)

            # process game results
            games_this_month += 1
            if result == "1-0":
                if user_color == "White":
                    wins_on_white += 1
                    month_wins += 1
                else:
                    losses_on_black += 1
                    month_losses += 1
            elif result == "0-1":
                if user_color == "Black":
                    wins_on_black += 1
                    month_wins += 1
                else:
                    losses_on_white += 1
                    month_losses += 1
            elif result == "1/2-1/2":
                month_draws += 1
                if user_color == "White":
                    draws_on_white += 1
                else:
                    draws_on_black += 1

            # process opening from url given
            opening_slug = opening.split("/")[-1]
            clean_opening = opening_slug.replace("-", " ")

            if clean_opening in month_openings:
                month_openings[clean_opening] += 1
            else:
                month_openings[clean_opening] = 1
            if clean_opening in all_time_stats["total_openings"]:
                all_time_stats["total_openings"][clean_opening] += 1 #count for total as well
            else:
                all_time_stats["total_openings"][clean_opening] = 1 #count for total as well


            #process time control
            if time_control in time_controls:
                time_controls[time_control] += 1
            else:
                time_controls[time_control] = 1
            if time_control in all_time_stats["total_time_controls"]:
                all_time_stats["total_time_controls"][time_control] += 1 #count for total as well
            else:
                all_time_stats["total_time_controls"][time_control] = 1 #count for total as well

            #process elo
            if user_color == "White":
                elo = game.get("WhiteElo", "")
                elo_overtime_month.append(elo)
            elif user_color == "Black":
                elo = game.get("BlackElo", "")
                elo_overtime_month.append(elo)


        #calculate rates
        month_win_rate = (month_wins / games_this_month * 100) if games_this_month > 0 else 0.0 # prevents division by zero
        month_loss_rate = (month_losses / games_this_month * 100) if games_this_month > 0 else 0.0 # prevents division by zero
        month_draws_rate = (month_draws / games_this_month * 100) if games_this_month > 0 else 0.0 # prevents division by zero

        #save the month stats into the stats dictionary
        stats_by_month[month_key] = {
            "games_this_month" : games_this_month,
            "month_wins" : month_wins,
            "month_losses" : month_losses,
            "month_draws" : month_draws,
            "wins_on_white" : wins_on_white,
            "losses_on_white" : losses_on_white,
            "wins_on_black" : wins_on_black,
            "losses_on_black" : losses_on_black,
            "draws_on_white" : draws_on_white,
            "draws_on_black" : draws_on_black,
            "month_win_rate" :  month_win_rate,
            "month_loss_rate" :  month_loss_rate,
            "month_draws_rate" :  month_draws_rate,
            "month_top10_openings" : dict(sorted(month_openings.items(), key=lambda item: item[1], reverse=True)[:10]),  # {"op1" : count, "op2" : count, ...}
            "month_top10_time_controls" : dict(sorted(time_controls.items(), key=lambda item: item[1], reverse=True)[:10]), # {"time1" : count, "time2" : count, ...}
            "elo_overtime_month" : elo_overtime_month  # [elo1, elo1, elo3, ...] for the month
        }

        #update the total stats
        all_time_stats["total_games_played"] += games_this_month
        all_time_stats["total_wins"] += month_wins
        all_time_stats["total_losses"] += month_losses
        all_time_stats["total_draws"] += month_draws
        all_time_stats["total_wins_on_white"] += wins_on_white
        all_time_stats["total_losses_on_white"] += losses_on_white
        all_time_stats["total_wins_on_black"] += wins_on_black
        all_time_stats["total_losses_on_black"] += losses_on_black
        all_time_stats["total_draws_on_white"] += draws_on_white
        all_time_stats["total_draws_on_black"] += draws_on_black
        all_time_stats["total_elo_overtime_alltime"].extend(elo_overtime_month)

    # instead of updating the total rates each month, updates one time after
    all_time_stats["total_win_rate"] = ((all_time_stats["total_wins"]) / (all_time_stats["total_games_played"])) * 100 if all_time_stats["total_games_played"] > 0 else 0.0 # prevents division by zero
    all_time_stats["total_loss_rate"] = ((all_time_stats["total_losses"])/ (all_time_stats["total_games_played"] ))* 100 if all_time_stats["total_games_played"] > 0 else 0.0 # prevents division by zero
    all_time_stats["total_draws_rate"] = ((all_time_stats["total_draws"]) / (all_time_stats["total_games_played"])) * 100 if all_time_stats["total_games_played"] > 0 else 0.0 # prevents division by zero
    all_time_stats["total_top10_openings"] = dict(sorted(all_time_stats["total_openings"].items(), key=lambda item: item[1], reverse=True)[:10])
    all_time_stats["total_top10_time_controls"] = dict(sorted(all_time_stats["total_time_controls"].items(), key=lambda item: item[1], reverse=True)[:10])


    print("SUCCESSFULLY ANALYZED USER'S STATS")

    return stats_by_month, all_time_stats