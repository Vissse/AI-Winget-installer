# presets.py

# ==============================================================================
# 1. DEFINICE JEDNOTLIVÝCH APLIKACÍ (S IKONAMI)
# ==============================================================================

# Používáme repozitář dashboard-icons přes jsDelivr (rychlý CDN)
BASE_ICON_URL = "https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png"

# --- Herní Launchery ---
steam_app = {
    "name": "Steam", "id": "Valve.Steam", "website": "https://store.steampowered.com",
    "icon_url": f"{BASE_ICON_URL}/steam.png"
}
epic_app = {
    "name": "Epic Games Launcher", "id": "EpicGames.EpicGamesLauncher", "website": "https://store.epicgames.com",
    "icon_url": f"{BASE_ICON_URL}/epic-games.png"
}
ubisoft_app = {
    "name": "Ubisoft Connect", "id": "Ubisoft.Connect", "website": "https://ubisoftconnect.com",
    "icon_url": f"{BASE_ICON_URL}/ubisoft-connect.png"
}
ea_app = {
    "name": "EA App", "id": "ElectronicArts.EADesktop", "website": "https://www.ea.com/ea-app",
    "icon_url": f"{BASE_ICON_URL}/ea.png"
}
gog_app = {
    "name": "GOG GALAXY", "id": "GOG.Galaxy", "website": "https://www.gog.com/galaxy",
    "icon_url": f"{BASE_ICON_URL}/gog-galaxy.png"
}
playnite_app = {
    "name": "Playnite", "id": "Playnite.Playnite", "website": "https://playnite.link",
    "icon_url": f"{BASE_ICON_URL}/playnite.png"
}
battlenet_app = {
    "name": "Battle.net", "id": "Blizzard.BattleNet", "website": "https://www.blizzard.com",
    "icon_url": f"{BASE_ICON_URL}/battle-net.png"
}
curseforge_app = {
    "name": "CurseForge", "id": "Overwolf.CurseForge", "website": "https://www.curseforge.com",
    "icon_url": f"{BASE_ICON_URL}/curseforge.png"
}
riot_app = {
    "name": "Riot Client", "id": "RiotGames.LeagueOfLegends.EUNE", "website": "https://www.riotgames.com",
    "icon_url": f"{BASE_ICON_URL}/riot-games.png"
}
wargaming_app = {
    "name": "Wargaming.net", "id": "Wargaming.GameCenter", "website": "https://wargaming.net",
    "icon_url": f"{BASE_ICON_URL}/wargaming.png"
}

# --- Prohlížeče ---
chrome_app = {
    "name": "Google Chrome", "id": "Google.Chrome", "website": "https://www.google.com/chrome",
    "icon_url": f"{BASE_ICON_URL}/google-chrome.png"
}
firefox_app = {
    "name": "Mozilla Firefox", "id": "Mozilla.Firefox", "website": "https://www.mozilla.org/firefox",
    "icon_url": f"{BASE_ICON_URL}/firefox.png"
}
edge_app = {
    "name": "Microsoft Edge", "id": "Microsoft.Edge", "website": "https://www.microsoft.com/edge",
    "icon_url": f"{BASE_ICON_URL}/microsoft-edge.png"
}
brave_app = {
    "name": "Brave Browser", "id": "Brave.Brave", "website": "https://brave.com",
    "icon_url": f"{BASE_ICON_URL}/brave.png"
}
opera_app = {
    "name": "Opera", "id": "Opera.Opera", "website": "https://www.opera.com",
    "icon_url": f"{BASE_ICON_URL}/opera.png"
}
opera_gx_app = {
    "name": "Opera GX", "id": "Opera.OperaGX", "website": "https://www.opera.com/gx",
    "icon_url": f"{BASE_ICON_URL}/opera-gx.png"
}
vivaldi_app = {
    "name": "Vivaldi", "id": "Vivaldi.Vivaldi", "website": "https://vivaldi.com",
    "icon_url": f"{BASE_ICON_URL}/vivaldi.png"
}
zen_app = {
    "name": "Zen Browser", "id": "Zen-Team.Zen-Browser", "website": "https://www.zen-browser.app",
    "icon_url": "https://cdn.jsdelivr.net/gh/zen-browser/desktop/assets/zen-logo.png" 
}
librewolf_app = {
    "name": "LibreWolf", "id": "LibreWolf.LibreWolf", "website": "https://librewolf.net",
    "icon_url": f"{BASE_ICON_URL}/librewolf.png"
}
ungoogled_app = {
    "name": "Ungoogled Chromium", "id": "eloston.ungoogled-chromium", "website": "https://github.com/ungoogled-software/ungoogled-chromium",
    "icon_url": f"{BASE_ICON_URL}/ungoogled-chromium.png"
}
waterfox_app = {
    "name": "Waterfox", "id": "Waterfox.Waterfox", "website": "https://www.waterfox.net",
    "icon_url": f"{BASE_ICON_URL}/waterfox.png"
}

# --- Komunikace ---
discord_app = {
    "name": "Discord", "id": "Discord.Discord", "website": "https://discord.com",
    "icon_url": f"{BASE_ICON_URL}/discord.png"
}
telegram_app = {
    "name": "Telegram", "id": "Telegram.TelegramDesktop", "website": "https://desktop.telegram.org",
    "icon_url": f"{BASE_ICON_URL}/telegram.png"
}
signal_app = {
    "name": "Signal", "id": "OpenWhisperSystems.Signal", "website": "https://signal.org",
    "icon_url": f"{BASE_ICON_URL}/signal.png"
}
teams_app = {
    "name": "Teams", "id": "Microsoft.Teams", "website": "https://www.microsoft.com/microsoft-teams",
    "icon_url": f"{BASE_ICON_URL}/microsoft-teams.png"
}
skype_app = {
    "name": "Skype", "id": "Zoom.ZoomSkypeForBusinessPlugin", "website": "https://www.skype.com",
    "icon_url": f"{BASE_ICON_URL}/skype.png"
}

# --- Grafika ---
gimp_app = {
    "name": "GIMP", "id": "GIMP.GIMP.3", "website": "https://www.gimp.org",
    "icon_url": f"{BASE_ICON_URL}/gimp.png"
}
photoshop_alt_app = {
    "name": "Paint.NET", "id": "dotPDN.PaintDotNet", "website": "https://www.getpaint.net",
    "icon_url": f"{BASE_ICON_URL}/paint-net.png"
}
inkscape_app = {
    "name": "Inkscape", "id": "Inkscape.Inkscape", "website": "https://inkscape.org",
    "icon_url": f"{BASE_ICON_URL}/inkscape.png"
}
krita_app = {
    "name": "Krita", "id": "KDE.Krita", "website": "https://krita.org",
    "icon_url": f"{BASE_ICON_URL}/krita.png"
}
blender_app = {
    "name": "Blender", "id": "BlenderFoundation.Blender", "website": "https://www.blender.org",
    "icon_url": f"{BASE_ICON_URL}/blender.png"
}
irfan_app = {
    "name": "IrfanView", "id": "IrfanSkiljan.IrfanView", "website": "https://www.irfanview.com",
    "icon_url": f"{BASE_ICON_URL}/irfanview.png"
}
affinity_app = {
    "name": "Affinity", 
    "id": "Canva.Affinity", 
    "website": "https://affinity.serif.com",
    "icon_url": f"{BASE_ICON_URL}/affinity.png" 
}

# --- Video ---
vlc_app = {
    "name": "VLC media player", "id": "VideoLAN.VLC", "website": "https://www.videolan.org/vlc",
    "icon_url": f"{BASE_ICON_URL}/vlc.png"
}
mpc_app = {
    "name": "MPC-BE", "id": "MPC-BE.MPC-BE", "website": "https://sourceforge.net/projects/mpcbe/",
    "icon_url": f"{BASE_ICON_URL}/mpc-hc.png"
}
potplayer_app = {
    "name": "Daum PotPlayer", "id": "Daum.PotPlayer", "website": "https://potplayer.daum.net",
    "icon_url": f"{BASE_ICON_URL}/potplayer.png"
}
kodi_app = {
    "name": "Kodi", "id": "XBMCFoundation.Kodi", "website": "https://kodi.tv",
    "icon_url": f"{BASE_ICON_URL}/kodi.png"
}

# --- Nástroje ---
winrar_app = {
    "name": "WinRAR", "id": "RARLab.WinRAR", "website": "https://www.win-rar.com",
    "icon_url": f"{BASE_ICON_URL}/winrar.png"
}
python_app = {
    "name": "Python 3", "id": "Python.Python.3.12", "website": "https://www.python.org",
    "icon_url": f"{BASE_ICON_URL}/python.png"
}

# --- Audio ---
audacity_app = {
    "name": "Audacity", "id": "Audacity.Audacity", "website": "https://www.audacityteam.org",
    "icon_url": f"{BASE_ICON_URL}/audacity.png"
}
ocenaudio_app = {
    "name": "ocenaudio", "id": "Ocenaudio.Ocenaudio", "website": "https://www.ocenaudio.com",
    "icon_url": f"{BASE_ICON_URL}/ocenaudio.png"
}

# ==============================================================================
# 2. DEFINICE SKUPIN (SOUHRNNÉ LISTY)
# ==============================================================================

_BROWSERS = [chrome_app, firefox_app, edge_app, brave_app, opera_app, opera_gx_app, vivaldi_app, zen_app, librewolf_app, ungoogled_app, waterfox_app]
_CHAT = [discord_app, telegram_app, signal_app, teams_app, skype_app]
_GAMES = [steam_app, epic_app, ubisoft_app, ea_app, gog_app, battlenet_app, riot_app, wargaming_app, playnite_app, curseforge_app]
_GRAPHICS = [gimp_app, photoshop_alt_app, inkscape_app, krita_app, blender_app, irfan_app, affinity_app]
_VIDEO = [vlc_app, mpc_app, potplayer_app, kodi_app]
_AUDIO = [audacity_app, ocenaudio_app]

_PDF = [
    {"name": "Adobe Acrobat Reader", "id": "Adobe.Acrobat.Reader.64-bit", "website": "https://get.adobe.com/reader", "icon_url": f"{BASE_ICON_URL}/adobe-acrobat-reader.png"},
    {"name": "Sumatra PDF", "id": "SumatraPDF.SumatraPDF", "website": "https://www.sumatrapdfreader.org", "icon_url": f"{BASE_ICON_URL}/sumatrapdf.png"},
    {"name": "Foxit PDF Reader", "id": "Foxit.FoxitReader", "website": "https://www.foxit.com", "icon_url": f"{BASE_ICON_URL}/foxit-reader.png"}
]

_OFFICE = [
    {"name": "LibreOffice", "id": "TheDocumentFoundation.LibreOffice", "website": "https://www.libreoffice.org", "icon_url": f"{BASE_ICON_URL}/libreoffice.png"},
    {"name": "Microsoft 365 (Office)", "id": "Microsoft.Office", "website": "https://www.office.com", "icon_url": f"{BASE_ICON_URL}/microsoft-office.png"},
    {"name": "OnlyOffice", "id": "ONLYOFFICE.DesktopEditors", "website": "https://www.onlyoffice.com", "icon_url": f"{BASE_ICON_URL}/onlyoffice.png"}
]

_TOOLS = [
    {"name": "7-Zip", "id": "7zip.7zip", "website": "https://www.7-zip.org", "icon_url": f"{BASE_ICON_URL}/7-zip.png"},
    winrar_app,
    {"name": "Notepad++", "id": "Notepad++.Notepad++", "website": "https://notepad-plus-plus.org", "icon_url": f"{BASE_ICON_URL}/notepad-plus-plus.png"},
    {"name": "AnyDesk", "id": "AnyDesk.AnyDesk", "website": "https://anydesk.com", "icon_url": f"{BASE_ICON_URL}/anydesk.png"},
    {"name": "OBS Studio", "id": "OBSProject.OBSStudio", "website": "https://obsproject.com", "icon_url": f"{BASE_ICON_URL}/obs-studio.png"},
    {"name": "PowerToys", "id": "Microsoft.PowerToys", "website": "https://learn.microsoft.com/windows/powertoys/", "icon_url": f"{BASE_ICON_URL}/powertoys.png"}
]

_DEV = [
    {"name": "VS Code", "id": "Microsoft.VisualStudioCode", "website": "https://code.visualstudio.com", "icon_url": f"{BASE_ICON_URL}/visual-studio-code.png"},
    {"name": "Git", "id": "Git.Git", "website": "https://git-scm.com", "icon_url": f"{BASE_ICON_URL}/git.png"},
    python_app,
    {"name": "Node.js", "id": "OpenJS.NodeJS.LTS", "website": "https://nodejs.org", "icon_url": f"{BASE_ICON_URL}/node-js.png"}
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
    "gx": [opera_gx_app],       
    "opera gx": [opera_gx_app], 
    "brave": [brave_app],
    "vivaldi": [vivaldi_app],
    "zen": [zen_app],
    "librewolf": [librewolf_app], 
    "ungoogled": [ungoogled_app], 
    "chromium": [ungoogled_app],  
    "waterfox": [waterfox_app],   

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
    "signal": [signal_app],

    # === SEKTOR: VIDEO & PŘEHRÁVAČE ===
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
    # Konkrétní
    "gimp": [gimp_app],
    "photoshop": [photoshop_alt_app], 
    "krita": [krita_app],
    "blender": [blender_app],
    "irfan": [irfan_app],
    "affinity": [affinity_app], 

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
    "7zip": _TOOLS[0], 
    "anydesk": [_TOOLS[3]],
    
    # === SEKTOR: VÝVOJ ===
    "dev": _DEV,
    "vývoj": _DEV,
    "programování": _DEV,
    # Konkrétní
    "python": [python_app],
    "git": [_DEV[1]],
    "vscode": [_DEV[0]],

    # === SEKTOR: AUDIO & ZVUK ===
    "audio": _AUDIO,
    "zvuk": _AUDIO,
    "sound": _AUDIO,
    "editor zvuku": _AUDIO,
    # Konkrétní
    "audacity": [audacity_app],
    "ocenaudio": [ocenaudio_app]
}