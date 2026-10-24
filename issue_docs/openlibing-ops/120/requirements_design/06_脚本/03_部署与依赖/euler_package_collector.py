#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Euler 软件包详情采集脚本（替代 SeaTunnel get_euler_package.conf）

数据链路：eulermaker data-api（固定入参 POST，无分页，一次全量）
         → Doris raw 层 raw_euler_package_info（os_project, spec_url, data_json）
         → sdi 层 sdi_rd_efc_euler_package 由既有 DML 清洗（不改）

接口说明：
  POST https://eulermaker.openeuler.openatom.cn/api/data-api/search
  固定入参：index=snapshots，os_project 指定项目，is_trunk=true，size=1，
  按 create_time 倒序取最新快照。spec_commits 为 map（key=包名，value=包对象），
  每包展开一行写入 raw 层；包名不在包对象内，sdi 层由 spec_url 尾段反解。

凭证（环境变量，与 SeaTunnel conf 的 ${openlibing_doris_*} 对齐，禁止硬编码）：
  OPENLIBING_DORIS_URL       形如 jdbc:mysql://fe1:9030,fe2:9030/openlibing?...
  OPENLIBING_DORIS_USERNAME
  OPENLIBING_DORIS_PASSWORD

依赖：pip install requests pymysql

Usage:
  python euler_package_collector.py                     # 正常采集写库
  python euler_package_collector.py --dry-run           # 只拉接口+解析，不写库
  python euler_package_collector.py --os-project xxx     # 换项目（默认 24.03-LTS-SP4）
"""

import argparse
import json
import os
import re
import sys
import time

import requests
import pymysql

API_URL = "https://eulermaker.openeuler.openatom.cn/api/data-api/search"
DEFAULT_OS_PROJECT = "openEuler-24.03-LTS-SP4:everything"
INSERT_SQL = ("INSERT INTO raw_euler_package_info "
              "(os_project, spec_url, data_json) VALUES (%s, %s, %s)")
BATCH_SIZE = 500
# Doris string_type_length_soft_limit_bytes 默认 1MB，超限单条会被拒收，防御性跳过
DATA_JSON_MAX_BYTES = 1024 * 1024


def build_body(os_project):
    """构造固定入参（与原 SeaTunnel conf 的 body 逐字段一致）"""
    return {
        "index": "snapshots",
        "query": {
            "size": 1,
            "_source": ["spec_commits", "custom_packages"],
            "query": {
                "bool": {
                    "must": [
                        {"term": {"os_project": os_project}},
                        {"term": {"is_trunk": True}},
                    ]
                }
            },
            "sort": [{"create_time": {"order": "desc"}}],
        },
        "sort": [{"create_time": {"order": "desc"}}],
    }


def fetch(os_project, retry):
    """调用接口，指数退避重试"""
    body = build_body(os_project)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    last_err = None
    for attempt in range(1, retry + 1):
        try:
            resp = requests.post(API_URL, json=body, headers=headers,
                                 timeout=(12, 120))
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retry:
                wait = 2 ** attempt
                print("[WARN] 第 %d 次请求失败: %s，%ds 后重试" % (attempt, e, wait),
                      flush=True)
                time.sleep(wait)
    raise RuntimeError("接口请求失败（已重试 %d 次）: %s" % (retry, last_err))


def parse(data, os_project):
    """解析 spec_commits，逐包展开为 (os_project, spec_url, data_json) 行"""
    hits = ((data or {}).get("hits") or {}).get("hits") or []
    if not hits:
        raise RuntimeError("响应 hits 为空，无快照数据")
    spec_commits = (hits[0].get("_source") or {}).get("spec_commits") or {}
    if not isinstance(spec_commits, dict) or not spec_commits:
        raise RuntimeError("spec_commits 为空或格式异常（非对象）")
    if spec_commits.get("spec_url"):
        raise RuntimeError("spec_commits 结构异常：疑似被当作包对象")

    rows, skipped = [], 0
    for pkg_name, pkg in spec_commits.items():
        if not isinstance(pkg, dict):
            skipped += 1
            continue
        spec_url = pkg.get("spec_url")
        data_json = json.dumps(pkg, ensure_ascii=False)
        if not spec_url or len(data_json.encode("utf-8")) > DATA_JSON_MAX_BYTES:
            skipped += 1
            print("[WARN] 跳过包 %s（spec_url 缺失或 data_json 超 1MB）" % pkg_name,
                  flush=True)
            continue
        rows.append((os_project, spec_url, data_json))
    return rows, skipped, len(spec_commits)


def parse_jdbc_url(jdbc_url):
    """解析 jdbc:mysql://fe1:9030,fe2:9030/db?... 为 [(host, port), ...], database"""
    m = re.match(r"^jdbc:mysql://([^/]+)/([^?]+)(?:\?.*)?$", jdbc_url.strip())
    if not m:
        raise ValueError("无法解析 Doris JDBC URL: %s" % jdbc_url)
    hosts, database = m.group(1).split(","), m.group(2)
    parsed = []
    for h in hosts:
        if ":" in h:
            host, port = h.rsplit(":", 1)
            parsed.append((host, int(port)))
        else:
            parsed.append((h, 3306))
    return parsed, database


def connect(url, user, password):
    """多 FE 逐个尝试连接"""
    hosts, database = parse_jdbc_url(url)
    last_err = None
    for host, port in hosts:
        try:
            conn = pymysql.connect(host=host, port=port, user=user,
                                   password=password, database=database,
                                   charset="utf8mb4", connect_timeout=12)
            print("[INFO] 已连接 Doris FE: %s:%d/%s" % (host, port, database),
                  flush=True)
            return conn
        except Exception as e:  # noqa: BLE001
            last_err = e
            print("[WARN] 连接 %s:%d 失败: %s" % (host, port, e), flush=True)
    raise RuntimeError("所有 FE 连接失败: %s" % last_err)


def write(conn, rows):
    """分批 executemany 写入，返回提交行数"""
    written = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i:i + BATCH_SIZE]
            cur.executemany(INSERT_SQL, batch)
            written += len(batch)
    conn.commit()
    return written


def verify(conn, os_project):
    """对账：查询表内该 os_project 的行数（UNIQUE KEY upsert 幂等）"""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM raw_euler_package_info "
                    "WHERE os_project = %s", (os_project,))
        return cur.fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Euler 软件包详情采集脚本")
    parser.add_argument("--os-project", default=DEFAULT_OS_PROJECT,
                        help="Euler 项目名（默认 %(default)s）")
    parser.add_argument("--retry", type=int, default=3, help="接口重试次数")
    parser.add_argument("--dry-run", action="store_true",
                        help="只拉接口并解析，不写库")
    args = parser.parse_args()

    data = fetch(args.os_project, args.retry)
    rows, skipped, total = parse(data, args.os_project)
    print("[INFO] spec_commits 共 %d 包：有效 %d 行，跳过 %d"
          % (total, len(rows), skipped), flush=True)
    if not rows:
        print("[ERROR] 解析后 0 行，终止", flush=True)
        return 1

    if args.dry_run:
        print("[INFO] dry-run 通过。首行样例: spec_url=%s" % rows[0][1],
              flush=True)
        return 0

    url = os.environ.get("OPENLIBING_DORIS_URL")
    user = os.environ.get("OPENLIBING_DORIS_USERNAME")
    password = os.environ.get("OPENLIBING_DORIS_PASSWORD")
    if not all([url, user, password]):
        print("[ERROR] 缺少环境变量 OPENLIBING_DORIS_URL / "
              "OPENLIBING_DORIS_USERNAME / OPENLIBING_DORIS_PASSWORD", flush=True)
        return 1

    conn = connect(url, user, password)
    try:
        written = write(conn, rows)
        actual = verify(conn, args.os_project)
        print("[INFO] 写入完成：本批 %d 行；表内 %s 现存 %d 行（UNIQUE KEY 幂等，"
              "含本批覆盖后的全量）" % (written, args.os_project, actual), flush=True)
        if actual <= 0:
            print("[ERROR] 对账失败：表内行数为 0", flush=True)
            return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
