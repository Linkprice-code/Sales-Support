import pathlib
import re
import unittest
from html.parser import HTMLParser

ROOT=pathlib.Path(__file__).resolve().parents[1]
class InspectHTML(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.styles=0;self.scripts=0;self.external_css=[];self.external_js=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='style':self.styles+=1
        if tag=='script':
            self.scripts+=1
            if a.get('src'):self.external_js.append(a['src'])
        if tag=='link' and a.get('rel')=='stylesheet':self.external_css.append(a.get('href'))

class TestUI(unittest.TestCase):
    def test_single_file_and_tabs(self):
        text=(ROOT/'index.html').read_text(encoding='utf-8')
        p=InspectHTML();p.feed(text)
        self.assertEqual(len(p.ids),len(set(p.ids)))
        for id in ['rootFilters','categoryResults','newsList','newsCoverage','signalPanel','saPlans','gfaPlans','noteTitle','copyResearchPrompt']:
            self.assertIn(id,p.ids)
        self.assertGreaterEqual(p.styles,1)
        self.assertGreaterEqual(p.scripts,2)
        self.assertFalse(p.external_css)
        self.assertFalse(p.external_js)
        self.assertIn('data/news.json',text)
        self.assertNotIn('NAVER_HUB_CLIENT_ID',text)
        self.assertNotIn('OPENAI_API_KEY',text)

if __name__=='__main__':unittest.main()
