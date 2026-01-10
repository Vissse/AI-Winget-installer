# view_settings.py
import tkinter as tk
from tkinter import messagebox
import webbrowser
import threading
from google import genai 
from google.genai import types

from config import COLORS
from settings_manager import SettingsManager
from updater import GitHubUpdater

class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        self.settings = SettingsManager.load_settings()
        current_key = self.settings.get("api_key", "")

        header = tk.Frame(self, bg=COLORS['bg_main'], pady=20, padx=20)
        header.pack(fill='x')
        tk.Label(header, text="Uživatelské nastavení", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack(side="left")

        content = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        content.pack(fill='both', expand=True)

        api_frame = tk.Frame(content, bg=COLORS['bg_sidebar'], padx=20, pady=20)
        api_frame.pack(fill='x', pady=(0, 20))

        tk.Label(api_frame, text="Gemini API Klíč", font=("Segoe UI", 12, "bold"), bg=COLORS['bg_sidebar'], fg="white").pack(anchor="w")
        tk.Label(api_frame, text="Pro fungování AI vyhledávání je potřeba Google Gemini API klíč.", font=("Segoe UI", 9), bg=COLORS['bg_sidebar'], fg=COLORS['sub_text']).pack(anchor="w", pady=(0, 10))

        entry_bg = tk.Frame(api_frame, bg=COLORS['input_bg'], padx=10, pady=5)
        entry_bg.pack(fill='x')
        self.api_entry = tk.Entry(entry_bg, font=("Consolas", 11), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.api_entry.pack(fill='x')
        self.api_entry.insert(0, current_key)

        link_lbl = tk.Label(api_frame, text="🔗 Získat API klíč zdarma (Google AI Studio)", font=("Segoe UI", 9, "underline"), bg=COLORS['bg_sidebar'], fg=COLORS['accent'], cursor="hand2")
        link_lbl.pack(anchor="w", pady=(10, 5))
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://aistudio.google.com/app/apikey"))

        btn_frame = tk.Frame(api_frame, bg=COLORS['bg_sidebar'])
        btn_frame.pack(fill='x', pady=(20, 0))

        save_btn = tk.Button(btn_frame, text="💾 Uložit klíč", command=self.save_key, bg=COLORS['accent'], fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=20, pady=8, cursor="hand2")
        save_btn.pack(side="left")
        def on_save_enter(e): save_btn.config(bg=COLORS['accent_hover'])
        def on_save_leave(e): save_btn.config(bg=COLORS['accent'])
        save_btn.bind("<Enter>", on_save_enter)
        save_btn.bind("<Leave>", on_save_leave)

        check_btn = tk.Button(btn_frame, text="⚡ Ověřit správnost API", command=self.check_api_status, bg=COLORS['input_bg'], fg="white", font=("Segoe UI", 10), relief="flat", padx=20, pady=8, cursor="hand2")
        check_btn.pack(side="left", padx=10)
        def on_check_enter(e): check_btn.config(bg=COLORS['item_hover'])
        def on_check_leave(e): check_btn.config(bg=COLORS['input_bg'])
        check_btn.bind("<Enter>", on_check_enter)
        check_btn.bind("<Leave>", on_check_leave)

        update_btn = tk.Button(btn_frame, text="🔄 Zkontrolovat update", command=self.check_update, bg=COLORS['input_bg'], fg="white", font=("Segoe UI", 10), relief="flat", padx=20, pady=8, cursor="hand2")
        update_btn.pack(side="left", padx=10)
        def on_update_enter(e): update_btn.config(bg=COLORS['item_hover'])
        def on_update_leave(e): update_btn.config(bg=COLORS['input_bg'])
        update_btn.bind("<Enter>", on_update_enter)
        update_btn.bind("<Leave>", on_update_leave)
  
        quota_btn = tk.Button(btn_frame, text="📊 Graf spotřeby", command=lambda: webbrowser.open("https://aistudio.google.com/app/usage?timeRange=last-90-days"), bg=COLORS['input_bg'], fg="white", font=("Segoe UI", 10), relief="flat", padx=20, pady=8, cursor="hand2")
        quota_btn.pack(side="left", padx=10)
        def on_quota_enter(e): quota_btn.config(bg=COLORS['item_hover'])
        def on_quota_leave(e): quota_btn.config(bg=COLORS['input_bg'])
        quota_btn.bind("<Enter>", on_quota_enter)
        quota_btn.bind("<Leave>", on_quota_leave)

        self.status_frame = tk.Frame(content, bg=COLORS['bg_main'], pady=20)
        self.status_frame.pack(fill='x')
        self.status_label = tk.Label(self.status_frame, text="", font=("Segoe UI", 10), bg=COLORS['bg_main'])
        self.status_label.pack(anchor="w")

    def save_key(self):
        new_key = self.api_entry.get().strip()
        self.settings["api_key"] = new_key
        if SettingsManager.save_settings(self.settings):
            messagebox.showinfo("Úspěch", "API klíč byl uložen.")
        else:
            messagebox.showerror("Chyba", "Nepodařilo se uložit nastavení.")

    def check_api_status(self):
        key = self.api_entry.get().strip()
        if not key:
            self.update_status("⚠️ Chybí API klíč.", "orange")
            return
        self.update_status("⏳ Ověřuji spojení s Google AI...", COLORS['sub_text'])
        threading.Thread(target=self._test_connection_thread, args=(key,), daemon=True).start()

    def _test_connection_thread(self, key):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Hello",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
            if response and response.text:
                self.controller.after(0, lambda: self.update_status("✅ Klíč je AKTIVNÍ (GenAI SDK).", COLORS['success']))
            else:
                self.controller.after(0, lambda: self.update_status("❌ Žádná odpověď.", COLORS['danger']))
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg: msg, color = "⚠️ Limit vyčerpán (429).", "orange"
            elif "400" in error_msg: msg, color = "❌ Neplatný API klíč.", COLORS['danger']
            else: msg, color = f"❌ Chyba: {error_msg[:30]}...", COLORS['danger']
            self.controller.after(0, lambda: self.update_status(msg, color))

    def update_status(self, text, color):
        self.status_label.config(text=text, fg=color)

    def check_update(self):
        updater = GitHubUpdater(self)
        threading.Thread(target=lambda: updater.check_for_updates(silent=False)).start()