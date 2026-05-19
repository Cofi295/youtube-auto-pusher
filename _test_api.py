import sys
sys.path.insert(0, 'A:/ALL-TOOLS/YouTube-Auto-Pusher-ver1')
from core.database import DatabaseManager, Profile
from api_server import _profile_to_dict
DatabaseManager.initialize()
for p in DatabaseManager.get_all_profiles():
    try:
        d = _profile_to_dict(p)
        print(f'Profile {p.id}: OK, channels={len(d.get("channels", []))}')
    except Exception as e:
        print(f'Profile {p.id}: ERROR - {e}')
        import traceback; traceback.print_exc()
