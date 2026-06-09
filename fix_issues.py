"""Fix LaTeX formatting issues in 4 problematic reports"""
import sys
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'
conn = db.get_db()

d = chr(36)

for rid in [89, 95, 98, 100]:
    r = conn.execute('SELECT id, content FROM reports WHERE id=?', (rid,)).fetchone()
    c = r['content']
    original = c

    if rid == 100:
        # Report 100: has 6 \[ and 5 \] — one unclosed display math
        # Find the last \[ and add \] before the next section or end
        bo = c.count('\\[')
        bc = c.count('\\]')
        if bo != bc:
            # Find positions of all \[ and \]
            pos = 0
            opens = []
            closes = []
            while pos < len(c) - 1:
                if c[pos:pos+2] == '\\[':
                    opens.append(pos)
                    pos += 2
                elif c[pos:pos+2] == '\\]':
                    closes.append(pos)
                    pos += 2
                else:
                    pos += 1

            # Find the unmatched open
            stack = []
            unmatched = []
            for p in opens:
                stack.append(p)
            # Remove matched pairs
            i, j = 0, 0
            pairs = []
            remaining_opens = list(opens)
            for cl in closes:
                # Find the most recent open before this close
                for oi in range(len(remaining_opens)-1, -1, -1):
                    if remaining_opens[oi] < cl:
                        del remaining_opens[oi]
                        break

            if remaining_opens:
                for pos in remaining_opens:
                    # Add \] at the end of the paragraph containing this \[
                    # Find the next double newline or end of content
                    end = c.find('\n\n', pos)
                    if end == -1:
                        end = len(c)
                    else:
                        end = end  # insert before the paragraph break

                    # Check if there's already a \] nearby
                    nearby = c[pos:min(len(c), pos+500)]
                    # Insert \] right before the next blank line
                    insert_pos = end
                    c = c[:insert_pos] + '\n\\]\n' + c[insert_pos:]

                    print(f"Report #{rid}: Added missing \\] after pos {pos}")

    if rid in [89, 95, 98]:
        # These reports have odd dollar sign counts
        # Find the specific problematic $
        positions = [i for i, ch in enumerate(c) if ch == d]

        # Separate into $$ pairs and singles
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

        # Find the unpaired single
        if len(singles) % 2 != 0:
            # Pair singles: opening $ at even indices, closing $ at odd
            # The unpaired one is at index len(singles)-1
            # But we need to figure out if it's an opener or closer
            # Strategy: check the context — is it inside what looks like a LaTeX expression?
            unpaired_pos = singles[-1]
            ctx = c[max(0, unpaired_pos-200):min(len(c), unpaired_pos+200)]

            # Count $ before and after
            before = c[:unpaired_pos].count(d)
            after = c[unpaired_pos+1:].count(d)

            print(f"Report #{rid}: unpaired $ at position {unpaired_pos}")
            print(f"  $ before: {before}, $ after: {after}")
            print(f"  Context: {ctx[:200]}")

            # If there are more $$ signs total, it's likely a LaTeX math issue
            # Try to determine if it's an opening or closing $
            if before % 2 == 0:
                # Even before → this $ opens a new math block
                # Check if there's LaTeX content after that needs closing
                after_ctx = c[unpaired_pos+1:unpaired_pos+200]
                if any(x in after_ctx for x in ['\\', '_{', '^{']):
                    # Looks like math — add closing $
                    # Find natural break point (end of sentence/phrase)
                    for terminator in ['. ', '.\n', ')\n', '\n\n']:
                        term_pos = c.find(terminator, unpaired_pos+1)
                        if 10 < term_pos < unpaired_pos + 200:
                            c = c[:term_pos] + d + c[term_pos:]
                            print(f"  Added closing $ at position {term_pos}")
                            break
                    else:
                        # If no natural terminator found nearby, don't modify
                        print(f"  WARNING: Could not find safe place to add closing $")
                else:
                    # Not math — escape the dollar sign
                    c = c[:unpaired_pos] + '&#36;' + c[unpaired_pos+1:]
                    print(f"  Escaped non-math $ as HTML entity")
            else:
                # Odd before → this $ closes a math block, but is missing its opening
                # OR it's a stray $
                before_ctx = c[max(0, unpaired_pos-200):unpaired_pos]
                if any(x in before_ctx for x in ['\\', '_{', '^{']):
                    # Missing opening — add at start of math expression
                    # Find the beginning
                    for start_marker in ['where ', 'with ', 'and ', 'is ', 'as ']:
                        marker_pos = before_ctx.rfind(start_marker)
                        if marker_pos > 0:
                            insert_at = unpaired_pos - len(before_ctx) + marker_pos + len(start_marker)
                            c = c[:insert_at] + d + c[insert_at:]
                            print(f"  Added opening $ at position ~{insert_at}")
                            break
                else:
                    # Stray dollar — escape it
                    c = c[:unpaired_pos] + '&#36;' + c[unpaired_pos+1:]
                    print(f"  Escaped non-math $ as HTML entity")

    # Update if changed
    if c != original:
        conn.execute("UPDATE reports SET content = ? WHERE id = ?", (c, rid))
        conn.commit()
        print(f"  Report #{rid} updated in database")
    print()

conn.close()
print("Done.")
