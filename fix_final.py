import sys
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'
d = chr(36)
conn = db.get_db()

# Fix #95: add closing $ for $[Q; D_1]
r = conn.execute('SELECT content FROM reports WHERE id=95').fetchone()
c = r['content']
pos = c.find('D_1]')
if pos > 0:
    before_closing = c[pos+4:pos+10]
    print(f"#95: After 'D_1]': {repr(before_closing)}")
    # Add closing $ right after D_1]
    c = c[:pos+4] + d + c[pos+4:]
    conn.execute('UPDATE reports SET content=? WHERE id=95', (c,))
    conn.commit()
    print(f"  Fixed: added closing $")
    # Verify
    r2 = conn.execute('SELECT content FROM reports WHERE id=95').fetchone()
    print(f"  Dollar count after: {r2['content'].count(d)} (should be even)")

# Fix #98: add closing $ for $\boldsymbol{\alpha}
r = conn.execute('SELECT content FROM reports WHERE id=98').fetchone()
c = r['content']
pos = c.rfind('boldsymbol')
if pos > 0:
    # The formula is $\boldsymbol{\alpha} — need closing $
    end_pos = c.find('}', pos) + 1  # end of \boldsymbol{\alpha}
    print(f"\n#98: After formula: {repr(c[end_pos:end_pos+10])}")
    c = c[:end_pos] + d + c[end_pos:]
    conn.execute('UPDATE reports SET content=? WHERE id=98', (c,))
    conn.commit()
    print(f"  Fixed: added closing $")
    r2 = conn.execute('SELECT content FROM reports WHERE id=98').fetchone()
    print(f"  Dollar count after: {r2['content'].count(d)} (should be even)")

# Final verification: all reports
print("\n=== Final verification ===")
issues = 0
for r in conn.execute('SELECT id FROM reports ORDER BY id').fetchall():
    r2 = conn.execute('SELECT content FROM reports WHERE id=?', (r['id'],)).fetchone()
    dc = r2['content'].count(d)
    bo = r2['content'].count('\\[')
    bc = r2['content'].count('\\]')

    if dc % 2 != 0:
        issues += 1
        print(f"  #{r['id']}: Odd dollars: {dc}")
    if bo != bc:
        issues += 1
        print(f"  #{r['id']}: Bracket mismatch: [{bo} vs {bc}]")

if issues == 0:
    print("ALL 150 REPORTS PASS! No LaTeX issues found.")
else:
    print(f"Remaining issues: {issues}")

conn.close()
