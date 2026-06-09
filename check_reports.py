"""Final check - handle false positives and unicode"""
import sys
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'
conn = db.get_db()

real_issues = []

for r in conn.execute("SELECT id, research_topic, content FROM reports ORDER BY id").fetchall():
    rid = r['id']
    content = r['content']

    # 1. Check truncation (very short content)
    if len(content) < 3000:
        real_issues.append((rid, 'TRUNCATED', f'Only {len(content)} chars'))

    # 2. Check unmatched \[ and \] (LaTeX display math)
    bo = content.count('\\[')
    bc = content.count('\\]')
    if bo != bc:
        real_issues.append((rid, 'BRACKET_MISMATCH', f'open={bo} close={bc}'))

    # 3. Check unmatched \( and \) (LaTeX inline math)
    po = content.count('\\(')
    pc = content.count('\\)')
    if po != pc:
        real_issues.append((rid, 'PAREN_MISMATCH', f'open={po} close={pc}'))

    # 4. Check unpaired $ that look like LaTeX math (not currency)
    if content.count('$') % 2 != 0:
        positions = [i for i, c in enumerate(content) if c == chr(36)]
        for pos in positions:
            before = content[max(0, pos-200):pos]
            after = content[pos+1:pos+201]
            # Only flag if the context looks like math (contains LaTeX commands)
            has_math_nearby = any(
                cmd in before[-100:] + after[:100]
                for cmd in ['\\', '_', '^', '{', '}']
            )
            if has_math_nearby:
                ctx = content[max(0,pos-30):min(len(content),pos+30)]
                ctx_clean = ctx.encode('ascii', errors='replace').decode('ascii')
                real_issues.append((rid, 'UNPAIRED_MATH_DOLLAR', f'...{ctx_clean}...'))
                break  # One per report

print(f"Reports checked: 150")
print(f"Issues found: {len(real_issues)}")
print()

if not real_issues:
    print("RESULT: All 150 reports pass. No genuine issues found.")
else:
    for rid, itype, detail in real_issues:
        print(f"  #{rid:3d} [{itype}] {detail[:120]}")

conn.close()
