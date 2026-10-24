# -*- coding: utf-8 -*-
"""samba/webster 文件头鉴定（Range 请求只取前 96 字节）。"""
import json
import urllib.request

for name in ['samba', 'webster']:
    url = f'https://gitcode.com/api/v5/repos/boostkit/KAE/contents/scripts/compressTestDataset/{name}?ref=kae2'
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    dl = d['download_url']
    req = urllib.request.Request(dl, headers={'Range': 'bytes=0-95'})
    with urllib.request.urlopen(req, timeout=120) as r:
        head = r.read(96)
    print('=== %s === size: %s' % (name, d['size']))
    print('first16(hex):', head[:16].hex())
    print('head(repr):', repr(head))
    print()
