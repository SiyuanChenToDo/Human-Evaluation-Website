import sys
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'

r = db.get_report(20)
c = r['content']

# Show sections near problematic areas
# Check for non-ASCII characters that might cause issues
for i, ch in enumerate(c):
    if ord(ch) > 127 and ord(ch) < 0x3000:
        ctx = c[max(0,i-30):min(len(c),i+30)]
        print(f"Non-ASCII U+{ord(ch):04X} at pos {i}: {ctx}")

print("\n--- Report content (lines with special chars) ---")
for i, line in enumerate(c.split('\n')):
    if any(ord(ch) > 127 for ch in line):
        print(f"  [{i}] {line[:200]}")

print("\n--- Looking for math-like content ---")
# Check for underscores, carets, backslashes that might be math
d = chr(36)
for i, line in enumerate(c.split('\n')):
    has_math_markers = ('_' in line or '^' in line or '{' in line) and len(line) > 10
    has_backslash = chr(92) in line
    if has_math_markers or has_backslash:
        if len(line) < 300:
            print(f"  [{i}] {line[:250]}")
