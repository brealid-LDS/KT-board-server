from flask import Flask, request, jsonify, render_template
from collections import defaultdict
import uuid
import time
import config

app = Flask(__name__)

# ====== 原有内存态数据结构，保持不变 ======
registered_clients = {}
server_cache = {}
group_cache = defaultdict(dict)

# ====== 工具函数 ======
def make_token():
    return str(uuid.uuid4())

def is_alive(client_token):
    hb = server_cache[client_token]['last_heartbeat']
    if hb == 'None':
        return False
    period = registered_clients[client_token]["client_config"].get('heartbeat_period', 5)
    return (time.time() - hb) < 10 * period

def get_group_alive(group_name):
    if 'client-token' not in group_cache[group_name]:
        return 0
    return sum(1 for t in group_cache[group_name]['client-token'] if is_alive(t))

def timeago(ts):
    if ts == 'None':
        return '从未'
    s = time.time() - ts
    if s < 7:
        return '刚刚'
    if s < 10:
        return '10 秒内'
    elif s < 30:
        return f'半分钟内'
    elif s < 60:
        return f'1 分钟内'
    elif s < 3600:
        return f'{int(s/60)} 分钟前'
    elif s < 86400:
        return f'{int(s/3600)} 小时前'
    else:
        return f'{int(s/86400)} 天前'

def clamp_pct(p):
    return max(0.0, min(100.0, p))

# ====== API（保持你原有的三个） ======
@app.route(f'/{config.key_path}/clear-client')
def clear_client():
    registered_clients.clear()
    server_cache.clear()
    group_cache.clear()
    return jsonify({"status": "ok", "message": "All server caches cleared."})

@app.route(f'/{config.key_path}/register-client', methods=['POST'])
def register_client():
    data = request.get_json(force=True, silent=True) or {}
    client_group = data.get("client_group")
    if not client_group:
        return jsonify({"status": "error", "message": "client_group is required"}), 400

    client_name = data.get("client_name")
    if not client_name:
        return jsonify({"status": "error", "message": "client_name is required"}), 400

    client_config = data.get("client_config")
    if not client_config:
        client_config = {}
    elif type(client_config) is not dict:
        return jsonify({"status": "error", "message": "client_config must be dict"}), 400

    token = make_token()
    registered_clients[token] = {
        "client_group": client_group,
        "client_name": client_name,
        "client_config": client_config
    }
    server_cache[token] = {
        "last_heartbeat": "None",
        "client_info": {}
    }
    if client_group in group_cache and 'client-token' in group_cache[client_group]:
        group_cache[client_group]['client-token'].append(token)
    else:
        group_cache[client_group]['client-token'] = [token]

    return jsonify({"status": "ok", "token": token})

@app.route(f'/{config.key_path}/heart-beat', methods=['POST'])
def heart_beat():
    data = request.get_json(force=True, silent=True) or {}
    client_token = data.get("client_token")
    if not client_token:
        return jsonify({"status": "error", "message": "client_token is required"}), 400
    if client_token not in registered_clients:
        return jsonify({"status": "error", "message": "client_token is invalid"}), 400

    client_info = data.get("client_info")
    if not client_info:
        client_info = {}
    elif type(client_info) is not dict:
        return jsonify({"status": "error", "message": "client_info must be dict"}), 400

    server_cache[client_token]["last_heartbeat"] = time.time()
    server_cache[client_token]["client_info"] = client_info
    return jsonify({"status": "ok", "message": f"Heartbeat received from {client_token}"})

# ====== 新增：仪表盘页面（Jinja 模版） ======
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', site_name=getattr(config, 'site_name', 'KT board'))

# ====== 新增：前端自动刷新用的数据接口 ======
@app.route(f'/dashboard-data', methods=['GET'])
def dashboard_data():
    groups_payload = []
    for group_name in sorted(group_cache.keys()):
        tokens = group_cache[group_name].get('client-token', [])
        clients_payload = []
        for t in sorted(tokens, key=lambda x: registered_clients[x]['client_name']):
            reg = registered_clients.get(t, {})
            info = server_cache.get(t, {})
            hb = info.get('last_heartbeat', 'None')

            # 解析 client_info
            ci = info.get('client_info', {})
            # CPU：你的客户端上报是每核使用率（0-1）数组
            cpu_arr = ci.get('cpu', [])
            if isinstance(cpu_arr, list) and cpu_arr:
                cores = len(cpu_arr)
                total_pct = sum(cpu_arr) * 100.0   # 可能 >100（多核累积）
            else:
                cores = None
                total_pct = None

            # MEM： [usedGB, totalGB]
            mem_arr = ci.get('mem', [])
            if isinstance(mem_arr, list) and len(mem_arr) == 2:
                mem_used, mem_total = float(mem_arr[0]), float(mem_arr[1])
            else:
                mem_used = mem_total = None

            # GPU： [{usage: 0-1, mem: [usedGB, totalGB]}, ...]
            gpus = []
            for g in ci.get('gpu', []) or []:
                usage = g.get('usage', None)
                mem = g.get('mem', [])
                if usage is not None:
                    usage_pct = float(usage) * 100.0
                else:
                    usage_pct = None
                if isinstance(mem, list) and len(mem) == 2:
                    gu, gt = float(mem[0]), float(mem[1])
                else:
                    gu = gt = None
                gpus.append({
                    "usagePct": usage_pct,
                    "memUsedGB": gu,
                    "memTotalGB": gt,
                })

            clients_payload.append({
                "name": reg.get("client_name", t),
                "alive": is_alive(t),
                "heartbeat_period": reg.get("client_config", {}).get('heartbeat_period', 5),
                "last_heartbeat": None if hb == 'None' else int(hb * 1000),  # 前端用 ms
                "timeago": timeago(hb),
                "cpu": None if total_pct is None else {"cores": cores, "usagePct": total_pct},
                "mem": None if mem_total is None else {"usedGB": mem_used, "totalGB": mem_total},
                "gpu": gpus,
            })

        groups_payload.append({
            "name": group_name,
            "alive": get_group_alive(group_name),
            "total": len(tokens),
            "clients": clients_payload
        })

    return jsonify({
        "siteName": getattr(config, 'site_name', 'KT board'),
        "groups": groups_payload
    })

if __name__ == '__main__':
    app.run(config.host, config.port, debug=False)
