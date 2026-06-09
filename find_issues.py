import sys
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'
conn = db.get_db()

for rid in [89, 95, 98, 100]:
    r = conn.execute('SELECT content FROM reports WHERE id=?', (rid,)).fetchone()
    c = r['content']
    d = chr(36)  # dollar sign

    print(f'=== REPORT #{rid} ===')

    if rid in [89, 95, 98]:
        # Find dollar positions
        positions = [i for i, ch in enumerate(c) if ch == d]
        # Identify $$ pairs (consecutive dollars)
        ss_set = set()
        singles = []
        i = 0
        while i < len(positions):
            if i + 1 < len(positions) and positions[i+1] == positions[i] + 1:
                ss_set.add(positions[i])
                ss_set.add(positions[i+1])
                i += 2
            else:
                singles.append(positions[i])
                i += 1

        print(f'  Total $ chars: {len(positions)}')
        print(f'  $$ markers: {len(ss_set)}')
        print(f'  Single $: {len(singles)}')

        # Check each single dollar
        for pos in singles:
            ctx = c[max(0, pos-60):min(len(c), pos+60)]
            # Determine if math or currency
            is_math = any(x in ctx for x in ['\\', '_', '^', '{', '}', 'mathbf', 'theta'])
            print(f'  pos={pos} math={is_math}: {ctx[:120]}')
        print()

    if rid == 100:
        # Find unmatched \[
        positions = []
        i = 0
        while i < len(c) - 1:
            if c[i:i+2] == '\\[':
                positions.append(('OPEN', i))
                i += 2
            elif c[i:i+2] == '\\]':
                positions.append(('CLOSE', i))
                i += 2
            else:
                i += 1

        # Build a stack to find unclosed
        stack = []
        for typ, pos in positions:
            if typ == 'OPEN':
                stack.append(pos)
            else:
                if stack:
                    stack.pop()

        if stack:
            for pos in stack:
                ctx = c[max(0, pos-50):min(len(c), pos+80)]
                print(f'  UNCLOSED \\[ at {pos}: {ctx[:150]}')

        # Also show content near the end
        print(f'  Last 300 chars:')
        print(f'  {c[-300:]}')

conn.close()
