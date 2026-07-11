import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8001/api/chat',
    data=json.dumps({'question': '什么是楷书？'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print('Status:', e.code)
    print(e.read().decode())
