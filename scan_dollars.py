"""Scan all 150 reports for non-LaTeX dollar signs"""
import sys, re
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'
conn = db.get_db()

d = chr(36)
total_non_math = 0

for r in conn.execute('SELECT id, research_topic, content FROM reports ORDER BY id').fetchall():
    rid = r['id']
    c = r['content']

    # Find dollar signs followed by digits (likely currency)
    for m in re.finditer(r'\$\d', c):
        pos = m.start()
        # Get a bit more context
        end = min(len(c), pos + 30)
        snippet = c[pos:end].split('\n')[0][:60]
        # Check if it looks like currency (comma/period in the number part)
        after_dollar = c[pos+1:pos+20]
        is_currency = bool(re.match(r'\d{1,3}(?:,\d{3})', after_dollar))
        is_math = any(x in c[max(0,pos-50):min(len(c),pos+80)] for x in ['\\', '_{', '^{', '}$', '$ '])

        if is_currency or (not is_math):
            total_non_math += 1
            if total_non_math <= 20:  # Show first 20 only
                print(f"  #{rid:3d} pos {pos}: {snippet}")

conn.close()
print(f"\nTotal non-math dollar signs found: {total_non_math}")
