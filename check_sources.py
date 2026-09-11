import urllib.request, os

urls_to_try = [
    'https://raw.githubusercontent.com/ldulcic/customer-support-chatbot/master/data/twcs.csv',
]

for url in urls_to_try:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            size = r.headers.get('Content-Length', 'unknown')
            print(f'OK: {url} | size: {size}')
    except Exception as e:
        print(f'FAIL: {url} | {e}')
