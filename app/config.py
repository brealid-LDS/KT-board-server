import json

try:
    with open('config.json', 'r') as f:
        x: dict = json.loads(f.read())
    assert type(x) is dict
except Exception as e:
    print(f'读取失败: {e}')
    x = {}
    
site_name = x.get('site-name', 'KT board')
host = x.get('host', '127.0.0.1')
port = x.get('port', 9961)
key_path = x.get('key-path', 'test-skey-20250813')
    