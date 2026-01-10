# view_installer.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import re
import subprocess
from google import genai 
from PIL import Image, ImageTk

from config import COLORS, OUTPUT_FILE
from gui_components import ToolTip, ModernScrollbar, IconLoader
from settings_manager import SettingsManager
from install_manager import InstallationDialog

class InstallerPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        try: self.default_icon = ImageTk.PhotoImage(Image.new('RGB', (32, 32), color=COLORS['item_bg']))
        except: pass
        self.queue_data = {} 
        self.is_searching = False
        self.columnconfigure(0, weight=1, uniform="group1") 
        self.columnconfigure(1, weight=1, uniform="group1") 
        self.rowconfigure(0, weight=0) 
        self.rowconfigure(1, weight=0) 
        self.rowconfigure(2, weight=1) 
        header_frame = tk.Frame(self, bg=COLORS['bg_main'], pady=15)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(header_frame, text="Installer", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg']).pack(side="left", padx=20)
        left_controls = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        left_controls.grid(row=1, column=0, sticky="nsew")
        tk.Label(left_controls, text="Zadejte název programu", font=("Segoe UI", 14, "bold"), bg=COLORS['bg_main'], fg=COLORS['fg'], anchor="w").pack(fill='x')
        tk.Label(left_controls, text="(Nebo popište, co hledáte, např. 'úprava zvuku')", font=("Segoe UI", 9), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(0, 10))
        search_frame = tk.Frame(left_controls, bg=COLORS['bg_main'])
        search_frame.pack(fill='x', pady=(0, 10))
        search_border = tk.Frame(search_frame, bg=COLORS['input_bg'], bd=0, highlightthickness=0) 
        search_border.pack(fill='x', ipady=2)
        self.input_entry = tk.Entry(search_border, font=("Segoe UI", 12), bg=COLORS['input_bg'], fg="white", insertbackground="white", relief="flat")
        self.input_entry.pack(side='left', fill='both', expand=True, padx=10)
        self.input_entry.bind('<Return>', lambda event: self.start_search())
        self.search_btn = self.create_animated_btn(search_border, "Hledat", self.start_search, COLORS['accent'], COLORS['accent_hover'])
        self.search_btn.pack(side='right', fill='y', padx=2, pady=2)
        style = ttk.Style()
        style.theme_use('default')
        style.configure("Horizontal.TProgressbar", background=COLORS['accent'], troughcolor=COLORS['bg_main'], borderwidth=0, thickness=2)
        self.progress = ttk.Progressbar(search_frame, orient="horizontal", mode="indeterminate", style="Horizontal.TProgressbar")
        tk.Label(left_controls, text="Výsledky hledání:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text'], anchor="w").pack(fill='x', pady=(10, 5), side="bottom")
        right_controls = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        right_controls.grid(row=1, column=1, sticky="sew") 
        queue_header_row = tk.Frame(right_controls, bg=COLORS['bg_main'])
        queue_header_row.pack(fill='x', pady=(10, 5), side="bottom")
        tk.Label(queue_header_row, text="Instalační fronta:", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(side="left")
        actions_frame = tk.Frame(queue_header_row, bg=COLORS['bg_main'])
        actions_frame.pack(side="right")
        self.create_header_btn(actions_frame, "📂", self.import_queue, "Importovat seznam", COLORS['input_bg'], COLORS['item_hover'])
        self.create_header_btn(actions_frame, "🗑️", self.clear_queue, "Vymazat frontu", COLORS['danger'], COLORS['danger_hover'])
        self.create_header_btn(actions_frame, "💾", self.save_only, "Uložit .bat soubor", COLORS['input_bg'], COLORS['item_hover'])
        self.create_header_btn(actions_frame, "🚀", self.install_now, "Instalovat vše", COLORS['success'], COLORS['success_hover'])
        left_list_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        left_list_frame.grid(row=2, column=0, sticky="nsew")
        self.found_container = tk.Frame(left_list_frame, bg=COLORS['bg_sidebar'])
        self.found_container.pack(fill='both', expand=True, pady=(0, 20))
        self.found_canvas = tk.Canvas(self.found_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.found_scrollbar = ModernScrollbar(self.found_container, command=self.found_canvas.yview, bg=COLORS['bg_sidebar'])
        self.found_scrollable = tk.Frame(self.found_canvas, bg=COLORS['bg_sidebar'])
        self.found_scrollable.bind("<Configure>", self.on_frame_configure)
        self.found_canvas.create_window((0, 0), window=self.found_scrollable, anchor="nw", width=480)
        self.found_canvas.configure(yscrollcommand=self.found_scrollbar.set)
        self.found_canvas.bind("<Configure>", lambda e: self.found_canvas.itemconfig(self.found_canvas.find_all()[0], width=e.width))
        self.found_canvas.pack(side="left", fill="both", expand=True)
        self.found_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.found_container, self.found_canvas)
        right_list_frame = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        right_list_frame.grid(row=2, column=1, sticky="nsew")
        self.queue_container = tk.Frame(right_list_frame, bg=COLORS['bg_sidebar'])
        self.queue_container.pack(fill='both', expand=True, pady=(0, 20))
        self.queue_canvas = tk.Canvas(self.queue_container, bg=COLORS['bg_sidebar'], highlightthickness=0)
        self.queue_scrollbar = ModernScrollbar(self.queue_container, command=self.queue_canvas.yview, bg=COLORS['bg_sidebar'])
        self.queue_scrollable = tk.Frame(self.queue_canvas, bg=COLORS['bg_sidebar'])
        self.queue_scrollable.bind("<Configure>", lambda e: self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all")))
        self.queue_canvas.create_window((0, 0), window=self.queue_scrollable, anchor="nw", width=480)
        self.queue_canvas.configure(yscrollcommand=self.queue_scrollbar.set)
        self.queue_canvas.bind("<Configure>", lambda e: self.queue_canvas.itemconfig(self.queue_canvas.find_all()[0], width=e.width))
        self.queue_canvas.pack(side="left", fill="both", expand=True)
        self.queue_scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(self.queue_container, self.queue_canvas)

    def on_frame_configure(self, event):
        self.found_canvas.configure(scrollregion=self.found_canvas.bbox("all"))

    def create_animated_btn(self, parent, text, command, bg_color, hover_color):
        btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", font=("Segoe UI", 10, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", borderwidth=0)
        def on_enter(e):
            if btn['state'] != 'disabled': btn.config(bg=hover_color)
        def on_leave(e):
            if btn['state'] != 'disabled': btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def create_header_btn(self, parent, text, command, tooltip_text, bg_color, hover_color):
        btn = tk.Button(parent, text=text, command=command, bg=bg_color, fg="white", font=("Segoe UI Emoji", 12), relief="flat", width=3, cursor="hand2", borderwidth=0)
        btn.pack(side="left", padx=2)
        def on_enter(e):
            if btn['state'] != 'disabled': btn.config(bg=hover_color)
        def on_leave(e):
            if btn['state'] != 'disabled': btn.config(bg=bg_color)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        ToolTip(btn, tooltip_text)
        return btn

    def import_queue(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("Batch files", "*.bat"), ("All files", "*.*")])
        if file_path:
             messagebox.showinfo("Import", f"Vybrán soubor: {file_path}\n(Funkce importu zatím není plně implementována)")

    def _bind_mousewheel(self, widget, canvas):
        def _on_mousewheel(event):
            if canvas.bbox("all"):
                scroll_height = canvas.bbox("all")[3]
                visible_height = canvas.winfo_height()
                if scroll_height <= visible_height: return 
            if event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
            self.found_scrollbar.redraw()
            self.queue_scrollbar.redraw()
        bind_enter = lambda e: {canvas.bind_all("<MouseWheel>", _on_mousewheel), canvas.bind_all("<Button-4>", _on_mousewheel), canvas.bind_all("<Button-5>", _on_mousewheel)}
        bind_leave = lambda e: {canvas.unbind_all("<MouseWheel>"), canvas.unbind_all("<Button-4>"), canvas.unbind_all("<Button-5>")}
        widget.bind('<Enter>', bind_enter)
        widget.bind('<Leave>', bind_leave)

    def start_search(self):
        user_request = self.input_entry.get()
        if not user_request:
            messagebox.showwarning("Chyba", "Napiš název programu.")
            return
        if self.is_searching: return 
        self.is_searching = True
        self.search_btn.config(cursor="arrow") 
        self.input_entry.delete(0, 'end') 
        self.progress.pack(fill='x', pady=(5, 0))
        self.progress.start(10) 
        threading.Thread(target=self.get_winget_ids_thread, args=(user_request,)).start()

    def get_winget_ids_thread(self, user_request):
        settings = SettingsManager.load_settings()
        api_key = settings.get("api_key", "")
        print(f"--- FÁZE 1: Zjišťování záměru pro: '{user_request}' ---")
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Chyba init AI: {e}")
            self.controller.after(0, self.stop_loading_animation)
            return

        intent_prompt = f"""
        Jsi expert na Windows software a Winget repozitář.
        Uživatel zadal: "{user_request}"
        Pokud hledá konkrétní app, vrať jen opravený název.
        Pokud hledá kategorii, vrať seznam nejlepších aplikací.
        Odpověz POUZE ve formátu: QUERIES: app1;app2;app3
        """
        search_terms = []
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=intent_prompt)
            raw_intent = response.text.strip()
            if "QUERIES:" in raw_intent:
                clean_line = raw_intent.replace("QUERIES:", "").strip()
                search_terms = [t.strip() for t in clean_line.split(";") if t.strip()]
            else:
                search_terms = [user_request]
            print(f"AI navrhlo: {search_terms}")
        except Exception as e:
            print(f"Chyba AI intent: {e}")
            search_terms = [user_request]

        combined_output = ""
        self.progress['maximum'] = len(search_terms) * 100
        current_prog = 0
        
        for term in search_terms:
            try:
                cmd = f'winget search "{term}" --source winget --accept-source-agreements -n 3'
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, encoding='cp852', errors='replace')
                combined_output += f"\n--- VÝSLEDKY PRO '{term}' ---\n" + result.stdout
            except: pass
            current_prog += 100

        filter_prompt = f"""
        Mám výstup z příkazové řádky (Winget Search) pro různé hledané výrazy.
        Původní dotaz uživatele byl: "{user_request}"
        SUROVÁ DATA Z WINGET:
        '''{combined_output}'''
        INSTRUKCE:
        1. Analyzuj surová data a najdi aplikace, které odpovídají záměru uživatele.
        2. Pokud data obsahují balast, ignoruj je. Hledáme hlavní aplikace.
        3. Extrahuj Název, ID a Verzi.
        4. Pokud ID nevidíš v datech, ale jsi si jistý, že to je ta správná aplikace, pokus se ID odhadnout.
        VÝSTUPNÍ FORMÁT (čistý JSON pole):
        [ {{ "name": "Název aplikace", "id": "Přesné.ID", "version": "verze (nebo 'Latest')", "website": "domena.com" }} ]
        """
        try:
            response = client.models.generate_content(model="gemini-2.5-flash", contents=filter_prompt)
            raw_text = response.text
            json_str = raw_text.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', json_str, re.DOTALL)
            data = json.loads(match.group(0)) if match else []

            for item in data:
                if not item.get('version') or item['version'] == "Latest": item['version'] = "Latest/Unknown"

            self.controller.after(0, self.display_search_results, data)

        except Exception as e:
            print(f"Chyba parsování: {e}")
            self.controller.after(0, self.stop_loading_animation)

    def stop_loading_animation(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.is_searching = False
        self.search_btn.config(cursor="hand2")

    def display_search_results(self, items):
        self.stop_loading_animation()
        for widget in self.found_scrollable.winfo_children(): widget.destroy()
        if not items:
            tk.Label(self.found_scrollable, text="Nic nenalezeno.", bg=COLORS['bg_sidebar'], fg="gray").pack(pady=20)
            return
        for item in items: self.create_list_item(self.found_scrollable, item, is_result_mode=True)
        self.found_canvas.update_idletasks()
        self.found_scrollbar.redraw()

    def create_list_item(self, parent_scrollable, item_data, is_result_mode):
        name = item_data.get("name")
        app_id = item_data.get("id")
        version = item_data.get("version")
        card = tk.Frame(parent_scrollable, bg=COLORS['item_bg'], pady=10, padx=10)
        card.pack(fill='x', padx=(10,0), pady=5)
        icon_label = tk.Label(card, image=self.default_icon, bg=COLORS['item_bg'])
        icon_label.pack(side="left", padx=(0, 15))
        IconLoader.load_async(item_data, icon_label, self.controller)
        text_frame = tk.Frame(card, bg=COLORS['item_bg'])
        text_frame.pack(side="left", fill="both", expand=True)
        tk.Label(text_frame, text=name, font=("Segoe UI", 11, "bold"), bg=COLORS['item_bg'], fg="white", anchor="w").pack(fill="x")
        tk.Label(text_frame, text=f"ID: {app_id} | v{version}", font=("Segoe UI", 9), bg=COLORS['item_bg'], fg=COLORS['sub_text'], anchor="w").pack(fill="x")
        action_symbol = tk.Label(card, font=("Arial", 18), bg=COLORS['item_bg'], cursor="hand2", padx=10)
        action_symbol.pack(side="right")
        if is_result_mode:
            action_symbol.config(text="＋", fg=COLORS['accent'])
            action_symbol.bind("<Button-1>", lambda e, i=item_data: self.add_item_to_queue(i))
            self._bind_symbol_hover(action_symbol, COLORS['accent'], COLORS['fg'])
        else:
            action_symbol.config(text="✕", fg=COLORS['danger'])
            action_symbol.bind("<Button-1>", lambda e, aid=app_id: self.remove_from_queue(aid))
            self._bind_symbol_hover(action_symbol, COLORS['danger'], COLORS['fg'])
        self._bind_card_hover(card, text_frame, icon_label, action_symbol)

    def _bind_symbol_hover(self, widget, hover_bg, hover_fg):
        normal_bg = COLORS['item_bg']
        normal_fg = widget.cget("fg")
        def on_enter(e): widget.config(bg=hover_bg, fg=hover_fg)
        def on_leave(e): widget.config(bg=normal_bg, fg=normal_fg)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _bind_card_hover(self, card, text_frame, icon_label, action_symbol):
        widgets_to_change = [card, text_frame, icon_label] + text_frame.winfo_children()
        def on_enter(e):
            for w in widgets_to_change: w.config(bg=COLORS['item_hover'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_hover'])
        def on_leave(e):
            for w in widgets_to_change: w.config(bg=COLORS['item_bg'])
            if e.widget != action_symbol: action_symbol.config(bg=COLORS['item_bg'])
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def add_item_to_queue(self, item_data):
        app_id = item_data.get("id")
        if app_id in self.queue_data: return
        self.queue_data[app_id] = item_data
        self.create_list_item(self.queue_scrollable, item_data, is_result_mode=False)
        self.queue_canvas.update_idletasks()
        self.queue_canvas.yview_moveto(1.0)
        self.queue_scrollbar.redraw()

    def remove_from_queue(self, app_id):
        if app_id in self.queue_data:
            del self.queue_data[app_id]
            self.refresh_queue_view()

    def refresh_queue_view(self):
        for widget in self.queue_scrollable.winfo_children(): widget.destroy()
        for app_id, item_data in self.queue_data.items():
            self.create_list_item(self.queue_scrollable, item_data, is_result_mode=False)
        self.queue_canvas.update_idletasks()
        self.queue_scrollbar.redraw()

    def clear_queue(self):
        self.queue_data = {}
        self.refresh_queue_view()

    def _create_batch_file(self):
        if not self.queue_data:
            messagebox.showwarning("Pozor", "Seznam je prázdný.")
            return False
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f: 
                f.write("@echo off\nchcp 65001 > nul\necho Zahajuji instalaci...\n\n")
                for aid, data in self.queue_data.items():
                    f.write(f"echo Instaluji: {data['name']}...\n")
                    f.write(f"winget install -e --id {aid} --silent --accept-package-agreements --accept-source-agreements\n")
                    f.write("echo ----------------------------------------\n")
                f.write("\necho Hotovo!\n")
            return True
        except Exception as e:
            messagebox.showerror("Chyba", str(e))
            return False

    def save_only(self):
        if self._create_batch_file(): 
            messagebox.showinfo("Uloženo", f"Soubor: {OUTPUT_FILE}")

    def install_now(self):
        if not self.queue_data:
            messagebox.showwarning("Pozor", "Seznam je prázdný.")
            return
        InstallationDialog(self.controller, list(self.queue_data.values()))