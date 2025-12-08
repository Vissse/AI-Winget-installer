import requests
import json
import datetime

# URL API
BASE_URL = "https://api.winget.run/v2/packages"

def test_deep_inspection(query):
    print(f"\n--- HLOUBKOVÁ INSPEKCE PRO: '{query}' ---")
    
    # Používáme osvědčené parametry z předchozího testu
    params = {
        'query': query,
        'take': 1,
        'ensureContains': 'true'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python/3.9'
    }

    try:
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Chyba serveru: {response.status_code}")
            return

        data = response.json()
        packages = data.get('Packages', []) if isinstance(data, dict) else data

        if not packages:
            print("Žádné balíčky nenalezeny.")
            return

        # Vezmeme první balíček pro analýzu
        pkg = packages[0]
        
        # Získáme objekt 'Latest' - tam bývá většina detailů
        latest = pkg.get('Latest', {})
        if not isinstance(latest, dict): latest = {}

        print(f"ID Balíčku: {pkg.get('PackageIdentifier')}")
        print("-" * 40)

        # 1. HLEDÁNÍ IKONY
        # Prohledáme všechna možná místa
        icon_root = pkg.get('IconUrl') or pkg.get('Logo')
        icon_latest = latest.get('IconUrl') or latest.get('Logo') or latest.get('InstallerIconUrl')
        
        print(f"[IKONA]")
        print(f"  V rootu:   {icon_root}")
        print(f"  V Latest:  {icon_latest}")
        
        # 2. HLEDÁNÍ DATUMU (UpdatedAt)
        # Hledáme klíče, které vypadají jako čas
        date_root = pkg.get('UpdatedAt') or pkg.get('ModifiedAt')
        date_latest = latest.get('UpdatedAt') or latest.get('ManifestVersion') # Někdy verze obsahuje datum
        
        print(f"[DATUM]")
        print(f"  V rootu:   {date_root}")
        print(f"  V Latest:  {date_latest}")

        # 3. HLEDÁNÍ TAGŮ
        tags = latest.get('Tags')
        print(f"[TAGY]")
        print(f"  Nalezeno:  {tags}")

        print("-" * 40)
        print("RAW DATA Z OBJEKTU 'Latest' (pro kontrolu klíčů):")
        # Vypíšeme jen klíče a zkrácené hodnoty, abychom viděli strukturu
        for key, value in latest.items():
            val_str = str(value)
            if len(val_str) > 50: val_str = val_str[:50] + "..."
            print(f"  '{key}': {val_str}")

    except Exception as e:
        print(f"Chyba: {e}")

if __name__ == "__main__":
    # Otestujeme na Steamu, ten by měl mít hodně metadat
    test_deep_inspection("Steam")