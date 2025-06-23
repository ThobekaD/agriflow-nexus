import os
import json
import re

__all__ = ['set_rpc_config', 'get_rpc_config', 'rpc_connect_args']

CFG_FN = os.path.expanduser('~/.adk')

VERSION_RE = re.compile(r'(\d+).(\d+).(\d+)')
CRR_VERSION = '0.0.5'


def _load_config_file(fn):
    with open(fn, 'r')as f:
        res_dic = json.load(f)
    if 'version' not in res_dic:  # update config for early version
        res_dic = {
            'rpc': {'servers': res_dic},
            'version': CRR_VERSION,
        }
    return res_dic


def set_rpc_config(host='', port: int = None, key=None, server_id='', default_server='', filename: str = None):
    import base64
    if filename:
        cfg_dic = _load_config_file(filename)
    else:
        if os.path.exists(CFG_FN):
            cfg_dic = _load_config_file(CFG_FN)
        else:
            cfg_dic = {'rpc': {'servers': {}}, 'version': CRR_VERSION}

        # cfg_dic.setdefault(server_id, {})
        # cfg_dic[server_id].update(host=host, port=port, key=key)

        server_id = server_id or 'default'

        rpc_cfg = cfg_dic['rpc']
        svr_cfg = rpc_cfg['servers'].get(server_id, {})

        host = host or svr_cfg.get('host', '127.0.0.1')
        port = port or svr_cfg.get('port', 9900)
        key = key or svr_cfg.get('key', base64.b64encode(os.urandom(32)).decode())
        svr_cfg.update(host=host, port=port, key=key)
        rpc_cfg['servers'][server_id] = svr_cfg

        rpc_cfg['default_server'] = default_server or rpc_cfg.get('default_server', 'default')
    with open(CFG_FN, 'w')as f:
        json.dump(cfg_dic, f, indent=4)


def get_rpc_config(server_id='') -> dict:
    # return _load_config_file(CFG_FN)[server_id]  # old version bak
    rpc_cfg: dict = _load_config_file(CFG_FN)['rpc']
    server_id = server_id or rpc_cfg.get('default_server', 'default')
    return rpc_cfg['servers'][server_id]


def rpc_connect_args(server=False, server_id=''):
    cfg = get_rpc_config(server_id=server_id)
    host = '0.0.0.0' if server else cfg['host']
    port = cfg['port']
    key = cfg['key'].encode()
    return (host, port), key


if __name__ == '__main__':
    set_rpc_config()
