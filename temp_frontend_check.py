import urllib.request

try:
    with urllib.request.urlopen('http://127.0.0.1:5173/', timeout=5) as r:
        print('FRONTEND_STATUS', r.status)
        print(r.read(200).decode(errors='ignore'))
except Exception as e:
    print('FRONTEND_ERROR', repr(e))
    raise
