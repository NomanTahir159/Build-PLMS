"""PLMS private stdin/stdout API. No HTTP listener or browser-selected file paths."""
import math, datetime, copy, hashlib, hmac, json, os, re, secrets, sqlite3, sys, time
from html.parser import HTMLParser
from pathlib import Path

MAX_BYTES = 64 * 1024 * 1024
class ApiError(Exception): pass

def password_hash(password):
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise ApiError('Use a password of 12 to 256 characters.')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000)
    return f'pbkdf2-sha256$600000${salt.hex()}${digest.hex()}'

def password_verify(password, encoded):
    try:
        alg, count, salt, digest = encoded.split('$')
        if alg != 'pbkdf2-sha256' or not 600000 <= int(count) <= 2000000 or len(salt) != 32 or len(digest) != 64: return False
        if not isinstance(password, str) or len(password) > 256: return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(count))
        return hmac.compare_digest(actual, bytes.fromhex(digest))
    except (ValueError, AttributeError): return False

def validate_tree(value, depth=0):
    if depth > 40: raise ApiError('Data is nested too deeply.')
    if isinstance(value,float) and not math.isfinite(value):raise ApiError('Invalid numeric value.')
    if isinstance(value, dict):
        if any(k in ('__proto__', 'prototype', 'constructor') for k in value): raise ApiError('Invalid data key.')
        for v in value.values(): validate_tree(v, depth+1)
    elif isinstance(value, list):
        if len(value)>100000: raise ApiError('Too many records.')
        for v in value: validate_tree(v, depth+1)
    elif not isinstance(value,(str,int,float,bool,type(None))): raise ApiError('Invalid data type.')

class SafeReportHTML(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag.lower() in ('script','iframe','object','embed','base','meta','link','foreignobject','animate','set'):
            raise ApiError('Unsafe report HTML.')
        for key,value in attrs:
            if key.lower().startswith('on'):raise ApiError('Unsafe report event handler.')
            if key.lower() in ('href','src','xlink:href','action','formaction'):
                url=re.sub(r'[\x00-\x20]+','',value or '').lower()
                if url.startswith(('javascript:','vbscript:')) or (url.startswith('data:') and not re.match(r'data:image/(png|jpeg|webp|gif);base64,',url)):raise ApiError('Unsafe report URL.')

def valid_hash(value):
    return isinstance(value,str) and bool(re.fullmatch(r'pbkdf2-sha256\$(600000|[6-9][0-9]{5}|1[0-9]{6}|2000000)\$[0-9a-f]{32}\$[0-9a-f]{64}',value))

def validate_state(s):
    validate_tree(s)
    if not isinstance(s,dict): raise ApiError('Invalid application data.')
    for key, idkey in [('patients','lab'),('orders','lab'),('catalog','code'),('users','id')]:
        if not isinstance(s.get(key),list): raise ApiError('Missing '+key+' list.')
        ids=set()
        for row in s[key]:
            if not isinstance(row,dict) or not str(row.get(idkey,'')).strip(): raise ApiError('Invalid '+key+' record.')
            ident=str(row[idkey]).lower() if key=='users' else str(row[idkey])
            if ident in ids: raise ApiError('Duplicate '+key+' identifier.')
            ids.add(ident)
    labs={str(p['lab']) for p in s['patients']}
    for o in s['orders']:
        if str(o['lab']) not in labs or not isinstance(o.get('tests'),list) or any(not isinstance(x,str) for x in o['tests']): raise ApiError('Invalid order reference.')
    for lab, values in s.get('results',{}).items():
        if str(lab) not in labs or not isinstance(values,dict): raise ApiError('Invalid result reference.')
        if any(not isinstance(v,(str,int,float,bool,type(None))) for v in values.values()): raise ApiError('Invalid result value.')
    for u in s['users']:
        if not u.get('name') or not u.get('role'): raise ApiError('User name and role are required.')
    for template in s.get('reportTemplates',[]):
        if not isinstance(template,dict):raise ApiError('Invalid report template.')
        SafeReportHTML().feed(str(template.get('content','')))
    for versions in s.get('reportVersions',{}).values():
        if not isinstance(versions,list):raise ApiError('Invalid report history.')
        for version in versions:SafeReportHTML().feed(str(version.get('html','')))
    return s

ARRAY_POLICY = {
 'patients':('lab','patients'), 'orders':('lab','orders'), 'catalog':('code','catalog'),
 'users':('id','users'), 'inventory':('id','inventory'), 'qcEntries':('id','qc'),
 'criticalAlerts':('code','critical_alerts'), 'reportTemplates':('id','reports'),
 'textTemplates':('id','reports')}
GLOBAL_POLICY = {
 'rolePermissions':'admin_tools.manage_roles','userPermissionOverrides':'users.change_permissions',
 'profileRegistry':'catalog.edit_profile','profileDepartments':'catalog.edit_profile',
 'profileTestOrder':'catalog.reorder_profile_tests','profileSections':'catalog.edit_profile',
 'profileTestDefinitions':'catalog.edit_profile','profileStatus':'catalog.edit_profile',
 'profileActive':'catalog.edit_profile','profileOrder':'catalog.edit_profile',
 'profileCodes':'catalog.edit_profile','criticalHiddenTests':'critical_alerts.delete','catalogOrder':'catalog.reorder_tests','settings':'settings.edit','reportVersionAssets':'reports.amend',
 'reportVersions':'reports.amend','resultReferences':'results.edit',
 'reportText':'results.edit','resultReportContent':'results.edit','inventoryTransactions':'inventory.adjust_stock'}
CLIENT_PREFS={'theme','themeMode','accent','accentColor','ui','preferences'}

class Backend:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS app_state(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS credentials(id TEXT PRIMARY KEY, hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS security_audit(id INTEGER PRIMARY KEY, time REAL NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, time TEXT NOT NULL, reason TEXT NOT NULL, bytes INTEGER NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS login_failures(login TEXT PRIMARY KEY, failures INTEGER NOT NULL, until REAL NOT NULL);''')
        self.sessions={}
    def initialized(self): return self.db.execute('SELECT 1 FROM app_state WHERE id=1').fetchone() is not None
    def load(self):
        r=self.db.execute('SELECT revision, body FROM app_state WHERE id=1').fetchone()
        if not r: raise ApiError('Complete first-time setup.')
        return r[0],json.loads(r[1])
    def audit(self, actor, action): self.db.execute('INSERT INTO security_audit(time,actor,action) VALUES(?,?,?)',(time.time(),str(actor),action))
    def require(self, user, data, *permissions):
        if not any(self.allowed(user,data,p) for p in permissions): raise ApiError('Permission denied: '+permissions[0])
    def allowed(self,u,s,p):
        role=str(u.get('role','')).lower()
        if role=='administrator': return True
        # Unknown/missing permissions are denied; use authoritative stored assignments.
        return s.get('userPermissionOverrides',{}).get(str(u['id']),{}).get(p,s.get('rolePermissions',{}).get(u.get('role'),{}).get(p,False)) is True
    def actor(self, token):
        session=self.sessions.get(token)
        if not session or time.time()-session['last']>1800 or time.time()-session['start']>28800:
            self.sessions.pop(token,None); raise ApiError('Session expired. Sign in again.')
        rev,s=self.load();u=next((u for u in s['users'] if str(u['id'])==session['id'] and str(u.get('status','Active')).lower()=='active'),None)
        if not u: self.sessions.pop(token,None); raise ApiError('Account is inactive.')
        cred=self.db.execute('SELECT hash FROM credentials WHERE id=?',(session['id'],)).fetchone()
        if not cred or not hmac.compare_digest(session['credential'],cred[0]):self.sessions.pop(token,None);raise ApiError('Password changed. Sign in again.')
        session['last']=time.time();return session,u,rev,s
    def departments(self,u):
        if str(u.get('role','')).lower() in ('administrator','reception'): return None
        raw=u.get('department') or u.get('departments') or 'All'
        parts=raw if isinstance(raw,list) else re.split(r'[,;|]',str(raw))
        if any(str(x).strip().lower() in ('all','all departments','laboratory','') for x in parts): return None
        return {str(x).strip().lower() for x in parts}
    def item_tests(self,s,key):
        direct=[t for t in s['catalog'] if t.get('name')==key]
        return direct[:1] or [t for t in s['catalog'] if key in (t.get('profiles') or []) or t.get('profile')==key]
    def can_lab(self,u,s,lab):
        depts=self.departments(u)
        if depts is None: return True
        o=next((o for o in s['orders'] if str(o['lab'])==str(lab)),None)
        if not o: return False
        # Mixed-department records stay private unless every booked department is assigned.
        ds={str(t.get('department','')).lower() for key in o['tests'] for t in self.item_tests(s,key)}
        return bool(ds) and ds <= depts
    def visible(self,u,s):
        out=copy.deepcopy(s)
        clinical=any(self.allowed(u,s,k) for k in ('patients.view','orders.view','samples.view','results.view','reports.view'))
        labs={str(p['lab']) for p in s['patients'] if clinical and self.can_lab(u,s,p['lab'])}
        for key in ('patients','orders'): out[key]=[r for r in out.get(key,[]) if str(r['lab']) in labs]
        for key in ('results','resultReferences','reportVersions','resultReportContent','reportText'):
            permitted=any(self.allowed(u,s,k) for k in ('results.view','reports.view'))
            out[key]={k:v for k,v in out.get(key,{}).items() if str(k) in labs} if permitted else {}
        assets=set()
        for versions in out.get('reportVersions',{}).values():
            for version in versions:assets.update(re.findall(r'plms-version-asset:([A-Za-z0-9_-]+)',version.get('html','')))
        out['reportVersionAssets']={k:v for k,v in out.get('reportVersionAssets',{}).items() if self.allowed(u,s,'reports.view') and k in assets}
        for key,p in [('inventory','inventory.view'),('qcEntries','qc.view'),('criticalAlerts','critical_alerts.view')]:
            if not self.allowed(u,s,p):out[key]=[]
        depts=self.departments(u)
        if depts is not None:
            for key in ('inventory','qcEntries'):out[key]=[r for r in out.get(key,[]) if str(r.get('department','All')).lower() in depts|{'all','all departments'}]
        if not self.allowed(u,s,'users.view'): out['users']=[r for r in out['users'] if str(r['id'])==str(u['id'])]
        for row in out['users']: row['password']='';row['passwordSet']=bool(self.db.execute('SELECT 1 FROM credentials WHERE id=?',(str(row['id']),)).fetchone());row['bypassLogin']=False
        # Never expose other users' overrides when Users & Roles is unavailable.
        if not self.allowed(u,s,'users.view'):out['userPermissionOverrides']={str(u['id']):out.get('userPermissionOverrides',{}).get(str(u['id']),{})}
        return out
    def response(self,session,u,rev,s):
        state=self.visible(u,s);session['base']=copy.deepcopy(state);session['revision']=rev
        return {'state':state,'revision':rev,'userId':str(u['id'])}
    def login(self,login,password):
        key=str(login).strip().lower(); now=time.time()
        failure=self.db.execute('SELECT failures,until FROM login_failures WHERE login=?',(key,)).fetchone()
        if failure and failure[1]>now:raise ApiError('Too many attempts. Try again in a few minutes.')
        rev,s=self.load();u=next((x for x in s['users'] if str(x['id']).lower()==key),None)
        if not u:
            matches=[x for x in s['users'] if str(x.get('name','')).lower()==key]
            u=matches[0] if len(matches)==1 else None
        cred=self.db.execute('SELECT hash FROM credentials WHERE id=?',(str(u['id']),)).fetchone() if u else None
        dummy='pbkdf2-sha256$600000$'+'00'*16+'$'+'00'*32
        ok=password_verify(password,cred[0] if cred else dummy)
        if not ok or not u or str(u.get('status','Active')).lower()!='active':
            n=(failure[0] if failure else 0)+1
            self.db.execute('INSERT OR REPLACE INTO login_failures VALUES(?,?,?)',(key,n,now+300 if n>=5 else 0));raise ApiError('Username or password is incorrect, or the account is inactive.')
        self.db.execute('DELETE FROM login_failures WHERE login=?',(key,));token=secrets.token_urlsafe(32)
        session={'id':str(u['id']),'last':now,'start':now,'credential':cred[0]};self.sessions[token]=session;self.audit(u['id'],'Signed in')
        return {'token':token,**self.response(session,u,rev,s)}
    def bootstrap(self,req):
        if self.initialized():raise ApiError('Setup is already complete.')
        s=validate_state(copy.deepcopy(req['state']));login=str(req['username']).strip();hashed=password_hash(req['password'])
        if not login or len(login)>100:raise ApiError('Enter a valid username.')
        # Preserve imported records and accounts, but never keep legacy/default passwords active.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            for u in s['users']:
                old=u.pop('password','');u.pop('passwordSet',None);u['bypassLogin']=False
                if valid_hash(old) and not password_verify('123',old):self.db.execute('INSERT INTO credentials VALUES(?,?)',(str(u['id']),old))
                else:u['status']='Inactive'
            admin=next((u for u in s['users'] if str(u['id']).lower()==login.lower()),None)
            if not admin:admin={'id':login,'name':req.get('name') or 'Administrator'};s['users'].append(admin)
            admin.update(role='Administrator',status='Active',department='All',bypassLogin=False)
            self.db.execute('INSERT OR REPLACE INTO credentials VALUES(?,?)',(str(admin['id']),hashed))
            self.db.execute('INSERT INTO app_state VALUES(1,1,?)',(json.dumps(s,ensure_ascii=False),));self.audit(admin['id'],'Database initialized and existing data migrated');self.db.execute('COMMIT')
        except Exception:self.db.execute('ROLLBACK');raise
        return self.login(str(admin['id']),req['password'])
    def user_change(self,u,s,old,new):
        if old is None:
            self.require(u,s,'users.add')
            if new.get('role')!='Technologist':self.require(u,s,'users.change_role')
            if new.get('department','All')!=u.get('department','All'):self.require(u,s,'users.change_department')
        elif new is None:self.require(u,s,'users.delete');return
        else:self.require(u,s,'users.edit')
        for field,permission in [('id','users.edit_user_id'),('role','users.change_role'),('department','users.change_department'),('status','users.change_status'),('permissions','users.change_permissions')]:
            if old and old.get(field)!=new.get(field):self.require(u,s,permission)
        if new.get('bypassLogin'):raise ApiError('Bypass Login is unavailable with trusted authentication.')
        pwd=new.pop('__nativePassword',None);new.pop('passwordSet',None);new.pop('password',None)
        if pwd:
            self.require(u,s,'users.reset_password' if old else 'users.add')
            self.db.execute('INSERT OR REPLACE INTO credentials VALUES(?,?)',(str(new['id']),password_hash(pwd)))
        elif old is None:raise ApiError('Set a password for the new account.')
    def order_change(self,u,s,old,new):
        if old is None:
            self.require(u,s,'orders.add')
            for key in new['tests']:
                tests=self.item_tests(s,key)
                if not tests or any(t.get('active') is False for t in tests) or s.get('profileActive',{}).get(str(key).strip().lower()) is False:raise ApiError('Only active, known tests and profiles can be booked.')
            return
        if new is None:self.require(u,s,'orders.delete');return
        booking=set(old)|set(new)-{'testStates'}
        workflow={'testStates','sample','status','reportedAt','reportStatus','approvedAt','approvedBy','processedAt','receivedAt','collectedAt','sampleHistory','resultStatus','resultHistory','parameterStates'}
        if any(old.get(k)!=new.get(k) for k in booking-workflow):self.require(u,s,'orders.edit')
        for key in set(old.get('testStates',{}))|set(new.get('testStates',{})):
            a=old.get('testStates',{}).get(key,{});b=new.get('testStates',{}).get(key,{})
            if a==b:continue
            if a.get('sampleStatus')!=b.get('sampleStatus'):
                p={'Received':'samples.receive','Rejected':'samples.reject','Resampled':'samples.resample','Fresh Sample Requested':'results.reperform'}.get(b.get('sampleStatus'))
                if not p:raise ApiError('Invalid sample transition.')
                self.require(u,s,p)
            if a.get('resultStatus')!=b.get('resultStatus'):
                p={'Approved':'results.approve','Processed':'results.submit','Repeated':'results.repeat','Restored':'results.reperform','Rejected':'results.reject','Fresh Sample':'samples.receive','Fresh Sample Requested':'results.reperform','All':'results.reperform'}.get(b.get('resultStatus'))
                if not p:raise ApiError('Invalid result transition.')
                self.require(u,s,p,'results.authorize' if p=='results.approve' else p)
            if a.get('sampleStatus')==b.get('sampleStatus') and a.get('resultStatus')==b.get('resultStatus'):self.require(u,s,'orders.edit')
        if any(old.get(k)!=new.get(k) for k in ('approvedAt','approvedBy','reportedAt','reportStatus')):self.require(u,s,'results.approve','results.authorize','reports.approve')
        if old.get('status')!=new.get('status'):self.require(u,s,'orders.edit','orders.complete','results.submit','results.approve')
        if old.get('resultStatus')!=new.get('resultStatus'):self.require(u,s,'results.approve','results.authorize')
        if old.get('parameterStates')!=new.get('parameterStates'):
            self.require(u,s,'results.enter','results.edit')
            before=old.get('parameterStates',{});after=new.get('parameterStates',{})
            if any(before.get(code,{}).get('excluded') and not after.get(code,{}).get('excluded') for code in before) and u.get('role')!='Administrator':raise ApiError('Restoring excluded parameters requires an Administrator.')
        if any(old.get(k)!=new.get(k) for k in ('processedAt','resultHistory')):self.require(u,s,'results.enter','results.edit','results.submit')
        if any(old.get(k)!=new.get(k) for k in ('receivedAt','collectedAt','sampleHistory')):self.require(u,s,'samples.collect','samples.receive','samples.reject','samples.resample')
        if old.get('sample')!=new.get('sample'):self.require(u,s,'samples.receive','samples.reject','samples.resample','orders.edit')
    def commit(self,token,requested,revision):
        session,u,rev,s=self.actor(token)
        if revision!=rev or session['revision']!=rev:raise ApiError('Data changed. Reload before saving.')
        validate_state(requested);base=session['base'];merged=copy.deepcopy(s)
        renames=[]
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.db.execute('SELECT revision FROM app_state WHERE id=1').fetchone()[0]!=rev:raise ApiError('Data changed. Reload before saving.')
            for key in set(base)|set(requested):
                before=base.get(key);after=requested.get(key)
                if before==after:continue
                if key in ARRAY_POLICY:
                    idkey,prefix=ARRAY_POLICY[key]; a={str(r[idkey]):r for r in before or []};b={str(r[idkey]):copy.deepcopy(r) for r in after or []};real={str(r[idkey]):r for r in merged.get(key,[])}
                    if key=='users':
                        removed=set(a)-set(b);added=set(b)-set(a)
                        for new_id in list(added):
                            new=b[new_id]
                            if new.get('__nativePassword'):continue
                            candidates=[old_id for old_id in removed if a[old_id].get('name')==new.get('name')]
                            if len(candidates)!=1:continue
                            old_id=candidates[0];self.require(u,s,'users.edit_user_id');self.require(u,s,'users.edit')
                            if new_id in real:raise ApiError('Identifier already exists.')
                            self.user_change(u,s,a[old_id],new)
                            self.db.execute('UPDATE credentials SET id=? WHERE id=?',(new_id,old_id))
                            real.pop(old_id,None);real[new_id]=new;renames.append((old_id,new_id));removed.remove(old_id);a.pop(old_id);b.pop(new_id)
                    for ident in set(a)|set(b):
                        if a.get(ident)==b.get(ident):continue
                        old=a.get(ident);new=b.get(ident)
                        if old is None and ident in real:raise ApiError('Identifier already exists.')
                        if key in ('patients','orders') and old and not self.can_lab(u,s,ident):raise ApiError('Record access denied.')
                        if key in ('inventory','qcEntries'):
                            depts=self.departments(u)
                            if depts is not None and any(str(row.get('department','All')).lower() not in depts|{'all','all departments'} for row in (old,new) if row):raise ApiError('Record access denied.')
                        if key=='users':self.user_change(u,s,old,new)
                        elif key=='orders':self.order_change(u,s,old,new)
                        else:
                            action='add' if old is None else 'delete' if new is None else 'edit'
                            permission=prefix+'.'+action
                            if key=='catalog':permission+='_'+'test'
                            if key in ('reportTemplates','textTemplates'):permission='reports.manage_templates'
                            self.require(u,s,permission)
                            if key=='inventory' and old and new and old.get('stock')!=new.get('stock'):self.require(u,s,'inventory.adjust_stock')
                            if key=='qcEntries' and old and new and old.get('calibrationDue')!=new.get('calibrationDue'):self.require(u,s,'qc.calibration')
                        if new is None:real.pop(ident,None)
                        else:real[ident]=new
                        if key=='users' and new is None:self.db.execute('DELETE FROM credentials WHERE id=?',(ident,))
                    previous_order=[str(row[idkey]) for row in before or []];requested_order=[str(row[idkey]) for row in after or []]
                    if set(previous_order)==set(requested_order) and previous_order!=requested_order:
                        self.require(u,s,'reports.manage_templates' if key in ('reportTemplates','textTemplates') else 'catalog.reorder_tests' if key=='catalog' else prefix+'.edit')
                    merged[key]=[real.pop(ident) for ident in requested_order if ident in real]+list(real.values())
                elif key=='results':
                    for lab in set(before or {})|set(after or {}):
                        av=(before or {}).get(lab,{});bv=(after or {}).get(lab,{})
                        if av==bv:continue
                        if not self.can_lab(u,s,lab):raise ApiError('Record access denied.')
                        self.require(u,s,'results.enter','results.edit')
                        o=next((o for o in s['orders'] if str(o['lab'])==str(lab)),None)
                        if not o:raise ApiError('Order does not exist.')
                        allowed={str(t['code']) for k in o['tests'] for t in self.item_tests(s,k)}
                        for code in set(av)|set(bv):
                            if av.get(code)==bv.get(code):continue
                            if code.split('::')[-1] not in allowed:raise ApiError('Result is not booked for this order.')
                            if any(o.get('testStates',{}).get(k,{}).get('resultStatus')=='Approved' and any(str(t['code'])==code.split('::')[-1] for t in self.item_tests(s,k)) for k in o['tests']):
                                self.require(u,s,'reports.amend');self.require(u,s,'results.approve','results.authorize')
                        if lab in after:merged.setdefault(key,{})[lab]=bv
                        else:merged.setdefault(key,{}).pop(lab,None)
                elif key in ('resultReferences','reportVersions','reportText','resultReportContent'):
                    self.require(u,s,'reports.amend','results.approve','results.authorize') if key=='reportVersions' else self.require(u,s,'results.enter','results.edit')
                    target=merged.setdefault(key,{})
                    for lab in set(before or {})|set(after or {}):
                        av=(before or {}).get(lab);bv=(after or {}).get(lab)
                        if av==bv:continue
                        if not self.can_lab(u,s,lab):raise ApiError('Record access denied.')
                        if key=='reportVersions' and any(x.get('kind')=='Amended' for x in (bv or [])[len(av or []):]):self.require(u,s,'reports.amend')
                        if key=='reportVersions' and av and (not isinstance(bv,list) or bv[:len(av)]!=av):raise ApiError('Archived report versions cannot be changed.')
                        if lab in after:target[lab]=copy.deepcopy(bv)
                        else:target.pop(lab,None)
                elif key=='reportVersionAssets':
                    self.require(u,s,'reports.amend','results.approve','results.authorize')
                    target=merged.setdefault(key,{})
                    for asset in set(before or {})|set(after or {}):
                        av=(before or {}).get(asset);bv=(after or {}).get(asset)
                        if av==bv:continue
                        if asset not in (before or {}) and asset in target:raise ApiError('Report asset identifier already exists.')
                        if asset in (before or {}):self.require(u,s,'reports.amend')
                        if asset in (after or {}):target[asset]=copy.deepcopy(bv)
                        else:target.pop(asset,None)
                elif key=='settings':
                    a=copy.deepcopy(before or {});b=copy.deepcopy(after or {});ab=a.pop('backup',{});bb=b.pop('backup',{})
                    if a!=b:self.require(u,s,'settings.edit')
                    for field in set(ab)|set(bb):
                        if ab.get(field)==bb.get(field):continue
                        self.require(u,s,{'auto':'backups.manage','lastExport':'backups.export','lastRestore':'backups.restore'}.get(field,'settings.edit'))
                    merged[key]=copy.deepcopy(after)
                elif key in GLOBAL_POLICY:
                    self.require(u,s,GLOBAL_POLICY[key]);merged[key]=copy.deepcopy(after)
                elif key in CLIENT_PREFS:merged[key]=copy.deepcopy(after)
                else:
                    # Migration flags/counters can initialize only at bootstrap; unknown writes fail closed.
                    raise ApiError('Unsupported change: '+key)
            validate_state(merged)
            for key in ('patients','orders'):
                oldlabs={str(x['lab']):x for x in base.get(key,[])}
                for row in requested.get(key,[]):
                    if oldlabs.get(str(row['lab']))!=row and not self.can_lab(u,merged,row['lab']):raise ApiError('Record access denied.')
            active_admins=[x for x in merged['users'] if x.get('role')=='Administrator' and x.get('status','Active')=='Active']
            if not active_admins:raise ApiError('Keep at least one active Administrator.')
            self.db.execute('UPDATE app_state SET revision=?,body=? WHERE id=1',(rev+1,json.dumps(merged,ensure_ascii=False)));self.audit(u['id'],'Authorized database update');self.db.execute('COMMIT')
        except Exception:self.db.execute('ROLLBACK');raise
        for old_id,new_id in renames:
            for ss in self.sessions.values():
                if ss['id']==old_id:ss['id']=new_id
        # Reload actor so role/status changes take effect immediately.
        session,u,rev,s=self.actor(token);return self.response(session,u,rev,s)
    def backup_state(self,s):
        out=copy.deepcopy(s)
        for row in out['users']:
            cred=self.db.execute('SELECT hash FROM credentials WHERE id=?',(str(row['id']),)).fetchone();row['password']=cred[0] if cred else ''
        return out
    def snapshot_store(self,row):
        if not isinstance(row,dict) or not re.fullmatch(r'[a-zA-Z0-9-]{1,100}',str(row.get('id',''))):raise ApiError('Invalid snapshot identifier.')
        payload=row.get('payload',{})
        if payload.get('format')!='PLMS_BACKUP' or payload.get('version')!=2:raise ApiError('Unsupported snapshot format.')
        validate_state(payload.get('data'))
        expected=hashlib.sha256(json.dumps({'data':payload['data'],'auditEvents':payload.get('auditEvents')},ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        if payload.get('integrity',{}).get('algorithm')!='SHA-256' or not hmac.compare_digest(str(payload.get('integrity',{}).get('value','')),expected):raise ApiError('Snapshot integrity check failed.')
        for u in payload['data']['users']:
            if u.get('password') and not valid_hash(u['password']):raise ApiError('Snapshot credential format is invalid.')
        if not isinstance(payload.get('auditEvents'),list):raise ApiError('Invalid snapshot audit.')
        serialized=json.dumps(payload,ensure_ascii=False,separators=(',',':'))
        self.db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?,?)',(row['id'],str(row.get('time',payload.get('exportedAt',''))),str(row.get('reason','Migrated'))[:100],len(serialized.encode()),serialized))
        return {k:row[k] for k in ('id','time','reason') if k in row}|{'bytes':len(serialized.encode())}
    def handle(self,r):
        try:return self.dispatch(r)
        except ApiError:
            action=r.get('action','Unknown') if isinstance(r,dict) else 'Unknown'
            if action not in ('login','commit','restore','password','read','audit','backup','bootstrap','logout','ping','status'):action='Unknown'
            session=self.sessions.get(r.get('token')) if isinstance(r,dict) else None
            self.audit(session['id'] if session else 'Unauthenticated','Denied '+action)
            raise
    def dispatch(self,r):
        validate_tree(r);action=r.get('action')
        if action=='status':return {'initialized':self.initialized()}
        if action=='bootstrap':return self.bootstrap(r)
        if action=='login':return self.login(r.get('username',''),r.get('password',''))
        session,u,rev,s=self.actor(r.get('token'))
        if action=='ping':return {'ok':True}
        if action=='read':return self.response(session,u,rev,s)
        if action=='commit':return self.commit(r['token'],r['state'],r['revision'])
        if action=='logout':self.audit(u['id'],'Signed out');self.sessions.pop(r['token'],None);return {'ok':True}
        if action=='password':
            target=str(r.get('userId') or u['id'])
            if target==str(u['id']):
                self.require(u,s,'account.change_own_password');row=self.db.execute('SELECT hash FROM credentials WHERE id=?',(target,)).fetchone()
                if not row or not password_verify(r.get('current',''),row[0]):raise ApiError('Current password is incorrect.')
            else:self.require(u,s,'users.reset_password')
            if not any(str(x['id'])==target for x in s['users']):raise ApiError('Account not found.')
            self.db.execute('INSERT OR REPLACE INTO credentials VALUES(?,?)',(target,password_hash(r['password'])));self.audit(u['id'],'Password changed')
            for tok,ss in list(self.sessions.items()):
                if ss['id']==target and tok!=r['token']:self.sessions.pop(tok,None)
            if target==str(u['id']):session['credential']=self.db.execute('SELECT hash FROM credentials WHERE id=?',(target,)).fetchone()[0]
            return {'ok':True}
        if action=='audit':self.require(u,s,'audit.view');return {'events':[dict(zip(('id','time','actor','action'),row)) for row in self.db.execute('SELECT id,time,actor,action FROM security_audit ORDER BY id DESC LIMIT 1000')]}
        if action=='snapshots':
            self.require(u,s,'backups.view');return {'rows':[dict(zip(('id','time','reason','bytes'),x)) for x in self.db.execute('SELECT id,time,reason,bytes FROM snapshots ORDER BY time DESC')]}
        if action=='snapshot_read':
            self.require(u,s,'backups.export','backups.restore');row=self.db.execute('SELECT id,time,reason,bytes,payload FROM snapshots WHERE id=?',(str(r.get('id','')),)).fetchone()
            if not row:raise ApiError('Snapshot not found.')
            return {'row':dict(zip(('id','time','reason','bytes','payload'),(*row[:4],json.loads(row[4]))))}
        if action=='snapshot_import':
            self.require(u,s,'backups.manage');self.require(u,s,'backups.restore')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                for row in r.get('rows',[]):self.snapshot_store(row)
                self.audit(u['id'],'Recovery snapshots migrated');self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise
            return {'ok':True}
        if action=='snapshot_create':
            self.require(u,s,'backups.manage','backups.restore')
            reason=str(r.get('reason','On demand'))
            if reason=='Automatic' and not self.allowed(u,s,'backups.manage'):raise ApiError('Permission denied: backups.manage')
            data=self.backup_state(s);events=[];stamp=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
            digest=hashlib.sha256(json.dumps({'data':data,'auditEvents':events},ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            payload={'format':'PLMS_BACKUP','version':2,'exportedAt':stamp,'data':data,'auditEvents':events,'integrity':{'algorithm':'SHA-256','value':digest}}
            row=self.snapshot_store({'id':secrets.token_hex(16),'time':stamp,'reason':reason,'payload':payload})
            retain=max(3,min(30,int(s.get('settings',{}).get('backup',{}).get('auto',{}).get('retain',14))))
            for safety,limit in [(False,retain),(True,5)]:
                old=self.db.execute('SELECT id FROM snapshots WHERE (reason=?)=? ORDER BY time DESC LIMIT -1 OFFSET ?',('Before restore',int(safety),limit)).fetchall()
                self.db.executemany('DELETE FROM snapshots WHERE id=?',old)
            self.audit(u['id'],'Recovery snapshot created');return {'row':row}
        if action=='backup':
            self.require(u,s,'backups.export');return {'state':self.backup_state(s),'revision':rev}
        if action=='restore':
            self.require(u,s,'backups.restore')
            if u.get('role')!='Administrator':raise ApiError('A full database restore requires an Administrator.')
            incoming=validate_state(copy.deepcopy(r['state']))
            current_hash=self.db.execute('SELECT hash FROM credentials WHERE id=?',(str(u['id']),)).fetchone()[0]
            admin=next((x for x in incoming['users'] if str(x['id'])==str(u['id'])),None)
            if admin is None:admin=copy.deepcopy(u);incoming['users'].append(admin)
            admin.update(role='Administrator',status='Active',department='All',password=current_hash)
            self.db.execute('BEGIN IMMEDIATE')
            try:
                if self.db.execute('SELECT revision FROM app_state WHERE id=1').fetchone()[0]!=rev:raise ApiError('Data changed. Reload before restoring.')
                self.db.execute('DELETE FROM credentials')
                for row in incoming['users']:
                    cred=row.pop('password','');row['bypassLogin']=False
                    if cred and not valid_hash(cred):raise ApiError('Backup has an invalid credential format.')
                    if cred and not password_verify('123',cred):self.db.execute('INSERT INTO credentials VALUES(?,?)',(str(row['id']),cred))
                    else:row['status']='Inactive'
                if not any(str(x['id'])==str(u['id']) and x.get('role')=='Administrator' and x.get('status','Active')=='Active' for x in incoming['users']):raise ApiError('Backup must retain the current Administrator.')
                if not self.db.execute('SELECT 1 FROM credentials WHERE id=?',(str(u['id']),)).fetchone():raise ApiError('Backup must retain an Administrator password.')
                self.db.execute('UPDATE app_state SET revision=?,body=? WHERE id=1',(rev+1,json.dumps(incoming,ensure_ascii=False)));self.audit(u['id'],'Backup restored');self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise
            self.sessions={r['token']:session};return self.response(session,u,rev+1,incoming)
        raise ApiError('Unknown action.')

def main():
    if len(sys.argv)!=2:raise SystemExit('PLMS backend requires its application-data database path.')
    backend=Backend(sys.argv[1])
    while True:
        line=sys.stdin.buffer.readline(MAX_BYTES+1)
        if not line:break
        if len(line)>MAX_BYTES:break
        try:
            req=json.loads(line);result={'ok':True,'data':backend.handle(req)}
        except ApiError as e:result={'ok':False,'error':str(e)}
        except Exception:result={'ok':False,'error':'The database operation could not be completed.'}
        sys.stdout.write(json.dumps(result,ensure_ascii=False)+'\n');sys.stdout.flush()
if __name__=='__main__':main()
