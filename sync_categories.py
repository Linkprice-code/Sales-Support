"""Fetch the COMPLETE current Naver Commerce category catalog via authorized official API.
This script NEVER crawls private HTML or exposes credentials in public files.
"""
from __future__ import annotations
import os,json,base64,time,pathlib,datetime,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data/categories.json'
API='https://api.commerce.naver.com/external'

def request(url,body=None,headers=None):
    data=urllib.parse.urlencode(body).encode('utf-8') if body is not None else None
    req=urllib.request.Request(url,data=data,headers=headers or {},method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(req,timeout=50) as f: return json.load(f)

def main():
    cid=os.getenv('NAVER_COMMERCE_CLIENT_ID')
    secret=os.getenv('NAVER_COMMERCE_CLIENT_SECRET')
    if not cid or not secret:
        print('[SKIP] NAVER_COMMERCE_CLIENT_ID/SECRET not configured; retaining starter catalog')
        return
    try:
        import bcrypt
    except ImportError as e: raise RuntimeError('pip install bcrypt before using official commerce API') from e
    now=str(int(time.time()*1000))
    signature=base64.b64encode(bcrypt.hashpw((cid+'_'+now).encode(),secret.encode())).decode()
    token=request(API+'/v1/oauth2/token',{'client_id':cid,'client_secret_sign':signature,'timestamp':now,'grant_type':'client_credentials','type':'SELF'},{'Accept':'application/json'})
    access=token.get('access_token')
    if not access:raise RuntimeError('OAuth response did not contain access_token')
    result=request(API+'/v1/categories',headers={'Accept':'application/json;charset=UTF-8','Authorization':'Bearer '+access})
    if not isinstance(result,list) or len(result)<100:
        raise RuntimeError('Category API returned unexpected response/insufficient rows; nothing overwritten')
    path_to_id={};top_order=[];medium_order=[]
    for r in result:
        parts=[s.strip() for s in str(r.get('wholeCategoryName','')).split('>') if s.strip()]
        if not parts:continue
        key='>'.join(parts)
        if len(parts)<=2:path_to_id[key]=str(r.get('id',''))
        if len(parts)==1 and key not in top_order:top_order.append(key)
        if len(parts)>=2 and '>'.join(parts[:2]) not in medium_order:medium_order.append('>'.join(parts[:2]))
    if len(top_order)<9 or len(medium_order)<70:
        raise RuntimeError(f'Category completeness check failed: roots={len(top_order)} / medium={len(medium_order)}')
    missing=[path for path in medium_order if path not in path_to_id]
    if missing:raise RuntimeError(f'{len(missing)} medium categories have no official ID; preserving old catalog')
    rows=[]
    for major in top_order:
        rid=path_to_id.get(major)
        if not rid:continue
        rows.append({'id':rid,'name':major,'parent_id':None,'level':1,'source':'official'})
        for pair in medium_order:
            main,sub=pair.split('>',1)
            if main!=major:continue
            rows.append({'id':path_to_id[pair],'name':sub,'parent_id':rid,'level':2,'source':'official'})
    out={'metadata':{'schema':1,'source':'naver_commerce_api','verified_full_catalog':True,'updated':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),'records_in_official_response':len(result),'scope':'Full published official category list, displaying levels 1 and 2'},'categories':rows}
    temp=OUT.with_suffix('.json.tmp');temp.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(OUT)
    print(f'[OK] saved {len(rows)} category records; {len(top_order)} roots, {len(medium_order)} medium; official API returned {len(result)} rows')
if __name__=='__main__':main()
