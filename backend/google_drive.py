"""Hidden Google Drive backups. Tokens stay in Windows DPAPI, outside app_state.
Network/OAuth work runs off the database command thread; each snapshot uses its own
SQLite read transaction. Only appDataFolder and explicit PLMS backup files are used.
"""
import base64
import copy
import ctypes
import datetime as dt
import gzip
import hashlib
import hmac
import http.server as http_server
import io
import json
import os
from pathlib import Path
import re
import secrets
import socket
import sqlite3
import sys
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import webbrowser

MAX_BACKUP = 64 * 1024 * 1024
SCOPE = 'https://www.googleapis.com/auth/drive.appdata openid email'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
FILES_URL = 'https://www.googleapis.com/drive/v3/files'
MARKER = 'medicsoft-plms-v2'
INTERVALS = (1, 6, 12, 24, 168)
ACTIONS = ('drive_status', 'drive_configure', 'drive_connect', 'drive_cancel',
           'drive_disconnect', 'drive_settings', 'drive_backup', 'drive_list',
           'drive_download', 'drive_delete', 'drive_job')


class DriveError(Exception):
    pass


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def protect_windows(data, decrypt=False):
    if sys.platform != 'win32':
        raise DriveError('Google account storage requires the Windows app.')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]
    buf = ctypes.create_string_buffer(data)
    source, target = Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    operation = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    operation.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise DriveError('Windows could not access the saved Google connection. Reconnect this Windows user.')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


class CredentialStore:
    def __init__(self, database, codec=protect_windows, directory=None):
        identity = hashlib.sha256(str(Path(database).resolve()).encode()).hexdigest()[:16]
        # Per-Windows-user credentials: no tokens in the shared ProgramData database.
        local = os.environ.get('LOCALAPPDATA')
        self.directory = Path(directory) if directory else (Path(local) / 'Medicsoft' / 'PLMS' / 'GoogleDrive' if local else Path(database).parent / '.google-drive')
        self.path = self.directory / (identity + '.dat')
        self.codec = codec

    def read(self):
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.codec(self.path.read_bytes(), True))
        except DriveError:
            raise
        except Exception:
            raise DriveError('The saved Google connection could not be read. Reconnect your account.') from None

    def write(self, value):
        encrypted = self.codec(compact(value).encode(), False)
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        with temp.open('wb') as stream:
            stream.write(encrypted)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, self.path)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def http(method, url, headers=None, body=None, limit=MAX_BACKUP):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('oauth2.googleapis.com', 'www.googleapis.com', 'openidconnect.googleapis.com'):
        raise DriveError('Unexpected Google service address.')
    request = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
            result = response.read(limit + 1)
            if len(result) > limit:
                raise DriveError('The Google response exceeds the backup size limit.')
            return result
    except urllib.error.HTTPError as error:
        code = error.code
        if code in (400, 401):
            raise DriveError('Google authorization expired or was rejected. Reconnect your account.') from None
        if code == 403:
            raise DriveError('Google refused this request. Check Drive API access and available storage.') from None
        if code == 404:
            raise DriveError('The selected Google Drive backup is no longer available.') from None
        if code == 429:
            raise DriveError('Google is busy. PLMS will retry the automatic backup later.') from None
        raise DriveError('Google Drive is temporarily unavailable. Local backups remain available.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise DriveError('Google Drive could not be reached. Check the internet connection; automatic backups will retry.') from None


def canonical_bytes(value):
    """PLMS value-v1: unambiguous typed values, UTF-16 key order and IEEE doubles.
    This avoids Python/JavaScript JSON number and integer-key ordering differences.
    """
    if value is None:return b'z'
    if value is True:return b't'
    if value is False:return b'f'
    if isinstance(value,(int,float)):
        number=float(value)
        if number!=number or abs(number)==float('inf'):raise DriveError('Backup contains a non-finite number.')
        return b'n'+struct.pack('>d',0.0 if number==0 else number)
    if isinstance(value,str):
        # TextEncoder replaces lone surrogates with U+FFFD; valid pairs become UTF-8.
        text=value.encode('utf-16-le','surrogatepass').decode('utf-16-le','replace').encode('utf-8')
        return b's'+str(len(text)).encode()+b':'+text
    if isinstance(value,list):return b'a'+str(len(value)).encode()+b':'+b''.join(canonical_bytes(item) for item in value)
    if isinstance(value,dict):
        keys=sorted(value,key=lambda key:key.encode('utf-16-be','surrogatepass'))
        return b'o'+str(len(keys)).encode()+b':'+b''.join(canonical_bytes(key)+canonical_bytes(value[key]) for key in keys)
    raise DriveError('Backup contains an unsupported value.')


def bundle_digest(payload):
    value={'data':payload['data'],'auditEvents':payload['auditEvents']}
    raw=canonical_bytes(value) if payload.get('version')==3 else compact(value).encode()
    return hashlib.sha256(raw).hexdigest()


def build_backup(database):
    # Consistent, non-mutating view of state, credentials and audit from one transaction.
    uri = Path(database).resolve().as_uri() + '?mode=ro'
    connection = sqlite3.connect(uri, uri=True, timeout=15)
    try:
        connection.execute('BEGIN')
        row = connection.execute('SELECT body FROM app_state WHERE id=1').fetchone()
        if not row:
            raise DriveError('Complete PLMS setup before backing up.')
        data = json.loads(row[0])
        hashes = dict(connection.execute('SELECT id,hash FROM credentials'))
        for user in data['users']:
            user['password'] = hashes.get(str(user['id']), '')
        events = []
        for ident, moment, actor, action in connection.execute('SELECT id,time,actor,action FROM security_audit ORDER BY id'):
            events.append({'id': 'native-' + str(ident), 'time': dt.datetime.fromtimestamp(moment, dt.timezone.utc).isoformat().replace('+00:00', 'Z'),
                           'module': 'Security', 'action': action, 'entity': 'Local database',
                           'actor': {'id': str(actor), 'name': str(actor)}, 'changes': []})
        digest = hashlib.sha256(canonical_bytes({'data': data, 'auditEvents': events})).hexdigest()
        payload = {'format': 'PLMS_BACKUP', 'version': 3, 'exportedAt': stamp(), 'data': data,
                   'auditEvents': events, 'integrity': {'algorithm': 'SHA-256', 'canonicalization': 'plms-value-v1', 'value': digest}}
        raw = compact(payload).encode()
        if len(raw) > MAX_BACKUP:
            raise DriveError('This backup exceeds the Google backup size limit (64 MiB). Use local export.')
        return payload, raw
    finally:
        connection.close()


def decode_backup(raw):
    try:
        if raw[:2] == b'\x1f\x8b':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_BACKUP + 1)
        if len(raw) > MAX_BACKUP:
            raise DriveError('The selected backup exceeds the restore size limit.')
        payload = json.loads(raw)
        if payload.get('format') != 'PLMS_BACKUP' or payload.get('version') not in (2,3) or not isinstance(payload.get('auditEvents'), list):
            raise DriveError('This is not a supported PLMS backup.')
        if payload['version']==3 and payload.get('integrity',{}).get('canonicalization')!='plms-value-v1':
            raise DriveError('Unsupported backup integrity format.')
        digest = bundle_digest(payload)
        if payload.get('integrity', {}).get('algorithm') != 'SHA-256' or not hmac.compare_digest(digest, str(payload.get('integrity', {}).get('value', ''))):
            raise DriveError('Backup integrity check failed. The backup was not restored.')
        return payload
    except DriveError:
        raise
    except Exception:
        raise DriveError('The selected backup is incomplete or invalid.') from None


class GoogleDrive:
    def __init__(self, database, store=None, transport=http, opener=webbrowser.open):
        self.database = Path(database)
        self.store = store or CredentialStore(database)
        self.transport, self.opener = transport, opener
        self.lock = threading.RLock()
        self.job = None
        self.cancel = threading.Event()
        self.stop = threading.Event()
        self.retry_at = 0
        try:
            self.config = self.store.read()
            if not isinstance(self.config,dict):raise DriveError('Invalid saved Google connection.')
        except (DriveError,OSError):
            # Reconnection must remain available even when an old DPAPI file was
            # copied from another PC or damaged. Never try plaintext tokens.
            self.config={'lastError':'The saved Google connection could not be read. Set up the connection and sign in again.'}
        # Bind authorization to this database installation. Deleting/replacing the
        # database must not silently reactivate an old Windows-user connection.
        connection=sqlite3.connect(self.database,timeout=15)
        try:
            connection.execute('CREATE TABLE IF NOT EXISTS google_backup_identity(id INTEGER PRIMARY KEY CHECK(id=1),value TEXT NOT NULL)')
            connection.execute('INSERT OR IGNORE INTO google_backup_identity VALUES(1,?)',(uuid.uuid4().hex,))
            instance=connection.execute('SELECT value FROM google_backup_identity WHERE id=1').fetchone()[0]
            connection.commit()
        finally:connection.close()
        if self.config.get('databaseId')!=instance:
            for key in ('refresh_token','email','lastSuccess'):self.config.pop(key,None)
            self.config['enabled']=False
            self.config['deviceId']=uuid.uuid4().hex
        self.config['databaseId']=instance
        self.config.setdefault('deviceId', uuid.uuid4().hex)
        self.config.setdefault('deviceName', socket.gethostname()[:80])
        self.config.setdefault('hours', 24)
        self.config.setdefault('retain', 14)
        self.config.setdefault('enabled', False)
        self._access = None
        if not self.config.get('client'):
            bundled = Path(getattr(sys, '_MEIPASS', Path(__file__).parent)) / 'google-drive-client.json'
            if bundled.exists():
                self.config['client'] = self.client_definition(json.loads(bundled.read_text(encoding='utf-8-sig')))

    @staticmethod
    def client_definition(value):
        client = value.get('installed') if isinstance(value, dict) else None
        if not isinstance(client, dict):
            raise DriveError('Select Google OAuth credentials created for a Desktop app.')
        ident = client.get('client_id', '')
        secret = client.get('client_secret', '')
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{10,250}\.apps\.googleusercontent\.com', ident):
            raise DriveError('The Google Desktop client ID is invalid.')
        if not isinstance(secret, str) or not secret or len(secret) > 500:
            raise DriveError('The Google Desktop client secret is missing or invalid.')
        return {'client_id': ident, 'client_secret': secret}

    def public_status(self):
        with self.lock:
            return {'configured': bool(self.config.get('client')), 'connected': bool(self.config.get('refresh_token')),
                    'email': self.config.get('email', ''), 'enabled': self.config['enabled'], 'hours': self.config['hours'],
                    'retain': self.config['retain'], 'lastSuccess': self.config.get('lastSuccess', ''),
                    'lastAttempt': self.config.get('lastAttempt', ''), 'lastError': self.config.get('lastError', ''),
                    'deviceName': self.config['deviceName'], 'busy': bool(self.job and self.job['state'] == 'running'),
                    'operation': self.job['kind'] if self.job and self.job['state'] == 'running' else ''}

    def _save(self):
        self.store.write(self.config)

    def _commit_config(self, candidate):
        # A failed Windows/disk write must not change the active account/schedule.
        self.store.write(candidate)
        self.config=candidate

    def configure(self, value):
        client = self.client_definition(value)
        with self.lock:
            self._idle()
            candidate=copy.deepcopy(self.config)
            changed=client!=candidate.get('client')
            if changed:
                for key in ('refresh_token', 'email', 'lastSuccess', 'lastError'):
                    candidate.pop(key, None)
                candidate['enabled'] = False
            candidate['client'] = client
            self._commit_config(candidate)
            if changed:self._access=None
        return self.public_status()

    def settings(self, enabled, hours, retain):
        if not isinstance(enabled, bool) or isinstance(hours, bool) or hours not in INTERVALS or isinstance(retain, bool) or not isinstance(retain, int) or not 3 <= retain <= 30:
            raise DriveError('Choose a valid backup schedule and keep between 3 and 30 backups.')
        with self.lock:
            self._idle()
            if enabled and not self.config.get('refresh_token'):
                raise DriveError('Connect a Google account before enabling automatic backups.')
            self._commit_config({**self.config,'enabled':enabled,'hours':hours,'retain':retain})
        return self.public_status()

    def _idle(self):
        if self.job and self.job['state'] == 'running':
            raise DriveError('A Google Drive operation is already running.')

    def _start(self, kind, operation):
        with self.lock:
            self._idle()
            self.job = {'id': uuid.uuid4().hex, 'kind': kind, 'state': 'running'}
            ident = self.job['id']
            self.cancel.clear()
        def work():
            try:
                result = operation()
                with self.lock:
                    self.job.update(state='done', result=result)
            except Exception as error:
                message = str(error) if isinstance(error, DriveError) else 'The Google Drive operation could not be completed. Try again.'
                with self.lock:
                    self.job.update(state='error', error=message)
                    self.config['lastError'] = message
                    try:
                        self._save()
                    except Exception:
                        pass
        threading.Thread(target=work, daemon=True, name='PLMS Google ' + kind).start()
        return {'jobId': ident}

    def job_status(self, ident):
        with self.lock:
            if not self.job or ident != self.job['id']:
                raise DriveError('The Google Drive operation is no longer available.')
            return copy.deepcopy(self.job)

    def connect(self):
        if not self.config.get('client'):
            raise DriveError('Set up the Google Desktop connection before connecting an account.')
        return self._start('connect', self._authorize)

    def cancel_connect(self):
        with self.lock:
            if self.job and self.job['state'] == 'running' and self.job['kind'] == 'connect':
                self.cancel.set()
        return {'ok': True}

    def _json(self, method, url, headers=None, body=None, limit=1024 * 1024):
        try:
            return json.loads(self.transport(method, url, headers, body, limit))
        except (ValueError, TypeError):
            raise DriveError('Google returned an invalid response. Try again.') from None

    def _token(self, parameters):
        client = self.config['client']
        parameters = {**parameters, 'client_id': client['client_id'], 'client_secret': client['client_secret']}
        return self._json('POST', TOKEN_URL, {'Content-Type': 'application/x-www-form-urlencoded'}, urllib.parse.urlencode(parameters).encode())

    def _authorize(self):
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        accepted = {}
        callback_path = '/'
        class Handler(http_server.BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass
            def do_GET(self):
                query = urllib.parse.urlsplit(self.path)
                values = urllib.parse.parse_qs(query.query)
                valid = query.path == callback_path and hmac.compare_digest(values.get('state', [''])[0], state)
                if not valid:
                    self.send_error(400, 'Invalid sign-in response')
                    return
                accepted.update({key: values.get(key, [''])[0] for key in ('code', 'error')})
                body = b'<html><body><h3>PLMS Google sign-in received</h3><p>You may close this tab and return to PLMS.</p></body></html>'
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        class Listener(http_server.HTTPServer):
            def get_request(self):
                connection, address = super().get_request()
                connection.settimeout(3)
                return connection, address
        with Listener(('127.0.0.1', 0), Handler) as listener:
            listener.timeout = .5
            redirect = 'http://127.0.0.1:' + str(listener.server_port) + callback_path
            params = {'client_id': self.config['client']['client_id'], 'redirect_uri': redirect, 'response_type': 'code',
                      'scope': SCOPE, 'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256',
                      'access_type': 'offline', 'prompt': 'consent select_account'}
            if self.opener('https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode(params)) is False:
                raise DriveError('Google sign-in could not open. Check your default browser.')
            deadline = time.monotonic() + 180
            while not accepted and time.monotonic() < deadline and not self.cancel.is_set() and not self.stop.is_set():
                listener.handle_request()
            if self.cancel.is_set() or self.stop.is_set():
                raise DriveError('Google sign-in was canceled.')
            if not accepted:
                raise DriveError('Google sign-in timed out. Click Connect Google Drive to try again.')
            if accepted.get('error') or not accepted.get('code'):
                raise DriveError('Google sign-in was not approved. No account was connected.')
            tokens = self._token({'code': accepted['code'], 'code_verifier': verifier, 'redirect_uri': redirect, 'grant_type': 'authorization_code'})
        if not tokens.get('refresh_token') or not tokens.get('access_token'):
            raise DriveError('Google did not provide background access. Reconnect and approve access.')
        granted = set(str(tokens.get('scope', '')).split())
        if 'https://www.googleapis.com/auth/drive.appdata' not in granted:
            raise DriveError('Hidden Drive backup access was not approved.')
        info = self._json('GET', 'https://openidconnect.googleapis.com/v1/userinfo', {'Authorization': 'Bearer ' + tokens['access_token']})
        if not info.get('email') or not info.get('email_verified'):
            raise DriveError('Google did not return a verified account email.')
        with self.lock:
            if self.cancel.is_set():
                raise DriveError('Google sign-in was canceled.')
            self._commit_config({**self.config,'refresh_token':tokens['refresh_token'],'email':info['email'],'lastError':''})
            self._access = (tokens['access_token'], time.time() + max(60, int(tokens.get('expires_in', 3600))) - 30)
        return self.public_status()

    def _headers(self):
        if not self.config.get('refresh_token'):
            raise DriveError('Connect a Google account first.')
        if not self._access or self._access[1] <= time.time():
            token = self._token({'grant_type': 'refresh_token', 'refresh_token': self.config['refresh_token']})
            if not token.get('access_token'):
                raise DriveError('Reconnect Google Drive to renew backup access.')
            self._access = (token['access_token'], time.time() + max(60, int(token.get('expires_in', 3600))) - 30)
            if token.get('refresh_token'):
                with self.lock:
                    self.config['refresh_token'] = token['refresh_token']
                    self._save()
        return {'Authorization': 'Bearer ' + self._access[0]}

    def disconnect(self):
        with self.lock:
            self._idle()
            # Forget local authorization without revoking another installation.
            candidate=copy.deepcopy(self.config)
            for key in ('refresh_token','email'):candidate.pop(key,None)
            candidate['enabled']=False
            self._commit_config(candidate)
            self._access=None
        return self.public_status()

    def _list(self):
        rows, page = [], ''
        while True:
            params = {'spaces': 'appDataFolder', 'q': "trashed=false and appProperties has { key='plmsBackup' and value='" + MARKER + "' }",
                      'pageSize': 100, 'fields': 'nextPageToken,files(id,name,createdTime,size,appProperties)', 'orderBy': 'createdTime desc'}
            if page:
                params['pageToken'] = page
            response = self._json('GET', FILES_URL + '?' + urllib.parse.urlencode(params), self._headers())
            rows.extend(response.get('files', []))
            page = response.get('nextPageToken', '')
            if not page:
                return rows
            if len(rows) > 5000:
                raise DriveError('Too many cloud backups. Review backup retention before continuing.')

    def list_backups(self):
        return self._start('list', lambda: {'files': self._list()})

    def backup(self):
        return self._start('backup', self._upload)

    def _upload(self):
        with self.lock:
            self.config['lastAttempt'] = stamp()
            self._save()
        payload, raw = build_backup(self.database)
        compressed = gzip.compress(raw)
        ident = uuid.uuid4().hex
        # Keep a full local recovery copy before attempting any network operation.
        root = self.database.parent.parent if self.database.parent.name in ('Database', 'data') else self.database.parent
        folder = root / 'Backup'
        folder.mkdir(parents=True, exist_ok=True)
        local = folder / ('PLMS-Google-' + ident + '.json')
        with local.open('wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        copies = sorted(folder.glob('PLMS-Google-*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in copies[self.config['retain']:]:
            old.unlink()
        headers = self._headers()
        metadata = {'name': 'PLMS-' + self.config['deviceId'][:8] + '-' + payload['exportedAt'].replace(':', '-') + '.json.gz',
                    'parents': ['appDataFolder'], 'mimeType': 'application/gzip',
                    'appProperties': {'plmsBackup': MARKER, 'deviceId': self.config['deviceId'],
                                      'deviceName': self.config['deviceName'], 'sha256': hashlib.sha256(compressed).hexdigest()}}
        boundary = 'plms_' + secrets.token_hex(24)
        body = (('--' + boundary + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' + compact(metadata) + '\r\n--' + boundary + '\r\nContent-Type: application/gzip\r\n\r\n').encode()
                + compressed + ('\r\n--' + boundary + '--\r\n').encode())
        headers['Content-Type'] = 'multipart/related; boundary=' + boundary
        result = self._json('POST', 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,size,appProperties', headers, body)
        if not result.get('id'):
            raise DriveError('Google did not confirm the backup upload. The local copy was retained.')
        # Read back checksum and complete contents before treating upload as success.
        check = self.transport('GET', FILES_URL + '/' + urllib.parse.quote(result['id'], safe='') + '?alt=media', self._headers(), None, MAX_BACKUP)
        if not hmac.compare_digest(hashlib.sha256(check).hexdigest(), metadata['appProperties']['sha256']):
            raise DriveError('The uploaded backup could not be verified. The local copy was retained.')
        with self.lock:
            self.config.update(lastSuccess=payload['exportedAt'], lastError='')
            self._save()
            self.retry_at = 0
        try:
            own = [row for row in self._list() if row.get('appProperties', {}).get('deviceId') == self.config['deviceId']]
            for row in own[self.config['retain']:]:
                self.transport('DELETE', FILES_URL + '/' + urllib.parse.quote(row['id'], safe=''), self._headers(), None, 1024)
            # Bounded local Google recovery copies; general PLMS snapshots untouched.
            copies = sorted(folder.glob('PLMS-Google-*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
            for path in copies[self.config['retain']:]:
                path.unlink()
        except Exception:
            with self.lock:
                self.config['lastError'] = 'Backup uploaded successfully; old backup cleanup will retry after the next backup.'
                self._save()
        return {'fileId': result['id'], 'time': self.config['lastSuccess']}

    def download(self, file_id, purpose="restore"):
        if purpose not in ("restore", "export"):
            raise DriveError("Choose a valid cloud backup action.")
        if not isinstance(file_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', file_id):
            raise DriveError('Select a valid PLMS cloud backup.')
        def run():
            row = self._json('GET', FILES_URL + '/' + file_id + '?fields=id,name,spaces,size,appProperties', self._headers())
            if 'appDataFolder' not in row.get('spaces', []) or row.get('appProperties', {}).get('plmsBackup') != MARKER:
                raise DriveError('This file is not a hidden PLMS backup.')
            if int(row.get('size', 0)) > MAX_BACKUP:
                raise DriveError('The selected backup exceeds the restore size limit.')
            raw = self.transport('GET', FILES_URL + '/' + file_id + '?alt=media', self._headers(), None, MAX_BACKUP)
            expected = row.get('appProperties', {}).get('sha256', '')
            if not expected or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected):
                raise DriveError('Cloud backup checksum failed. No data was restored.')
            return {'name': row.get('name', 'Google Drive backup'), 'payload': decode_backup(raw), 'purpose': purpose}
        return self._start('download', run)

    def delete_backup(self, file_id):
        if not isinstance(file_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', file_id):
            raise DriveError('Select a valid PLMS cloud backup.')
        def run():
            row = self._json('GET', FILES_URL + '/' + file_id + '?fields=id,spaces,appProperties', self._headers())
            if 'appDataFolder' not in row.get('spaces', []) or row.get('appProperties', {}).get('plmsBackup') != MARKER:
                raise DriveError('This file is not a hidden PLMS backup.')
            self.transport('DELETE', FILES_URL + '/' + file_id, self._headers(), None, 1024)
            return {'fileId': file_id}
        return self._start('delete', run)

    def tick(self, now=None):
        now = time.time() if now is None else now
        with self.lock:
            if not self.config['enabled'] or not self.config.get('refresh_token') or self.retry_at > now or (self.job and self.job['state'] == 'running'):
                return False
            try:
                last = dt.datetime.fromisoformat(self.config.get('lastSuccess', '').replace('Z', '+00:00')).timestamp()
            except ValueError:
                last = 0
            if now - last < self.config['hours'] * 3600:
                return False
            self.retry_at = now + 300
            self.backup()
            return True

    def start_scheduler(self):
        def run():
            while not self.stop.wait(30):
                try:
                    self.tick()
                except Exception:
                    pass  # Error is visible through job/status; never write protocol stdout.
        threading.Thread(target=run, daemon=True, name='PLMS Google scheduler').start()
