import datetime as dt
import importlib.util
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('collector',ROOT/'scripts'/'collect_public_news.py')
collector=importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)
RSS='''<?xml version="1.0"?><rss version="2.0"><channel><title>sample</title>
<item><title>세탁기 신제품 출시 시장 주목</title><link>https://example.com/news/1</link><pubDate>Tue, 27 Oct 2026 12:00:00 +0900</pubDate></item>
<item><title>냉장고 가격 인상</title><link>https://example.com/news/2</link><pubDate>Tue, 27 Oct 2026 12:00:00 +0900</pubDate></item>
</channel></rss>'''.encode('utf-8')

class TestRSS(unittest.TestCase):
    def test_parse_headlines_links_only(self):
        news=collector.parse_feed(RSS,'테스트 언론')
        self.assertEqual(len(news),2)
        self.assertEqual(news[0]['title'],'세탁기 신제품 출시 시장 주목')
        self.assertNotIn('body',news[0])
    def test_category_match(self):
        self.assertTrue(collector.match_category('세탁기 신제품 출시',{'name':'세탁기'},'디지털/가전'))
        self.assertFalse(collector.match_category('냉장고 신제품 출시',{'name':'세탁기'},'디지털/가전'))
    def test_all_starter_categories_selected_by_rotation(self):
        import json
        with (ROOT/'data'/'categories.json').open(encoding='utf-8') as file:
            cats=json.load(file)['categories']
        mid={str(c['id']) for c in cats if c['level']==2}
        cover=set()
        for k in range(8):
            day=dt.date(2026,10,28)+dt.timedelta(days=k)
            cover.update(str(c['id']) for c in collector.select_categories(cats,set(),38,day))
        self.assertEqual(cover.intersection(mid),mid)
    def test_url_safe(self):
        self.assertEqual(collector.safe_https('javascript:alert(1)'),'')
        self.assertEqual(collector.safe_https('https://example.com/x'),'https://example.com/x')

if __name__=='__main__':unittest.main()
