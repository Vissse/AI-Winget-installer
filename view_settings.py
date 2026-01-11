# view_settings.py
import tkinter as tk
from tkinter import messagebox
import webbrowser
import threading
from google import genai 
from google.genai import types

from config import COLORS, THEMES
from settings_manager import SettingsManager
from updater import GitHubUpdater

class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        self.settings = SettingsManager.load_settings()
        
        # Načtení hodnot
        self.current_key = self.settings.get("api_key", "")
        
        saved_theme = self.settings.get("theme", "Dark (Default)")
        # Fix pro staré názvy
        if saved_theme == "Notion Light": saved_theme = "Light (Minimal)"
        self.current_theme = saved_theme
        
        self.current_lang = self.settings.get("language", "Čeština")

        # --- HLAVIČKA ---
        header = tk.Frame(self, bg=COLORS['bg_main'], pady=30, padx=40)
        header.pack(fill='x')
        tk.Label(header, text="Nastavení", font=("Segoe UI", 26, "bold"), bg=COLORS['bg_main'], fg="white").pack(side="left")

        # Hlavní kontejner
        scroll_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=40)
        scroll_frame.pack(fill='both', expand=True)

        content = tk.Frame(scroll_frame, bg=COLORS['bg_main'])
        content.pack(fill='x', anchor="n", pady=(0, 20))

        # ==========================================
        # 1. SEKCE: GEMINI API (Původní)
        # ==========================================
        self.create_header(content, "Gemini API")
        
        tk.Label(content, 
                 text="Pro fungování AI vyhledávání je potřeba Google Gemini API klíč.", 
                 font=("Segoe UI", 9), 
                 bg=COLORS['bg_main'], 
                 fg=COLORS['sub_text']
        ).pack(anchor="w", pady=(0, 10))
        
        api_container = tk.Frame(content, bg=COLORS['bg_main'], pady=5)
        api_container.pack(fill='x')

        api_row = tk.Frame(api_container, bg=COLORS['bg_main'])
        api_row.pack(fill='x')
        
        entry_bg = tk.Frame(api_row, bg=COLORS['input_bg'], padx=10, pady=8)
        entry_bg.pack(side="left", fill='x', expand=True, padx=(0, 10))
        
        self.api_entry = tk.Entry(entry_bg, font=("Consolas", 10), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.api_entry.pack(fill='x')
        self.api_entry.insert(0, self.current_key)

        save_btn = tk.Button(api_row, text="Uložit klíč", command=self.save_api_key,
                             bg=COLORS['accent'], fg="white", font=("Segoe UI", 10, "bold"),
                             relief="flat", padx=20, pady=8, cursor="hand2")
        save_btn.pack(side="right")
        self.hover_effect(save_btn, COLORS['accent'], COLORS['accent_hover'])

        sub_row = tk.Frame(api_container, bg=COLORS['bg_main'])
        sub_row.pack(fill='x', pady=(10, 0))

        link_lbl = tk.Label(sub_row, text="Získat klíč zdarma (Google AI Studio)", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text'], cursor="hand2")
        link_lbl.pack(side="left")
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))
        link_lbl.bind("<Enter>", lambda e: link_lbl.config(fg=COLORS['accent'], font=("Segoe UI", 9, "underline")))
        link_lbl.bind("<Leave>", lambda e: link_lbl.config(fg=COLORS['sub_text'], font=("Segoe UI", 9)))

        self.create_tool_btn(sub_row, "📊 Graf", lambda: webbrowser.open("https://aistudio.google.com/app/usage"))
        self.create_tool_btn(sub_row, "⚡ Ověřit", self.check_api_status)

        self.create_separator(content)


        # ==========================================
        # 2. SEKCE: PERSONALIZACE (Nové "CleanDropdown")
        # ==========================================
        self.create_header(content, "Personalizace")

        # Řádek: Motiv
        self.create_clean_setting_row(
            parent=content,
            title="Barevný motiv",
            desc="Přizpůsobte si vzhled aplikace.",
            current_val=self.current_theme,
            options=list(THEMES.keys()),
            callback=self.on_theme_change
        )

        # Řádek: Jazyk
        self.create_clean_setting_row(
            parent=content,
            title="Jazyk / Language",
            desc="Změňte jazyk uživatelského rozhraní.",
            current_val=self.current_lang,
            options=["Čeština", "English", "Deutsch", "Français", "Español"],
            callback=self.on_lang_change
        )

        self.create_separator(content)


        # ==========================================
        # 3. SEKCE: SYSTÉM (Původní)
        # ==========================================
        self.create_header(content, "Systém")

        update_row = tk.Frame(content, bg=COLORS['bg_main'], pady=10)
        update_row.pack(fill='x')

        tk.Label(update_row, text="Aktualizace aplikace", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(anchor="w")
        tk.Label(update_row, text="Zkontrolujte dostupnost nové verze.", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(anchor="w")

        up_btn = tk.Button(update_row, text="Zkontrolovat nyní", command=self.check_update,
                           bg=COLORS['input_bg'], fg=COLORS['fg'], font=("Segoe UI", 10),
                           relief="flat", padx=15, pady=6, cursor="hand2")
        up_btn.place(relx=1.0, rely=0.5, anchor="e") 
        self.hover_effect(up_btn, COLORS['input_bg'], COLORS['item_hover'])


        # --- STATUS BAR ---
        self.status_label = tk.Label(content, text="", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text'], pady=20)
        self.status_label.pack(anchor="w")


    # --- DESIGN HELPERY ---

    def create_header(self, parent, text):
        lbl = tk.Label(parent, text=text, font=("Segoe UI", 10, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text'])
        lbl.pack(anchor="w", pady=(15, 5))

    def create_separator(self, parent):
        tk.Frame(parent, bg=COLORS['border'], height=1).pack(fill='x', pady=20)

    def create_clean_setting_row(self, parent, title, desc, current_val, options, callback):
        """
        Vytvoří řádek, kde je vpravo 'čistý' dropdown (jen text + šipka).
        Místo Comboboxu používá Label + Menu.
        """
        row = tk.Frame(parent, bg=COLORS['bg_main'], pady=8)
        row.pack(fill='x')

        # Levá část (Popis)
        text_frame = tk.Frame(row, bg=COLORS['bg_main'])
        text_frame.pack(side="left", fill="both", expand=True)
        tk.Label(text_frame, text=title, font=("Segoe UI", 11), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(anchor="w")
        tk.Label(text_frame, text=desc, font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(anchor="w")

        # Pravá část (Clean Dropdown)
        # Vytvoříme 'falešné tlačítko' z Labelu, aby nemělo žádný border
        
        dropdown_frame = tk.Frame(row, bg=COLORS['bg_main'], cursor="hand2", padx=5, pady=5)
        dropdown_frame.pack(side="right")

        # Text hodnoty + šipka (Unicode)
        # Např: "Dark (Default) ⌄"
        display_text = f"{current_val}  ⌄"
        
        lbl_value = tk.Label(dropdown_frame, text=display_text, font=("Segoe UI", 10), 
                             bg=COLORS['bg_main'], fg=COLORS['fg'], cursor="hand2")
        lbl_value.pack()

        # Menu (vyskakovací seznam)
        menu = tk.Menu(dropdown_frame, tearoff=0, 
                       bg=COLORS['item_bg'], fg=COLORS['fg'], 
                       activebackground=COLORS['accent'], activeforeground='white',
                       bd=0, relief="flat", font=("Segoe UI", 10))

        # Funkce pro výběr
        def select_option(opt):
            lbl_value.config(text=f"{opt}  ⌄")
            callback(opt)

        # Naplnění menu
        for opt in options:
            menu.add_command(label=opt, command=lambda o=opt: select_option(o))

        # Zobrazení menu při kliknutí
        def show_menu(e):
            # Získáme souřadnice pro zobrazení menu pod labelem
            x = dropdown_frame.winfo_rootx()
            y = dropdown_frame.winfo_rooty() + dropdown_frame.winfo_height()
            menu.tk_popup(x, y)

        # Hover efekty
        def on_enter(e):
            dropdown_frame.config(bg=COLORS['item_hover'])
            lbl_value.config(bg=COLORS['item_hover'])
        
        def on_leave(e):
            dropdown_frame.config(bg=COLORS['bg_main'])
            lbl_value.config(bg=COLORS['bg_main'])

        # Binding
        for w in [dropdown_frame, lbl_value]:
            w.bind("<Button-1>", show_menu)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def create_tool_btn(self, parent, text, cmd):
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=COLORS['bg_main'], fg=COLORS['sub_text'], font=("Segoe UI", 9),
                        relief="flat", padx=10, pady=2, cursor="hand2", bd=0)
        btn.pack(side="right", padx=5)
        
        def on_enter(e): btn.config(fg=COLORS['fg'], bg=COLORS['item_hover'])
        def on_leave(e): btn.config(fg=COLORS['sub_text'], bg=COLORS['bg_main'])
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    def hover_effect(self, widget, bg_normal, bg_hover):
        def on_enter(e): widget.config(bg=bg_hover)
        def on_leave(e): widget.config(bg=bg_normal)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    # --- LOGIKA ---

    def on_theme_change(self, new_theme):
        self.settings["theme"] = new_theme
        SettingsManager.save_settings(self.settings)
        self.controller.update_theme(new_theme)

    def on_lang_change(self, new_lang):
        self.settings["language"] = new_lang
        SettingsManager.save_settings(self.settings)
        self.update_status(f"Jazyk změněn na: {new_lang}", COLORS['success'])

    def save_api_key(self):
        new_key = self.api_entry.get().strip()
        self.settings["api_key"] = new_key
        if SettingsManager.save_settings(self.settings):
            self.update_status("Klíč uložen.", COLORS['success'])
        else:
            self.update_status("Chyba ukládání.", COLORS['danger'])

    def check_api_status(self):
        key = self.api_entry.get().strip()
        if not key:
            self.update_status("⚠️ Chybí klíč", "orange")
            return
        self.update_status("Ověřuji...", COLORS['sub_text'])
        threading.Thread(target=self._test_connection_thread, args=(key,), daemon=True).start()

    def _test_connection_thread(self, key):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents="Hello",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
            if response:
                self.controller.after(0, lambda: self.update_status("✅ API Funkční", COLORS['success']))
        except Exception:
            self.controller.after(0, lambda: self.update_status("❌ Chyba API", COLORS['danger']))

    def update_status(self, text, color):
        self.status_label.config(text=text, fg=color)

    def check_update(self):
        updater = GitHubUpdater(self)
        threading.Thread(target=lambda: updater.check_for_updates(silent=False)).start()