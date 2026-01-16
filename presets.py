# presets.py

# ==============================================================================
# 1. DEFINICE JEDNOTLIVÝCH APLIKACÍ (ATOMICKÁ DATA)
# ==============================================================================

# --- Herní Launchery ---
steam_app = {"name": "Steam", "id": "Valve.Steam", "website": "https://store.steampowered.com"}
epic_app = {"name": "Epic Games Launcher", "id": "EpicGames.EpicGamesLauncher", "website": "https://store.epicgames.com"}
ubisoft_app = {"name": "Ubisoft Connect", "id": "Ubisoft.Connect", "website": "https://ubisoftconnect.com"}
ea_app = {"name": "EA App", "id": "ElectronicArts.EADesktop", "website": "https://www.ea.com/ea-app"}
gog_app = {"name": "GOG GALAXY", "id": "GOG.Galaxy", "website": "https://www.gog.com/galaxy"}
playnite_app = {"name": "Playnite", "id": "Playnite.Playnite", "website": "https://playnite.link"}
battlenet_app = {"name": "Battle.net", "id": "Blizzard.BattleNet", "website": "https://www.blizzard.com"}
curseforge_app = {"name": "CurseForge", "id": "Overwolf.CurseForge", "website": "https://www.curseforge.com"}
riot_app = {"name": "Riot Client (via LoL)", "id": "RiotGames.LeagueOfLegends.EUNE", "website": "https://www.riotgames.com"} 
wargaming_app = {"name": "Wargaming.net Game Center", "id": "Wargaming.GameCenter", "website": "https://wargaming.net"}

# --- Prohlížeče ---
chrome_app = {"name": "Google Chrome", "id": "Google.Chrome", "website": "https://www.google.com/chrome"}
firefox_app = {"name": "Mozilla Firefox", "id": "Mozilla.Firefox", "website": "https://www.mozilla.org/firefox"}
edge_app = {"name": "Microsoft Edge", "id": "Microsoft.Edge", "website": "https://www.microsoft.com/edge"}
brave_app = {"name": "Brave Browser", "id": "Brave.Brave", "website": "https://brave.com"}
opera_app = {"name": "Opera", "id": "Opera.Opera", "website": "https://www.opera.com"}
vivaldi_app = {"name": "Vivaldi", "id": "Vivaldi.Vivaldi", "website": "https://vivaldi.com"}
zen_app = {"name": "Zen Browser", "id": "Zen-Team.Zen-Browser", "website": "https://www.zen-browser.app"}

# --- Komunikace ---
discord_app = {"name": "Discord", "id": "Discord.Discord", "website": "https://discord.com"}
telegram_app = {"name": "Telegram Desktop", "id": "Telegram.TelegramDesktop", "website": "https://desktop.telegram.org"}
signal_app = {"name": "Signal", "id": "OpenWhisperSystems.Signal", "website": "https://signal.org"}
teams_app = {"name": "Teams", "id": "Microsoft.Teams", "website": "https://www.microsoft.com/microsoft-teams"}
skype_app = {"name": "Skype", "id": "Zoom.ZoomSkypeForBusinessPlugin", "website": "https://www.skype.com"}

# --- Grafika ---
gimp_app = {"name": "GIMP", "id": "GIMP.GIMP.3", "website": "https://www.gimp.org"}
photoshop_alt_app = {"name": "Paint.NET", "id": "dotPDN.PaintDotNet", "website": "https://www.getpaint.net"}
inkscape_app = {"name": "Inkscape", "id": "Inkscape.Inkscape", "website": "https://inkscape.org"}
krita_app = {"name": "Krita", "id": "KDE.Krita", "website": "https://krita.org"}
blender_app = {"name": "Blender", "id": "BlenderFoundation.Blender", "website": "https://www.blender.org"}
irfan_app = {"name": "IrfanView", "id": "IrfanSkiljan.IrfanView", "website": "https://www.irfanview.com"}

# --- Video Přehrávače (Nová sekce) ---
vlc_app = {"name": "VLC media player", "id": "VideoLAN.VLC", "website": "https://www.videolan.org/vlc"}
mpc_app = {"name": "MPC-BE", "id": "MPC-BE.MPC-BE", "website": "https://sourceforge.net/projects/mpcbe/"}
potplayer_app = {"name": "Daum PotPlayer", "id": "Daum.PotPlayer", "website": "https://potplayer.daum.net"}
kodi_app = {"name": "Kodi", "id": "XBMCFoundation.Kodi", "website": "https://kodi.tv"}

# --- Nástroje ---
winrar_app = {"name": "WinRAR", "id": "RARLab.WinRAR", "website": "https://www.win-rar.com"}
python_app = {"name": "Python 3", "id": "Python.Python.3.12", "website": "https://www.python.org"}


# ==============================================================================
# 2. DEFINICE SKUPIN (SOUHRNNÉ LISTY)
# ==============================================================================

_BROWSERS = [chrome_app, firefox_app, edge_app, brave_app, opera_app, vivaldi_app, zen_app]
_CHAT = [discord_app, telegram_app, signal_app, teams_app, skype_app]
_GAMES = [steam_app, epic_app, ubisoft_app, ea_app, gog_app, battlenet_app, riot_app, wargaming_app, playnite_app, curseforge_app]
_GRAPHICS = [gimp_app, photoshop_alt_app, inkscape_app, krita_app, blender_app, irfan_app]

# Nová skupina pro video
_VIDEO = [vlc_app, mpc_app, potplayer_app, kodi_app]

_PDF = [
    {"name": "Adobe Acrobat Reader DC", "id": "Adobe.Acrobat.Reader.64-bit", "website": "https://get.adobe.com/reader"},
    {"name": "Sumatra PDF", "id": "SumatraPDF.SumatraPDF", "website": "https://www.sumatrapdfreader.org"},
    {"name": "Foxit PDF Reader", "id": "Foxit.FoxitReader", "website": "https://www.foxit.com"}
]

_OFFICE = [
    {"name": "LibreOffice", "id": "TheDocumentFoundation.LibreOffice", "website": "https://www.libreoffice.org"},
    {"name": "Microsoft 365 (Office)", "id": "Microsoft.Office", "website": "https://www.office.com"},
    {"name": "OnlyOffice", "id": "ONLYOFFICE.DesktopEditors", "website": "https://www.onlyoffice.com"}
]

_TOOLS = [
    {"name": "7-Zip", "id": "7zip.7zip", "website": "https://www.7-zip.org"},
    winrar_app,
    {"name": "Notepad++", "id": "Notepad++.Notepad++", "website": "https://notepad-plus-plus.org"},
    {"name": "AnyDesk", "id": "AnyDesk.AnyDesk", "website": "https://anydesk.com"},
    {"name": "OBS Studio", "id": "OBSProject.OBSStudio", "website": "https://obsproject.com"},
    {"name": "PowerToys", "id": "Microsoft.PowerToys", "website": "https://learn.microsoft.com/en-us/windows/powertoys/"}
]

_DEV = [
    {"name": "Visual Studio Code", "id": "Microsoft.VisualStudioCode", "website": "https://code.visualstudio.com"},
    {"name": "Git", "id": "Git.Git", "website": "https://git-scm.com"},
    python_app,
    {"name": "Node.js LTS", "id": "OpenJS.NodeJS.LTS", "website": "https://nodejs.org"}
]


# ==============================================================================
# 3. MAPOVÁNÍ KLÍČOVÝCH SLOV (PRESETS)
# ==============================================================================

PRESETS = {
    # === SEKTOR: HRY (GAMING) ===
    "hry": _GAMES,
    "hra": _GAMES,
    "games": _GAMES,
    "gaming": _GAMES,
    "launchers": _GAMES,
    # Konkrétní
    "steam": [steam_app],
    "epic": [epic_app],
    "ubisoft": [ubisoft_app],
    "uplay": [ubisoft_app],
    "ea": [ea_app],
    "origin": [ea_app],
    "gog": [gog_app],
    "battlenet": [battlenet_app],
    "blizzard": [battlenet_app],
    "riot": [riot_app],
    "lol": [riot_app],
    "wargaming": [wargaming_app],
    "tanks": [wargaming_app],
    "playnite": [playnite_app],
    "curseforge": [curseforge_app],

    # === SEKTOR: INTERNET & PROHLÍŽEČE ===
    "prohlížeč": _BROWSERS,
    "browser": _BROWSERS,
    "internet": _BROWSERS,
    "web": _BROWSERS,
    # Konkrétní
    "chrome": [chrome_app],
    "firefox": [firefox_app],
    "edge": [edge_app],
    "opera": [opera_app],

    # === SEKTOR: KOMUNIKACE ===
    "chat": _CHAT,
    "komunikace": _CHAT,
    "messenger": _CHAT,
    "social": _CHAT,
    # Konkrétní
    "discord": [discord_app],
    "telegram": [telegram_app],
    "teams": [teams_app],
    "skype": [skype_app],

    # === SEKTOR: VIDEO & PŘEHRÁVAČE (Nová sekce) ===
    # Obecné
    "video": _VIDEO,
    "přehrávač": _VIDEO,
    "prehravac": _VIDEO,
    "player": _VIDEO,
    "filmy": _VIDEO,
    "film": _VIDEO,
    # Konkrétní
    "vlc": [vlc_app],
    "mpc": [mpc_app],
    "potplayer": [potplayer_app],
    "kodi": [kodi_app],

    # === SEKTOR: GRAFIKA & KREATIVITA ===
    "grafika": _GRAPHICS,
    "foto": _GRAPHICS,
    "design": _GRAPHICS,
    "úprava": _GRAPHICS,
    # Konkrétní
    "gimp": [gimp_app],
    "photoshop": [photoshop_alt_app], 
    "krita": [krita_app],
    "blender": [blender_app],

    # === SEKTOR: KANCELÁŘ ===
    "office": _OFFICE,
    "kancelář": _OFFICE,
    "dokumenty": _OFFICE,
    "pdf": _PDF,
    "reader": _PDF,
    # Konkrétní
    "word": _OFFICE,
    "excel": _OFFICE,

    # === SEKTOR: SYSTÉMOVÉ NÁSTROJE ===
    "tools": _TOOLS,
    "nástroje": _TOOLS,
    "utility": _TOOLS,
    "zip": _TOOLS,
    "rar": _TOOLS,
    # Konkrétní
    "winrar": [winrar_app],
    "7zip": [{"name": "7-Zip", "id": "7zip.7zip", "website": "https://www.7-zip.org"}],
    
    # === SEKTOR: VÝVOJ ===
    "dev": _DEV,
    "vývoj": _DEV,
    "programování": _DEV,
    # Konkrétní
    "python": [python_app],
    "git": [{"name": "Git", "id": "Git.Git", "website": "https://git-scm.com"}],
    "vscode": [{"name": "Visual Studio Code", "id": "Microsoft.VisualStudioCode", "website": "https://code.visualstudio.com"}]
}