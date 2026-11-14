import argparse,json,pathlib
from official_ir import analyze_official,SOURCES
p=argparse.ArgumentParser(description='CompanyScope official IR proof of concept')
p.add_argument('company',choices=sorted(SOURCES))
p.add_argument('--fixture',action='store_true',help='Use short, source-transcribed test excerpt rather than live download')
a=p.parse_args()
fixture=json.loads((pathlib.Path(__file__).parent/'fixtures'/'official_extracts.json').read_text())[a.company] if a.fixture else None
print(json.dumps(analyze_official(a.company,fixture),indent=2,ensure_ascii=False))
