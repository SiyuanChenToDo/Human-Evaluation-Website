import sys, re, urllib.request, http.cookiejar

# Fetch the page
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
import urllib.parse
data = urllib.parse.urlencode({'reviewer_id': '1'}).encode()
opener.open('http://127.0.0.1:5000/login', data)

# Get report 66
resp = opener.open('http://127.0.0.1:5000/report/66')
html = resp.read().decode('utf-8')

# Find formula around PCC
idx = html.find('PCC-guided dynamic')
if idx > 0:
    snippet = html[idx:idx+500]
    with open('test66_out.txt', 'w', encoding='utf-8') as f:
        f.write(f'FOUND at {idx}\n')
        f.write(snippet[:500] + '\n\n')

# Check if formulas are broken
d = chr(36)
formulas = re.findall(re.escape(d) + r'[^' + re.escape(d) + r']+' + re.escape(d), html)
broken = [f for f in formulas if '<sub>' in f]
with open('test66_out.txt', 'a', encoding='utf-8') as f:
    f.write(f'Total formulas: {len(formulas)}\n')
    f.write(f'Broken: {len(broken)}\n')
    for b in broken[:3]:
        f.write(f'  {b[:120]}\n')
print('Done - check test66_out.txt')
