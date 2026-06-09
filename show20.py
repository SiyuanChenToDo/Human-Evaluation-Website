import sys
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'
r = db.get_report(20)
c = r['content']

# Write to file
with open('report20_content.txt', 'w', encoding='utf-8') as f:
    f.write(c)

print(f"Written {len(c)} chars to report20_content.txt")

# Show sections containing tables and formulas
d = chr(36)
lines = c.split('\n')
for i, line in enumerate(lines):
    line_stripped = line.strip()
    # Show lines with table markers, math, or special formatting
    if any(x in line_stripped for x in ['|', d, '\\', 'hyperparam', 'metric', 'baseline', '##', '**']):
        if len(line_stripped) < 200:
            # Replace non-printable chars for terminal output
            clean = line_stripped.encode('ascii', errors='replace').decode('ascii')
            print(f"[{i:4d}] {clean[:180]}")
