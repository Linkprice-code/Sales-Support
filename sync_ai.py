"""OPTIONAL: Generate a small, source-aware summary using OpenAI Responses API.
Only categories selected in focus_categories.txt or official top-level categories are processed.
Do not call this unless API billing is enabled. No secret is ever added to web files.
"""
from __future__ import annotations
import datetime,json,os,pathlib,re,urllib.request,urllib.error,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data/ai_insights.json'
KST=datetime.timezone(datetime.timedelta(hours=9))
def post_json(url,body,token):
 req=urllib.request.Request(url,data=json.dumps(body,ensure_ascii=False).encode('utf8'),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},method='POST')
 with urllib.request.urlopen(req,timeout=125) as f:return json.load(f)
def extract(response):
 if isinstance(response.get('output_text'),str):return response['output_text']
 texts=[]
 for o in response.get('output',[]):
  for x in o.get('content',[]):
   if x.get('type')=='output_text':texts.append(x.get('text',''))
 return '\n'.join(texts)
def main():
 key=os.getenv('OPENAI_API_KEY','').strip()
 if not key:print('[SKIP] OPENAI_API_KEY missing; preserving existing analysis');return
 cats=json.loads((ROOT/'data/categories.json').read_text('utf8'))['categories'];market=json.loads((ROOT/'data/market.json').read_text('utf8'))['items'];focus=[x.strip() for x in (ROOT/'data/focus_categories.txt').read_text('utf8').splitlines() if x.strip() and not x.lstrip().startswith('#')]
 rows=[x for x in cats if x['level']==1 or (x['level']==2 and (x['id'] in focus or x['name'] in focus))]
 maxcalls=max(1,min(30,int(os.getenv('MAX_AI_CATEGORIES','12'))));rows=rows[:maxcalls];existing=json.loads(OUT.read_text('utf8')) if OUT.exists() else {'items':{}};items=existing.get('items',{})
 model=os.getenv('OPENAI_MODEL','gpt-6-luna')
 has_web=os.getenv('OPENAI_WEB_SEARCH','0')=='1'
 count=0
 for r in rows:
  series=market.get(r['id'],{}).get('data',[])
  prompt=f'''너는 한국 퍼포먼스 마케팅 실무 분석가이다. 날짜 {datetime.datetime.now(KST).date()}, 네이버쇼핑 카테고리 {r['name']}.
증거 데이터: {json.dumps(series[-8:],ensure_ascii=False)}.
목적: 광고 대행사 콜영업 전 시장 리서치. 네이버 SA / GFA 중심.
사실과 전략적 가설을 명확히 구분해라. 수치가 없는 경우 성장률·검색량·매출액·시장점유율을 절대 만들어내지 마라.
최신 뉴스는 웹 검색 도구를 사용할 때만 출처 URL을 포함하라. 검증되지 않으면 정량 주장 없이 가설·확인 포인트로 표현하라.
중요: 불확실한 업계 일반론을 단정하지 마라. 카탈로그 판매는 자격과 행동 데이터 연동이 가능한 경우에만 권고.
순수 JSON 객체만 출력한다. 키 summary(문장 배열 1~2개), positive(문장 배열 2개), negative(문장 배열 2개), actions(문장 배열 3개), sources(URL 문자열 배열 0~3개).'''
  req={'model':model,'input':prompt,'max_output_tokens':950,'store':False}
  if has_web:req['tools']=[{'type':'web_search','search_context_size':'low'}]
  try:
   result=post_json('https://api.openai.com/v1/responses',req,key)
   raw=extract(result).strip();match=re.search(r'\{[\s\S]*\}',raw)
   if not match:raise ValueError('no JSON in response')
   obj=json.loads(match.group());assert all(k in obj for k in ('summary','positive','negative','actions','sources'))
   obj['source_type']='AI generated advice; verify before use';obj['generated_at']=datetime.datetime.now(KST).isoformat();obj['model']=model
   items[r['id']]=obj;count+=1;print('[OK] AI analysis',r['name'])
  except Exception as e:print('[WARN] AI analysis failed:',r['name'],str(e)[:240])
  time.sleep(.5)
 if count:
  out={'metadata':{'source':'openai_responses_api','updated':datetime.datetime.now(KST).isoformat(),'model':model,'with_web_search':has_web,'updated_records':count},'items':items}
  temp=OUT.with_suffix('.tmp');temp.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');temp.replace(OUT)
 print('[DONE] AI analyses:',count)
if __name__=='__main__':main()
