import re
from pathlib import Path

h = Path("demo/01_impact_report.html").read_text(encoding="utf-8")
bare = re.findall(r'mc-name">((?:OI|PI|OD|FP|OG|PD|FF)\d+)<', h)
print("bare-code card titles remaining:", bare)
# sample a few resolved names for sanity
named = re.findall(r'mc-name">([^<]+)<', h)
print("total metric cards:", len(named))
print("first 8 titles:", named[:8])
