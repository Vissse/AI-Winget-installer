# view_health.py
import tkinter as tk
import subprocess
import threading
from config import COLORS
from gui_components import ModernScrollbar

class HealthCheckPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=COLORS['bg_main'])
        self.controller = controller
        
        header = tk.Frame(self, bg=COLORS['bg_main'], pady=20, padx=20)
        header.pack(fill='x')
        tk.Label(header, text="Windows Health & Maintenance", font=("Segoe UI", 18, "bold"), bg=COLORS['bg_main'], fg="white").pack(side="left")

        content = tk.Frame(self, bg=COLORS['bg_main'], padx=20)
        content.pack(fill='both', expand=True)

        controls = tk.Frame(content, bg=COLORS['bg_sidebar'], padx=15, pady=15)
        controls.pack(side="left", fill="y", padx=(0, 20))
        
        tk.Label(controls, text="Opravy Systému", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['accent']).pack(anchor="w", pady=(0, 10))

        self.create_tool_row(controls, "🔍", "SFC Scan", 
                             "sfc /scannow", 
                             "Kontrola integrity souborů (SFC)...",
                             "System File Checker (SFC).\nSkenuje integritu všech chráněných systémových souborů\na nahrazuje poškozené verze kopií z mezipaměti.\nZákladní první krok při opravě systému.")

        self.create_tool_row(controls, "💾", "CHKDSK Scan (Disk)", 
                             "chkdsk C: /scan", 
                             "Online kontrola disku (CHKDSK)...",
                             "Check Disk (Scan Mode).\nZkontroluje logickou strukturu souborového systému (NTFS)\na hledá chyby na disku C:.\nBěží za chodu Windows bez nutnosti restartu.")

        self.create_tool_row(controls, "🩺", "DISM Check Health", 
                             "dism /online /cleanup-image /CheckHealth", 
                             "Rychlá kontrola obrazu (DISM)...",
                             "DISM (CheckHealth).\nPouze zkontroluje, zda byl obraz systému označen jako poškozený.\nNeprovádí žádné opravy, slouží jen k rychlé diagnostice.")

        self.create_tool_row(controls, "🛠️", "DISM Restore Health", 
                             "dism /online /cleanup-image /RestoreHealth", 
                             "Hloubková oprava obrazu (DISM)...",
                             "DISM (RestoreHealth).\nPokročilá oprava obrazu Windows.\nStáhne funkční soubory z Windows Update a opraví poškozené\nkomponenty, které SFC nedokázal vyřešit.")
        
        # Sekce Správa PC (NOVÉ - Místo sítě a wingetu)
        tk.Label(controls, text="Správa PC a Údržba", font=("Segoe UI", 11, "bold"), bg=COLORS['bg_sidebar'], fg=COLORS['accent']).pack(anchor="w", pady=(20, 10))
        
        self.create_tool_row(controls, "🗑️", "Smazat Temp soubory", 
                             'del /q/f/s %TEMP%\\*', 
                             "Mazání dočasných souborů uživatele...",
                             "Temp Cleaner.\nBezpečně vymaže obsah složky %TEMP%.\nOdstraní zbytečné soubory po instalacích a cache aplikací.\n(Soubory, které systém právě používá, budou přeskočeny).")

        self.create_tool_row(controls, "💿", "Vyčištění Disku (Windows)", 
                             "cleanmgr.exe", 
                             "Spouštění nástroje Vyčištění disku...",
                             "Windows Disk Cleanup.\nSpustí oficiální nástroj Windows pro uvolnění místa.\nUmožní smazat Koš, miniatury, logy a staré aktualizace.")

        self.create_tool_row(controls, "🔋", "Report Baterie (Laptop)", 
                             "powercfg /batteryreport /output \"C:\\battery_report.html\"", 
                             "Generování reportu baterie...",
                             "PowerCfg Battery Report.\nVygeneruje detailní HTML report o zdraví baterie notebooku.\nSoubor bude uložen přímo na disk C:\\battery_report.html\n(Obsahuje historii nabíjení a reálnou kapacitu).")
        
        self.create_tool_row(controls, "🧹", "WinSxS Cleanup (Deep)", 
                             "dism /online /cleanup-image /StartComponentCleanup", 
                             "Hloubkové čištění systémových záloh...",
                             "Component Cleanup.\nAnalyzuje složku WinSxS a odstraňuje staré verze\naktualizací Windows, které již nejsou potřeba.\nUvolní místo na disku, ale znemožní odinstalaci aktualizací.")

        log_frame = tk.Frame(content, bg=COLORS['bg_main'])
        log_frame.pack(side="right", fill="both", expand=True)

        tk.Label(log_frame, text="Průběh operace:", font=("Segoe UI", 10), bg=COLORS['bg_main'], fg=COLORS['sub_text']).pack(anchor="w", pady=(0, 5))

        self.console = tk.Text(log_frame, bg="#0d0d0d", fg="#cccccc", font=("Consolas", 10), relief="flat", padx=10, pady=10, state="disabled")
        self.console.pack(fill="both", expand=True)

        try:
            scrollbar = ModernScrollbar(log_frame, command=self.console.yview, bg=COLORS['bg_main'])
            scrollbar.pack(side="right", fill="y", before=self.console)
            self.console.config(yscrollcommand=scrollbar.set)
        except: pass

    def create_tool_row(self, parent, icon, title, command, log_desc, tooltip_text):
        row = tk.Frame(parent, bg=COLORS['bg_sidebar'])
        row.pack(fill='x', pady=2)
        btn_frame = tk.Frame(row, bg=COLORS['input_bg'], cursor="hand2", height=35)
        btn_frame.pack(side="left", fill="y")
        btn_frame.pack_propagate(False) 
        btn_frame.configure(width=280)  
        lbl_icon = tk.Label(btn_frame, text=icon, font=("Segoe UI Emoji", 11), bg=COLORS['input_bg'], fg="white", width=4, cursor="hand2")
        lbl_icon.pack(side="left", fill="y")
        lbl_text = tk.Label(btn_frame, text=title, font=("Segoe UI", 10), bg=COLORS['input_bg'], fg="white", anchor="w", cursor="hand2")
        lbl_text.pack(side="left", fill="both", expand=True)
        def on_click(e): self.run_command(command, log_desc)
        btn_frame.bind("<Button-1>", on_click)
        lbl_icon.bind("<Button-1>", on_click)
        lbl_text.bind("<Button-1>", on_click)
        widgets_to_color = [btn_frame, lbl_icon, lbl_text]
        def on_btn_enter(e): 
            for w in widgets_to_color: w.config(bg=COLORS['item_hover'])
        def on_btn_leave(e): 
            for w in widgets_to_color: w.config(bg=COLORS['input_bg'])
        for w in widgets_to_color:
            w.bind("<Enter>", on_btn_enter)
            w.bind("<Leave>", on_btn_leave)

        base_font = ("Segoe UI Emoji", 12)
        info_lbl = tk.Label(row, text="🔍", font=base_font, bg=COLORS['bg_sidebar'], fg=COLORS['sub_text'], cursor="hand2")
        info_lbl.pack(side="left", padx=(8, 0)) 
        
        info_lbl.tooltip_win = None
        info_lbl.timer_id = None

        def show_tooltip():
            if info_lbl.tooltip_win: return
            x, y, cx, cy = info_lbl.bbox("insert")
            x += info_lbl.winfo_rootx() + 30
            y += info_lbl.winfo_rooty() + 10
            tw = tk.Toplevel(info_lbl)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tw, text=tooltip_text, justify='left', background="#2d2d2d", foreground="#ffffff", relief='solid', borderwidth=1, font=("Segoe UI", 9), padx=8, pady=5)
            label.pack()
            info_lbl.tooltip_win = tw

        def on_info_enter(e):
            info_lbl.config(fg=COLORS['accent'])
            info_lbl.timer_id = info_lbl.after(400, show_tooltip)

        def on_info_leave(e):
            info_lbl.config(fg=COLORS['sub_text'])
            if info_lbl.timer_id:
                info_lbl.after_cancel(info_lbl.timer_id)
                info_lbl.timer_id = None
            if info_lbl.tooltip_win:
                info_lbl.tooltip_win.destroy()
                info_lbl.tooltip_win = None
            
        info_lbl.bind("<Enter>", on_info_enter)
        info_lbl.bind("<Leave>", on_info_leave)
        return row

    def log(self, text):
        self.console.config(state="normal")
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)
        self.console.config(state="disabled")

    def run_command(self, cmd, description):
        self.console.config(state="normal")
        self.console.delete(1.0, tk.END)
        self.console.config(state="disabled")
        self.log(f"--- ZAHAJUJI: {description} ---")
        self.log(f"Příkaz: {cmd}")
        self.log("(Operace běží na pozadí, prosím čekejte...)\n")
        threading.Thread(target=self._execute_thread, args=(cmd,), daemon=True).start()

    def _execute_thread(self, cmd):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 1. Změna: Odstraníme 'chcp 65001' a 'text=True'.
            # Budeme číst surová data (bytes) a dekódovat je ručně.
            # To často vyřeší problém, kdy Python čeká na naplnění bufferu.
            
            if cmd.startswith("del"): 
                full_cmd = f"cmd /c {cmd}"
            else: 
                # Spustíme příkaz přímo, bez 'chcp'. Spoléháme na systémové kódování (cp852).
                full_cmd = cmd 

            process = subprocess.Popen(
                full_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                shell=True, 
                # bufsize=0 je klíčové pro vypnutí bufferování (jen pro binární režim)
                bufsize=0,  
                startupinfo=startupinfo
            )
            
            # Čteme výstup znak po znaku nebo řádek po řádku
            # Pro SFC/DISM je lepší číst řádky, i když progress bar (%) se ukáže až po dokončení řádku.
            # Ale úvodní texty by se měly objevit hned.
            
            while True:
                # Přečteme řádek v bytech
                line_bytes = process.stdout.readline()
                
                if not line_bytes and process.poll() is not None:
                    break
                
                if line_bytes:
                    # Ruční dekódování (cp852 pro česká Windows, jinak cp1250 nebo utf-8)
                    try:
                        # Zkusíme cp852 (DOS Latin 2 - standard pro CMD v CZ)
                        decoded_line = line_bytes.decode('cp852', errors='replace').strip()
                    except:
                        # Fallback
                        decoded_line = line_bytes.decode('utf-8', errors='replace').strip()
                    
                    if decoded_line:
                        self.controller.after(0, lambda l=decoded_line: self.log(l))
            
            rc = process.poll()
            if rc == 0:
                self.controller.after(0, lambda: self.log("\n✅ HOTOVO: Operace dokončena úspěšně."))
            else:
                self.controller.after(0, lambda: self.log(f"\n❌ CHYBA (Kód {rc}).\nUjistěte se, že je aplikace spuštěna jako SPRÁVCE."))
                
        except Exception as e:
            self.controller.after(0, lambda: self.log(f"Kritická chyba: {e}"))