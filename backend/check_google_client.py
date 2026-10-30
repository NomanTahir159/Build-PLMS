"""Validate build-owner Desktop client configuration without printing credentials."""
import json
from pathlib import Path
from google_drive import GoogleDrive

if __name__=='__main__':
    path=Path(__file__).with_name('google-drive-client.json')
    try:
        GoogleDrive.client_definition(json.loads(path.read_text(encoding='utf-8-sig')))
    except Exception:
        raise SystemExit('Google client configuration must be the JSON downloaded for a Desktop OAuth client.')
    print('Google Desktop OAuth client configuration validated.')
