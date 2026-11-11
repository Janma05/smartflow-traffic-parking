import json, os, time, uuid, smtplib
from pathlib import Path
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Optional, Literal
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'/'demo_data.json'
PARKING_THRESHOLD=int(os.getenv('PARKING_FULL_THRESHOLD','90'))
CONGESTION_THRESHOLD=int(os.getenv('SEVERE_CONGESTION_THRESHOLD','80'))
STALE_SECONDS=int(os.getenv('DEVICE_STALE_SECONDS','120'))
DEMO=os.getenv('TRAFFIQ_DEMO_MODE','true').lower()=='true'
app=FastAPI(title='TraffiQ / SmartFlow - Module 7 Alerts & Notifications',version='1.0.0',description='Parking, congestion, camera/sensor alerts, dashboard APIs, optional SMTP and FCM.')
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:3000','http://127.0.0.1:3000','http://localhost:5173','http://127.0.0.1:5173'],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
def now(): return datetime.now(timezone.utc).isoformat()
def read():
    with DATA.open(encoding='utf-8') as f: return json.load(f)
def save(d):
    with DATA.open('w',encoding='utf-8') as f: json.dump(d,f,indent=2)
def alert(d,kind,severity,title,message,sid,sname,meta=None):
    for a in d['alerts']:
        if a['source_id']==sid and a['alert_type']==kind and a['status']=='active':
            a.update(message=message,updated_at=now(),metadata=meta or a.get('metadata',{})); return a
    a={'alert_id':str(uuid.uuid4()),'alert_type':kind,'severity':severity,'title':title,'message':message,'source_id':sid,'source_name':sname,'status':'active','created_at':now(),'updated_at':now(),'acknowledged_at':None,'metadata':meta or {}}
    d['alerts'].insert(0,a); return a
def check_parking(d):
    out=[]
    for p in d['parking_facilities']:
        total,occ=int(p['total_spaces']),int(p['occupied_spaces']); pct=occ/total*100 if total else 0
        p['occupancy_percent']=round(pct,1)
        if pct>=PARKING_THRESHOLD:
            out.append(alert(d,'parking_nearly_full','critical' if pct>=97 else 'warning',f"Parking nearly full: {p['name']}",f"{p['name']} is {pct:.1f}% occupied ({occ}/{total}).",p['parking_id'],p['name'],{'occupancy_percent':round(pct,1),'available_spaces':max(total-occ,0),'threshold_percent':PARKING_THRESHOLD,'location':p.get('location')}))
    return out
def check_roads(d):
    out=[]
    for r in d['roads']:
        score=int(r.get('congestion_score',0)); level=str(r.get('congestion_level','')).lower()
        if score>=CONGESTION_THRESHOLD or level in ('severe','critical'):
            out.append(alert(d,'severe_congestion','critical' if score>=90 or level in ('severe','critical') else 'warning',f"Severe congestion: {r['road_name']}",f"{r['road_name']} has {level} congestion (score {score}/100).",r['road_id'],r['road_name'],{'congestion_score':score,'congestion_level':level,'average_speed_kmph':r.get('average_speed_kmph')}))
    return out
def check_devices(d):
    out=[]; current=time.time()
    for group,label,kind in [('cameras','camera','camera_unavailable'),('sensors','sensor','sensor_failure')]:
        for x in d[group]:
            last=x.get('last_seen_epoch'); offline=not x.get('is_online',False); stale=last is None or current-float(last)>STALE_SECONDS
            if offline or stale:
                state='offline' if offline else 'stale'
                out.append(alert(d,kind,'critical' if offline else 'warning',f"{label.title()} unavailable: {x['name']}",f"{x['name']} is {state}. Last update: {x.get('last_seen','unknown')}.",x['device_id'],x['name'],{'device_type':label,'device_status':state,'last_seen':x.get('last_seen'),'stale_after_seconds':STALE_SECONDS}))
    return out
def monitor(d):
    found=check_parking(d)+check_roads(d)+check_devices(d); d['last_monitoring_run']=now(); save(d)
    return {'monitoring_run_at':d['last_monitoring_run'],'alerts_created_or_updated':len(found),'alerts':found,'demo_data':DEMO,'thresholds':{'parking_percent':PARKING_THRESHOLD,'congestion_score':CONGESTION_THRESHOLD,'device_stale_seconds':STALE_SECONDS}}
class ParkingUpdate(BaseModel): occupied_spaces:int=Field(ge=0)
class RoadUpdate(BaseModel): congestion_score:int=Field(ge=0,le=100); congestion_level:Literal['low','medium','high','severe','critical']
class Heartbeat(BaseModel): is_online:bool=True; status_message:Optional[str]=None
class Ack(BaseModel): acknowledged_by:str=Field(min_length=1,max_length=120)
class Notification(BaseModel): channel:Literal['email','push']; recipient:str=Field(min_length=1); title:str=Field(min_length=1,max_length=200); message:str=Field(min_length=1,max_length=2000)
@app.get('/')
def home(): return {'project':'SmartFlow / TraffiQ','module':7,'name':'Alerts and Notifications','status':'running','mode':'demo_sample_data' if DEMO else 'configured','docs':'/docs','health':'/health'}
@app.get('/health')
def health(): return {'status':'ok','module':7,'mode':'demo_sample_data' if DEMO else 'configured'}
@app.get('/favicon.ico',include_in_schema=False)
def favicon(): return Response(status_code=204)
@app.get('/api/v1/alerts')
def list_alerts(status:Optional[Literal['active','acknowledged','resolved']]=None,severity:Optional[Literal['info','warning','critical']]=None,alert_type:Optional[str]=None,limit:int=Query(100,ge=1,le=500)):
    items=read()['alerts']
    if status: items=[a for a in items if a['status']==status]
    if severity: items=[a for a in items if a['severity']==severity]
    if alert_type: items=[a for a in items if a['alert_type']==alert_type]
    return {'count':len(items[:limit]),'alerts':items[:limit]}
@app.get('/api/v1/alerts/summary')
def summary():
    items=read()['alerts']; return {'total':len(items),'active':sum(a['status']=='active' for a in items),'acknowledged':sum(a['status']=='acknowledged' for a in items),'critical':sum(a['severity']=='critical' and a['status']=='active' for a in items),'warning':sum(a['severity']=='warning' and a['status']=='active' for a in items),'by_type':{k:sum(a['alert_type']==k and a['status']=='active' for a in items) for k in sorted({a['alert_type'] for a in items})}}
@app.post('/api/v1/monitoring/run')
def run_monitoring(): return monitor(read())
@app.get('/api/v1/parking')
def parking():
    d=read(); result=[]
    for p in d['parking_facilities']:
        p=dict(p); p['available_spaces']=max(p['total_spaces']-p['occupied_spaces'],0); p['occupancy_percent']=round(p['occupied_spaces']/p['total_spaces']*100,1) if p['total_spaces'] else 0; result.append(p)
    return {'parking_facilities':result}
@app.put('/api/v1/parking/{parking_id}')
def update_parking(parking_id:str,body:ParkingUpdate):
    d=read(); p=next((x for x in d['parking_facilities'] if x['parking_id']==parking_id),None)
    if not p: raise HTTPException(404,'Parking facility not found')
    if body.occupied_spaces>p['total_spaces']: raise HTTPException(422,'Occupied spaces cannot exceed total spaces')
    p.update(occupied_spaces=body.occupied_spaces,updated_at=now()); check_parking(d); save(d); return {'message':'Parking updated','parking':p}
@app.get('/api/v1/roads')
def roads(): return {'roads':read()['roads']}
@app.put('/api/v1/roads/{road_id}')
def update_road(road_id:str,body:RoadUpdate):
    d=read(); r=next((x for x in d['roads'] if x['road_id']==road_id),None)
    if not r: raise HTTPException(404,'Road not found')
    r.update(congestion_score=body.congestion_score,congestion_level=body.congestion_level,observed_at=now()); check_roads(d); save(d); return {'message':'Road updated','road':r}
@app.get('/api/v1/devices')
def devices():
    d=read(); return {'cameras':d['cameras'],'sensors':d['sensors']}
@app.post('/api/v1/devices/{device_id}/heartbeat')
def heartbeat(device_id:str,body:Heartbeat):
    d=read(); device=None
    for group in ('cameras','sensors'):
        device=next((x for x in d[group] if x['device_id']==device_id),None)
        if device: break
    if not device: raise HTTPException(404,'Camera or sensor not found')
    device.update(is_online=body.is_online,last_seen_epoch=time.time(),last_seen=now(),status_message=body.status_message); save(d); return {'message':'Heartbeat recorded','device':device}
@app.post('/api/v1/alerts/{alert_id}/acknowledge')
def acknowledge(alert_id:str,body:Ack):
    d=read(); a=next((x for x in d['alerts'] if x['alert_id']==alert_id),None)
    if not a: raise HTTPException(404,'Alert not found')
    if a['status']=='resolved': raise HTTPException(409,'Resolved alert cannot be acknowledged')
    a.update(status='acknowledged',acknowledged_by=body.acknowledged_by,acknowledged_at=now(),updated_at=now()); save(d); return {'message':'Alert acknowledged','alert':a}
@app.post('/api/v1/alerts/{alert_id}/resolve')
def resolve(alert_id:str):
    d=read(); a=next((x for x in d['alerts'] if x['alert_id']==alert_id),None)
    if not a: raise HTTPException(404,'Alert not found')
    a.update(status='resolved',resolved_at=now(),updated_at=now()); save(d); return {'message':'Alert resolved','alert':a}
def email_send(to,subject,body):
    host=os.getenv('SMTP_HOST'); user=os.getenv('SMTP_USERNAME'); password=os.getenv('SMTP_PASSWORD'); sender=os.getenv('SMTP_FROM',user or '')
    if not all([host,user,password,sender]): raise HTTPException(503,'SMTP not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM.')
    msg=EmailMessage(); msg['Subject']=subject; msg['From']=sender; msg['To']=to; msg.set_content(body)
    try:
        with smtplib.SMTP(host,int(os.getenv('SMTP_PORT','587')),timeout=15) as s: s.starttls(); s.login(user,password); s.send_message(msg)
    except (smtplib.SMTPException,OSError) as e: raise HTTPException(502,f'Email delivery failed ({type(e).__name__})') from e
    return {'channel':'email','status':'sent','recipient':to}
def fcm_send(token,title,body):
    try: import firebase_admin; from firebase_admin import credentials,messaging
    except ImportError as e: raise HTTPException(503,'FCM requires optional firebase-admin package') from e
    if not firebase_admin._apps:
        path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not path or not Path(path).exists(): raise HTTPException(503,'Set GOOGLE_APPLICATION_CREDENTIALS to Firebase service-account JSON')
        firebase_admin.initialize_app(credentials.Certificate(path))
    try: mid=messaging.send(messaging.Message(notification=messaging.Notification(title=title,body=body),token=token))
    except Exception as e: raise HTTPException(502,f'FCM delivery failed ({type(e).__name__})') from e
    return {'channel':'push','status':'sent','message_id':mid}
@app.post('/api/v1/notifications/send')
def send_notification(body:Notification): return email_send(body.recipient,body.title,body.message) if body.channel=='email' else fcm_send(body.recipient,body.title,body.message)
@app.get('/api/v1/config')
def config(): return {'parking_threshold_percent':PARKING_THRESHOLD,'congestion_threshold':CONGESTION_THRESHOLD,'device_stale_seconds':STALE_SECONDS,'demo_mode':DEMO,'email_configured':bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_USERNAME')),'push_configured':bool(os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))}
