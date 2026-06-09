import sys, re
sys.path.insert(0, '.')
import db; db.DB_PATH = 'eval.db'
r = db.get_report(20)
c = r['content']

idx = c.find('Framework Architecture')
section = c[idx:idx+800]

from app import render_markdown
html = render_markdown(section)

with open('test_source.txt', 'w', encoding='utf-8') as f:
    f.write(section)
with open('test_html.txt', 'w', encoding='utf-8') as f:
    f.write(html)

u_count_src = section.count('_')
u_count_html = html.count('_')
ub_count_src = section.count('_{')
ub_count_html = html.count('_{')
print("Source underscores:", u_count_src)
print("HTML underscores:", u_count_html)
print("Source _{}: ", ub_count_src)
print("HTML _{}: ", ub_count_html)
print("Done")
