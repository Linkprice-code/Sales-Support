"""Fetch Naver Shopping Insight official relative CLICK indices, not sales/revenue.
Runs only after NAVER_DATALAB_CLIENT_ID and NAVER_DATALAB_CLIENT_SECRET are configured.
"""
from __future__ import annotations
import datetime,json,os,pathlib,time,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/'data/categories.json';DST=ROOT/'data/market.json'
ENDPOINT='https://openapi.naver.com/v1/datalab/shopping/categories'
KST=datetime.timezone(datetime.timedelta(hours=9))
def main():
 cid=os.getenv('NAVER_DATALAB_CLIENT_ID','').strip();secret=os.getenv('NAVER_DATALAB_CLIENT_SECRET','').strip()
 if not(cid and secret):print('[SKIP] Naver DataLab credentials not configured; preserving prior market data');return
 cat=json.loads(SRC.read_text('utf8'));allrows=cat['categories'];roots=[x for x in allrows if x['level']==1 and x['id'].isdigit()]
 medium=[x for x in allrows if x['level']==2 and x['id'].isdigit()]
 focus=[]
 ff=ROOT/'data/focus_categories.txt'
 if ff.exists():focus=[s.strip() for s in ff.read_text('utf8').splitlines() if s.strip() and not s.startswith('#')]
 max_items=max(12,min(700,int(os.getenv('MAX_TREND_CATEGORIES','180'))))
 wanted=roots+[x for x in medium if x['id'] in focus or x['name'] in focus]+[x for x in medium if x['id'] not in focus and x['name'] not in focus]
 unique={x['id']:x for x in wanted};rows=list(unique.values())[:max_items]
 now=datetime.datetime.now(KST);last=(now-datetime.timedelta(days=1)).date();start=last-datetime.timedelta(days=55)
 old=json.loads(DST.read_text('utf8')) if DST.exists() else {'items':{}};items=old.get('items',{});errors=0;success=0
 for k in range(0,len(rows),3):
  chunk=rows[k:k+3]
  body={'startDate':start.isoformat(),'endDate':last.isoformat(),'timeUnit':'week','category':[{'name':r['name'],'param':[r['id']]} for r in chunk]}
  req=urllib.request.Request(ENDPOINT,data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','X-Naver-Client-Id':cid,'X-Naver-Client-Secret':secret},method='POST')
  try:
   with urllib.request.urlopen(req,timeout=45) as res:reply=json.load(res)
   for block in reply.get('results',[]):
    key=block.get('category')
    if isinstance(key,list):key=key[0] if key else None
    if not key:continue
    values=[{'period':v['period'],'ratio':round(float(v['ratio']),5)} for v in block.get('data',[]) if v.get('period') and v.get('ratio') is not None]
    if values:
     items[str(key)]={'data':values,'name':block.get('title',''),'startDate':start.isoformat(),'endDate':last.isoformat(),'source':'Naver Shopping Insight / official API'};success+=1
  except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError,KeyError) as e:
   print(f'[WARN] DataLab batch {k//3+1} failed: {e}');errors+=1
  time.sleep(.09)
 if success:
  out={'metadata':{'source':'naver_shopping_insight_api','updated':now.isoformat(),'requested':len(rows),'updated_records':success,'batch_errors':errors,'metric':'Relative shopping click index (NOT orders/sales)', 'window':{'start':start.isoformat(),'end':last.isoformat()}},'items':items}
  temp=DST.with_suffix('.tmp');temp.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');temp.replace(DST)
 print('[DONE] market records updated:',success,'errors:',errors,'requested:',len(rows))
if __name__=='__main__':main()
