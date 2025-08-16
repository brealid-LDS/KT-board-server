from app import config
import requests, random


response = requests.get(f'http://127.0.0.1:{config.port}/{config.key_path}/clear-client')
print(response.text)

print('-' * 40)
for i in range(1, 11):
    test_data = {
        'client_group': f'Group-{random.randint(1, 3)}',
        'client_name': f'Client-{i}',
    }
    response = requests.post(f'http://127.0.0.1:{config.port}/{config.key_path}/register-client', json=test_data)
    print(i, response.text, sep=': ', end='')
    
    if random.randrange(100) < 18:
        continue
    
    test_data = {
        'client_token': response.json()["token"],
        'client_info': {
            'cpu': [random.random() for _ in range(random.choice([2, 4, 6, 8, 12, 16]))],
            'mem': [random.random() * 16, 16], # 单位 GB
            'gpu': [{
                    'name': 'Nvidia GeoForce 9090',
                    'usage': random.random(),
                    'mem': [random.random() * 16, 16], # 单位 GB
                } for _ in range(8)
            ],
        }
    }
    response = requests.post(f'http://127.0.0.1:{config.port}/{config.key_path}/heart-beat', json=test_data)
    print(response.text)