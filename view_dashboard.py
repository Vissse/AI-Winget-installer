# view_dashboard.py
import tkinter as tk
from config import COLORS

class DashboardPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller

        # --- HLAVIČKA ---
        # Vycentrovaný kontejner pro vertikální střed
        center_wrapper = tk.Frame(self, bg=COLORS['bg_main'])
        center_wrapper.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.85)

        header_frame = tk.Frame(center_wrapper, bg=COLORS['bg_main'], pady=20)
        header_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(header_frame, text="Vítejte v AI Winget Installer", 
                 font=("Segoe UI", 32, "bold"), bg=COLORS['bg_main'], fg="white").pack(anchor="center")
        
        tk.Label(header_frame, text="Vyberte nástroj, který chcete použít.", 
                 font=("Segoe UI", 12), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(anchor="center", pady=(5, 0))

        # --- KONTEJNER PRO KARTY ---
        grid_frame = tk.Frame(center_wrapper, bg=COLORS['bg_main'])
        grid_frame.pack(fill='both', expand=True)
        
        grid_frame.columnconfigure(0, weight=1, uniform="card")
        grid_frame.columnconfigure(1, weight=1, uniform="card")
        grid_frame.rowconfigure(0, weight=1, uniform="card")
        grid_frame.rowconfigure(1, weight=1, uniform="card")

        # --- KARTY ---
        self.create_card(grid_frame, 0, 0, "📦 Installer", 
                         "Inteligentní vyhledávání a hromadná instalace aplikací.\nVyužívá AI pro nalezení správných ID balíčků.", "installer")

        self.create_card(grid_frame, 0, 1, "🔄 Updater", 
                         "Automatická kontrola zastaralých aplikací.\nUmožňuje hromadnou aktualizaci všeho jedním kliknutím.", "updater")

        self.create_card(grid_frame, 1, 0, "🩺 Health Check", 
                         "Nástroje pro údržbu a opravu systému Windows.\nObsahuje SFC, DISM, čištění disku a správu baterie.", "health")

        self.create_card(grid_frame, 1, 1, "⚙️ Nastavení", 
                         "Správa API klíče pro Google Gemini, změna\nbarevného motivu aplikace a jazykové předvolby.", "settings")

    def create_card(self, parent, row, col, title, description, view_name):
        # Frame karty (Rámeček)
        # Používáme highlightthickness=1 pro rámeček
        card = tk.Frame(parent, bg=COLORS['bg_sidebar'], cursor="hand2", 
                        highlightthickness=1, highlightbackground=COLORS['border'])
        card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")

        # Obsah karty
        # ZMĚNA: Místo place() použijeme pack() s padx/pady=1. 
        # To zajistí, že vnitřní barva nepřekreslí vnější rámeček.
        content = tk.Frame(card, bg=COLORS['bg_sidebar'], cursor="hand2")
        content.pack(fill='both', expand=True, padx=1, pady=1)

        # Helper frame pro vertikální centrování textu uvnitř contentu
        text_wrapper = tk.Frame(content, bg=COLORS['bg_sidebar'], cursor="hand2")
        text_wrapper.place(relx=0.5, rely=0.5, anchor="center", relwidth=1.0)

        lbl_title = tk.Label(text_wrapper, text=title, font=("Segoe UI", 18, "bold"), 
                             bg=COLORS['bg_sidebar'], fg="white", cursor="hand2")
        lbl_title.pack(anchor="center", pady=(0, 10))

        lbl_desc = tk.Label(text_wrapper, text=description, font=("Segoe UI", 10), 
                            bg=COLORS['bg_sidebar'], fg=COLORS['sub_text'], 
                            cursor="hand2", justify="center", wraplength=300)
        lbl_desc.pack(anchor="center")

        # Eventy
        widgets = [card, content, text_wrapper, lbl_title, lbl_desc]

        def on_click(e):
            self.controller.open_view_from_dashboard(view_name)

        def on_enter(e):
            hover_col = COLORS['accent'] # Vždy modrá
            # Změna barvy rámečku
            card.config(highlightbackground=hover_col, bg=COLORS['item_hover'])
            # Změna pozadí vnitřku
            content.config(bg=COLORS['item_hover'])
            text_wrapper.config(bg=COLORS['item_hover'])
            lbl_title.config(bg=COLORS['item_hover'], fg=hover_col)
            lbl_desc.config(bg=COLORS['item_hover'])

        def on_leave(e):
            # Návrat k původním barvám
            card.config(highlightbackground=COLORS['border'], bg=COLORS['bg_sidebar'])
            content.config(bg=COLORS['bg_sidebar'])
            text_wrapper.config(bg=COLORS['bg_sidebar'])
            lbl_title.config(bg=COLORS['bg_sidebar'], fg="white")
            lbl_desc.config(bg=COLORS['bg_sidebar'])

        for w in widgets:
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)