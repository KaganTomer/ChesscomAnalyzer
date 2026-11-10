"""
Chess.com Stats Analyzer — Desktop GUI
Wraps game_downloader.py / parser.py / analyzer.py in a Tkinter interface.
"""
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from game_downloader import download_data
from parser import parse_pgn_file
from analyzer import analyze_user_stats

# ---------------------------------------------------------------- palette --
BG_MAIN      = "#ffffff"   # Main background (White)
BG_PANEL     = "#f4f4f4"   # Cards / Sidebar / Tables (Off-White)
BG_PANEL_HI  = "#e0e0e0"   # Hovered / Alt Row
BLACK        = "#000000"   # Main accents
GRAY         = "#888888"   # Secondary accents
TEXT         = "#000000"   # Main text
TEXT_MUTED   = "#555555"   # Subtitles
FONT_FAMILY  = "Segoe UI"

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


class StatCard(tk.Frame):
    """A small rounded-feel stat tile: big value on top, muted label below."""
    def __init__(self, parent, label, value="—", accent=BLACK, **kw):
        super().__init__(parent, bg=BG_PANEL, highlightthickness=1,
                          highlightbackground="#dddddd", **kw)
        self.value_lbl = tk.Label(self, text=value, font=(FONT_FAMILY, 20, "bold"),
                                   fg=accent, bg=BG_PANEL)
        self.value_lbl.pack(pady=(12, 2), padx=16, anchor="w")
        self.label_lbl = tk.Label(self, text=label.upper(), font=(FONT_FAMILY, 8, "bold"),
                                   fg=TEXT_MUTED, bg=BG_PANEL)
        self.label_lbl.pack(pady=(0, 10), padx=16, anchor="w")

    def set(self, value):
        self.value_lbl.config(text=value)


class ChessAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chess.com Stats Analyzer")
        self.geometry("1280x860")
        self.minsize(1100, 750)
        self.configure(bg=BG_MAIN)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.msg_queue = queue.Queue()
        self.stats_by_month = {}
        self.all_time_stats = {}

        self._build_style()
        self._build_header()
        self._build_body()
        self._poll_queue()

    def _on_close(self):
        """Clean up resources and exit process when closing the window."""
        plt.close("all")  # Release all Matplotlib figure resources
        self.destroy()  # Destroy the Tkinter window
        import sys
        sys.exit(0)  # Forcefully terminate the Python process cleanly

    # ------------------------------------------------------------- styling
    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("Treeview", background=BG_PANEL, foreground=TEXT,
                         fieldbackground=BG_PANEL, borderwidth=0, rowheight=28,
                         font=(FONT_FAMILY, 9))
        style.configure("Treeview.Heading", background="#eeeeee", foreground=BLACK,
                         font=(FONT_FAMILY, 9, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", "#dcdcdc")], foreground=[("selected", BLACK)])

        style.configure("TProgressbar", troughcolor=BG_PANEL, background=BLACK,
                         bordercolor=BG_MAIN, lightcolor=BLACK, darkcolor=BLACK)

    # -------------------------------------------------------------- header
    def _build_header(self):
        header = tk.Frame(self, bg=BG_MAIN)
        header.pack(fill="x", padx=24, pady=(20, 10))

        title = tk.Label(header, text="♞ Chess.com Stats Analyzer",
                          font=(FONT_FAMILY, 20, "bold"), fg=BLACK, bg=BG_MAIN)
        title.pack(side="left")

        controls = tk.Frame(header, bg=BG_MAIN)
        controls.pack(side="right")

        tk.Label(controls, text="Chess.com username:", font=(FONT_FAMILY, 10),
                 fg=TEXT_MUTED, bg=BG_MAIN).pack(side="left", padx=(0, 8))

        self.username_var = tk.StringVar()
        entry = tk.Entry(controls, textvariable=self.username_var, width=22,
                          font=(FONT_FAMILY, 11), bg=BG_PANEL, fg=TEXT,
                          insertbackground=TEXT, relief="flat",
                          highlightthickness=1, highlightbackground="#cccccc",
                          highlightcolor=BLACK)
        entry.pack(side="left", ipady=5, padx=(0, 10))
        entry.bind("<Return>", lambda e: self._on_analyze())

        self.analyze_btn = tk.Button(controls, text="Analyze", command=self._on_analyze,
                                      bg=BLACK, fg=BG_MAIN, activebackground=TEXT_MUTED,
                                      activeforeground=BG_MAIN, font=(FONT_FAMILY, 10, "bold"),
                                      relief="flat", padx=18, pady=6, cursor="hand2")
        self.analyze_btn.pack(side="left")

        # status row
        status_row = tk.Frame(self, bg=BG_MAIN)
        status_row.pack(fill="x", padx=24)
        self.status_var = tk.StringVar(value="Enter a username and click Analyze.")
        tk.Label(status_row, textvariable=self.status_var, font=(FONT_FAMILY, 9),
                 fg=TEXT_MUTED, bg=BG_MAIN, anchor="w").pack(side="left", fill="x", expand=True)
        self.progress = ttk.Progressbar(status_row, mode="indeterminate", length=160)
        self.progress.pack(side="right", pady=(0, 8))

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=24, pady=(4, 0))

    # ---------------------------------------------------------------- body
    def _build_body(self):
        body = tk.Frame(self, bg=BG_MAIN)
        body.pack(fill="both", expand=True, padx=24, pady=16)

        # ---- sidebar: month list ----
        sidebar = tk.Frame(body, bg=BG_PANEL, width=200, highlightthickness=1,
                            highlightbackground="#e2e2e2")
        sidebar.pack(side="left", fill="y", padx=(0, 16))
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="MONTHS", font=(FONT_FAMILY, 9, "bold"),
                 fg=TEXT_MUTED, bg=BG_PANEL).pack(anchor="w", padx=14, pady=(14, 6))

        list_frame = tk.Frame(sidebar, bg=BG_PANEL)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.month_list = tk.Listbox(list_frame, bg=BG_PANEL, fg=TEXT,
                                      selectbackground=BLACK, selectforeground=BG_MAIN,
                                      font=(FONT_FAMILY, 10), relief="flat",
                                      highlightthickness=0, activestyle="none",
                                      yscrollcommand=scrollbar.set)
        self.month_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.month_list.yview)
        self.month_list.bind("<<ListboxSelect>>", self._on_month_select)

        # ---- main grid ----
        self.main_grid = tk.Frame(body, bg=BG_MAIN)
        self.main_grid.pack(side="left", fill="both", expand=True)

        self.main_grid.rowconfigure(0, weight=0) # Stat Cards
        self.main_grid.rowconfigure(1, weight=1) # Tables (Openings/Time Controls)
        self.main_grid.rowconfigure(2, weight=1) # Charts (Colors/Elo)
        self.main_grid.columnconfigure(0, weight=1, uniform="col")
        self.main_grid.columnconfigure(1, weight=1, uniform="col")

        self._build_overview_cards()
        self._build_tables()
        self._build_charts()

    def _build_overview_cards(self):
        cards_frame = tk.Frame(self.main_grid, bg=BG_MAIN)
        cards_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 12))

        for c in range(4):
            cards_frame.columnconfigure(c, weight=1, uniform="ccol")

        self.card_games = StatCard(cards_frame, "Games Played")
        self.card_wins = StatCard(cards_frame, "Wins", accent=BLACK)
        self.card_losses = StatCard(cards_frame, "Losses", accent=GRAY)
        self.card_draws = StatCard(cards_frame, "Draws", accent=TEXT_MUTED)
        self.card_win_rate = StatCard(cards_frame, "Win Rate", accent=BLACK)
        self.card_loss_rate = StatCard(cards_frame, "Loss Rate", accent=GRAY)
        self.card_draw_rate = StatCard(cards_frame, "Draw Rate", accent=TEXT_MUTED)
        self.card_top_opening = StatCard(cards_frame, "Top Opening")

        cards = [self.card_games, self.card_wins, self.card_losses, self.card_draws,
                 self.card_win_rate, self.card_loss_rate, self.card_draw_rate, self.card_top_opening]

        for i, card in enumerate(cards):
            r, c = divmod(i, 4)
            card.grid(row=r, column=c, sticky="nsew", padx=4, pady=4)

    def _build_tables(self):
        # Openings container
        container_openings = tk.Frame(self.main_grid, bg=BG_MAIN, highlightthickness=1, highlightbackground="#dddddd")
        container_openings.grid(row=1, column=0, sticky="nsew", padx=(4, 4), pady=(4, 4))

        header_o = tk.Label(container_openings, text="TOP 10 OPENINGS", font=(FONT_FAMILY, 9, "bold"), bg=BG_PANEL, fg=BLACK, anchor="w", padx=10, pady=5)
        header_o.pack(fill="x")
        self.tree_openings = self._create_treeview(container_openings, ("Opening", "Games"))

        # Time controls container
        container_time = tk.Frame(self.main_grid, bg=BG_MAIN, highlightthickness=1, highlightbackground="#dddddd")
        container_time.grid(row=1, column=1, sticky="nsew", padx=(4, 4), pady=(4, 4))

        header_t = tk.Label(container_time, text="TOP 10 TIME CONTROLS", font=(FONT_FAMILY, 9, "bold"), bg=BG_PANEL, fg=BLACK, anchor="w", padx=10, pady=5)
        header_t.pack(fill="x")
        self.tree_time = self._create_treeview(container_time, ("Time Control", "Games"))

    def _create_treeview(self, parent, columns):
        tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col.upper())
            tree.column(col, anchor="w" if col != columns[-1] else "center")
        tree.column(columns[-1], width=100, anchor="center")
        vsb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        return tree

    def _build_charts(self):
        # Colors chart container
        container_colors = tk.Frame(self.main_grid, bg=BG_MAIN, highlightthickness=1, highlightbackground="#dddddd")
        container_colors.grid(row=2, column=0, sticky="nsew", padx=(4, 4), pady=(4, 4))

        self.fig_colors, self.ax_colors = plt.subplots(figsize=(4, 3), dpi=100)
        self._style_fig(self.fig_colors, self.ax_colors)
        self.canvas_colors = FigureCanvasTkAgg(self.fig_colors, master=container_colors)
        self.canvas_colors.get_tk_widget().pack(fill="both", expand=True)

        # Elo chart container
        container_elo = tk.Frame(self.main_grid, bg=BG_MAIN, highlightthickness=1, highlightbackground="#dddddd")
        container_elo.grid(row=2, column=1, sticky="nsew", padx=(4, 4), pady=(4, 4))

        self.fig_elo, self.ax_elo = plt.subplots(figsize=(4, 3), dpi=100)
        self._style_fig(self.fig_elo, self.ax_elo)
        self.canvas_elo = FigureCanvasTkAgg(self.fig_elo, master=container_elo)
        self.canvas_elo.get_tk_widget().pack(fill="both", expand=True)

    def _style_fig(self, fig, ax):
        fig.patch.set_facecolor(BG_MAIN)
        ax.set_facecolor(BG_MAIN)
        ax.tick_params(colors=TEXT_MUTED)
        for spine in ax.spines.values():
            spine.set_color("#cccccc")
        ax.grid(True, color="#eeeeee", linewidth=1, alpha=0.8)

    # --------------------------------------------------------- interaction
    def _on_analyze(self):
        username = self.username_var.get().strip()
        if not username:
            messagebox.showwarning("Missing username", "Please enter a Chess.com username.")
            return

        self.analyze_btn.config(state="disabled")
        self.progress.start(12)
        self.status_var.set(f"Starting analysis for '{username}'...")
        self.month_list.delete(0, "end")

        os.makedirs(DATA_DIR, exist_ok=True)
        file_path = os.path.join(DATA_DIR, f"{username}_games.pgn")

        thread = threading.Thread(target=self._run_pipeline, args=(username, file_path), daemon=True)
        thread.start()

    def _run_pipeline(self, username, file_path):
        try:
            download_data(username, file_path=file_path,
                          status_callback=lambda msg: self.msg_queue.put(("status", msg)))
            self.msg_queue.put(("status", "Parsing PGN data..."))
            games_by_month = parse_pgn_file(file_path)
            if not games_by_month:
                raise ValueError("No games found to parse.")
            self.msg_queue.put(("status", "Crunching stats..."))
            stats_by_month, all_time_stats = analyze_user_stats(games_by_month, username)
            self.msg_queue.put(("done", (stats_by_month, all_time_stats)))
        except Exception as e:
            self.msg_queue.put(("error", str(e)))

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "status":
                    self.status_var.set(payload)
                elif kind == "error":
                    self.progress.stop()
                    self.analyze_btn.config(state="normal")
                    self.status_var.set("Something went wrong.")
                    messagebox.showerror("Error", payload)
                elif kind == "done":
                    self.stats_by_month, self.all_time_stats = payload
                    self._on_data_ready()
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _on_data_ready(self):
        self.progress.stop()
        self.analyze_btn.config(state="normal")
        self.status_var.set(f"Done — {self.all_time_stats.get('total_games_played', 0)} games analyzed.")

        self.month_list.insert("end", "All Time")
        for month in sorted(self.stats_by_month.keys()):
            self.month_list.insert("end", month)
        self.month_list.selection_set(0)
        self._render_selection("All Time")

    def _on_month_select(self, event):
        sel = self.month_list.curselection()
        if not sel:
            return
        value = self.month_list.get(sel[0])
        self._render_selection(value)


    # ------------------------------------------------------ normalization
    def _get_display_stats(self, selection):
        """Maps either all_time_stats or a single month's stats onto one common shape."""
        if selection == "All Time":
            s = self.all_time_stats
            return {
                "games": s.get("total_games_played", 0),
                "wins": s.get("total_wins", 0),
                "losses": s.get("total_losses", 0),
                "draws": s.get("total_draws", 0),
                "win_rate": s.get("total_win_rate", 0.0),
                "loss_rate": s.get("total_loss_rate", 0.0),
                "draw_rate": s.get("total_draws_rate", 0.0),
                "wins_white": s.get("total_wins_on_white", 0),
                "losses_white": s.get("total_losses_on_white", 0),
                "wins_black": s.get("total_wins_on_black", 0),
                "losses_black": s.get("total_losses_on_black", 0),
                "draws_white": s.get("total_draws_on_white", 0),
                "draws_black": s.get("total_draws_on_black", 0),
                "openings": s.get("total_top10_openings", {}),
                "time_controls": s.get("total_top10_time_controls", {}),
                "elo_series": s.get("total_elo_overtime_alltime", []),
            }
        else:
            s = self.stats_by_month[selection]
            return {
                "games": s.get("games_this_month", 0),
                "wins": s.get("month_wins", 0),
                "losses": s.get("month_losses", 0),
                "draws": s.get("month_draws", 0),
                "win_rate": s.get("month_win_rate", 0.0),
                "loss_rate": s.get("month_loss_rate", 0.0),
                "draw_rate": s.get("month_draws_rate", 0.0),
                "wins_white": s.get("wins_on_white", 0),
                "losses_white": s.get("losses_on_white", 0),
                "wins_black": s.get("wins_on_black", 0),
                "losses_black": s.get("losses_on_black", 0),
                "draws_white": s.get("draws_on_white", 0),
                "draws_black": s.get("draws_on_black", 0),
                "openings": s.get("month_top10_openings", {}),
                "time_controls": s.get("month_top10_time_controls", {}),
                "elo_series": s.get("elo_overtime_month", []),
            }

    # ------------------------------------------------------------ render
    def _render_selection(self, selection):
        d = self._get_display_stats(selection)

        self.card_games.set(d["games"])
        self.card_wins.set(d["wins"])
        self.card_losses.set(d["losses"])
        self.card_draws.set(d["draws"])
        self.card_win_rate.set(f"{d['win_rate']:.1f}%")
        self.card_loss_rate.set(f"{d['loss_rate']:.1f}%")
        self.card_draw_rate.set(f"{d['draw_rate']:.1f}%")
        top_opening = next(iter(d["openings"]), "—")
        self.card_top_opening.set(top_opening[:22] + ("…" if len(top_opening) > 22 else ""))

        self._render_colors_chart(d)

        # Get only the top 10 items to display
        top10_openings = dict(list(d["openings"].items())[:10])
        top10_time_controls = dict(list(d["time_controls"].items())[:10])

        self._render_table(self.tree_openings, top10_openings)
        self._render_table(self.tree_time, top10_time_controls)
        self._render_elo_chart(d["elo_series"])

    def _render_colors_chart(self, d):
        ax = self.ax_colors
        ax.clear()
        self._style_fig(self.fig_colors, ax)

        categories = ["Wins", "Losses", "Draws"]
        white_vals = [d["wins_white"], d["losses_white"], d["draws_white"]]
        black_vals = [d["wins_black"], d["losses_black"], d["draws_black"]]

        x = range(len(categories))
        width = 0.35
        # Thematic coloring for "As White" and "As Black"
        ax.bar([i - width / 2 for i in x], white_vals, width, label="As White",
               color=BG_MAIN, edgecolor=BLACK, linewidth=1.5)
        ax.bar([i + width / 2 for i in x], black_vals, width, label="As Black",
               color=BLACK, edgecolor=BLACK, linewidth=1.5)

        ax.set_xticks(list(x))
        ax.set_xticklabels(categories, color=BLACK)
        ax.set_title("Results by Color", color=BLACK, fontsize=10, fontweight="bold", pad=12)

        legend = ax.legend(facecolor=BG_MAIN, edgecolor="#cccccc", labelcolor=BLACK, loc="upper right")
        self.fig_colors.tight_layout()
        self.canvas_colors.draw()

    def _render_table(self, tree, data_dict):
        tree.delete(*tree.get_children())
        for name, count in data_dict.items():
            tree.insert("", "end", values=(name.title(), count))

    def _render_elo_chart(self, elo_series):
        ax = self.ax_elo
        ax.clear()
        self._style_fig(self.fig_elo, ax)

        numeric_elos = []
        for e in elo_series:
            try:
                numeric_elos.append(int(e))
            except (ValueError, TypeError):
                continue

        if numeric_elos:
            ax.plot(range(1, len(numeric_elos) + 1), numeric_elos, color=BLACK,
                    linewidth=2, marker="o", markersize=4, markerfacecolor=BG_MAIN, markeredgecolor=BLACK)
            ax.set_title("Elo Rating Over Games", color=BLACK, fontsize=10, fontweight="bold", pad=12)
            ax.set_xlabel("Game #", color=TEXT_MUTED, fontsize=8)
            ax.set_ylabel("Elo", color=TEXT_MUTED, fontsize=8)
        else:
            ax.text(0.5, 0.5, "No Elo data available", ha="center", va="center",
                    color=TEXT_MUTED, transform=ax.transAxes)

        self.fig_elo.tight_layout()
        self.canvas_elo.draw()


def main():
    app = ChessAnalyzerApp()
    app.mainloop()


if __name__ == "__main__":
    main()