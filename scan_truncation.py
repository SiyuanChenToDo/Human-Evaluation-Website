"""Scan ALL 150 reports for truncation in code blocks and formulas"""
import sys, re
sys.path.insert(0, '.')
import db
db.DB_PATH = 'eval.db'
conn = db.get_db()

issues = []

for r in conn.execute('SELECT id, research_topic, content FROM reports ORDER BY id').fetchall():
    rid = r['id']
    c = r['content']
    problems = []

    # Check for truncated code blocks: starts with ``` but content looks incomplete
    code_blocks = re.findall(r'```.*?```', c, re.DOTALL)
    for block in code_blocks:
        # Check if the code block ends abruptly (doesn't have proper closing)
        inner = block[3:-3].strip()  # Remove ``` markers
        lines = inner.split('\n')
        if lines:
            last = lines[-1].strip()
            # Truncation signs: ends with ..., or incomplete expression
            if last.endswith('...') or last.endswith('_') or last.endswith('{') or last.endswith(','):
                problems.append(f'TRUNCATED_CODE: {last[:60]}')

    # Check for truncated LaTeX formulas
    # Signs: unclosed braces, formulas ending mid-expression
    dollar_positions = [i for i, ch in enumerate(c) if ch == chr(36)]
    for pos in dollar_positions:
        # Get content up to 200 chars after this dollar
        after = c[pos:min(len(c), pos + 200)]
        # Check if the inline math block has proper closing
        # If this dollar opens math, the closing dollar should be within reasonable distance
        # Truncation signs inside math: incomplete commands like \math, \sum_{
        if after.startswith('$') and after[1:2] == '$':
            continue  # Skip $$ blocks
        if '\\math' in after[:50] and after.count(chr(36)) < 2:
            problems.append(f'TRUNCATED_MATH: {after[:60]}')

    # Check for truncated function/algorithm definitions
    if 'def compute_' in c:
        idx = c.find('def compute_')
        # Check if the next 300 chars contain a proper function end
        snippet = c[idx:min(len(c), idx+500)]
        if not any(snippet.endswith(x) for x in ['\n\n', 'return ', '# ']):
            # Function might be truncated
            last_few = snippet[-100:]
            problems.append(f'TRUNCATED_FUNC: def compute_...{last_few[:60]}')

    # Check for garbled formulas (like scrambled character sequences)
    garbled = re.findall(r'[∑∏∫]\{[^}]{0,2}\}', c)  # Sum with tiny subscript
    if garbled:
        problems.append(f'GARBLED_FORMULA: {garbled[0][:60]}')

    if problems:
        issues.append((rid, r['research_topic'][:80], problems))

conn.close()

print(f"Reports with truncation issues: {len(issues)}")
for rid, topic, probs in issues:
    print(f"\n#{rid}: {topic}")
    for p in probs:
        print(f"  - {p}")
