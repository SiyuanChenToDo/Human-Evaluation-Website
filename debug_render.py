import sys, re
sys.path.insert(0, '.')
import db; db.DB_PATH = 'eval.db'
r = db.get_report(66)
c = r['content']

idx = c.find('PCC-guided dynamic')
if idx < 0:
    idx = c.find('Semantic Role')
section = c[max(0,idx-100):idx+400]

from app import render_markdown
html = render_markdown(section)

d = chr(36)
with open('debug_render.txt', 'w', encoding='utf-8') as f:
    f.write("=== SOURCE ===\n")
    f.write(section)
    f.write("\n\n=== HTML ===\n")
    f.write(html)
    f.write("\n\nSource has dollars: " + str(section.count(d)) + "\n")
    f.write("HTML has dollars: " + str(html.count(d)) + "\n")
    f.write("HTML has <sub>: " + str(html.count('<sub>')) + "\n")
    f.write("Source has alpha_{ij}: " + str('alpha_{ij}' in section) + "\n")
    f.write("HTML has alpha_{ij}: " + str('alpha_{ij}' in html) + "\n")
    f.write("HTML has alpha<sub>: " + str('alpha<sub>' in html) + "\n")

print("Done")
