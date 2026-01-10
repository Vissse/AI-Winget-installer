# data_providers.py
import requests
from config import COLORS

class WingetRunAPI:
    BASE_URL = "https://api.winget.run/v2/packages"

    @staticmethod
    def search(query, limit=5):
        results = []
        try:
            params = { 'query': query, 'take': limit, 'ensureContains': 'true' }
            headers = { 'User-Agent': 'Mozilla/5.0' }
            
            response = requests.get(WingetRunAPI.BASE_URL, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                packages = []
                if isinstance(data, dict): packages = data.get('Packages', [])
                elif isinstance(data, list): packages = data
                
                for pkg in packages:
                    if not isinstance(pkg, dict): continue
                    pkg_id = pkg.get('Id') or pkg.get('PackageIdentifier')
                    if not pkg_id: continue

                    latest = pkg.get('Latest', {})
                    if not isinstance(latest, dict): latest = {}
                    name = latest.get('Name') or pkg.get('Name') or pkg_id

                    version = "Latest"
                    versions_list = pkg.get('Versions', [])
                    if isinstance(versions_list, list) and len(versions_list) > 0:
                        version = versions_list[0]
                    
                    icon_url = latest.get('IconUrl') or pkg.get('IconUrl') or pkg.get('Logo')
                    tags = latest.get('Tags', [])
                    tags_str = ", ".join(tags[:3]) if tags else ""
                    
                    updated_at = pkg.get('UpdatedAt') or latest.get('UpdatedAt') or ""
                    if updated_at: updated_at = updated_at.split('T')[0]

                    results.append({
                        "name": name,
                        "id": pkg_id,
                        "version": version,
                        "icon_url": icon_url,
                        "website": "winget.run",
                        "tags": tags_str,
                        "updated": updated_at
                    })
        except Exception as e:
            print(f"API Error: {e}")
        
        return results