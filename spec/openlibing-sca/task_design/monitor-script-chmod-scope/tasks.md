# monitor-script-chmod-scope — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 全盘 find 移除 `*.py`，并对 `/opt/app/openlibing` 下 `*.py` 单独执行 `chmod 550`（`0e1d77b1`）
- [x] Task 2: 业务 `*.py` 权限由 `550` 收紧为 `400`，与 `*.jar` 对齐（`f1723f96`）
- [x] Task 3: 静态核验 `monitor.sh` 最终形态与 issue 验收项差异（全盘 find 保留其它脚本类型；`*.py` 为 400）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                              | 关联        |
| ---------- | ----------------------------------------------------------------- | ----------- |
| `0e1d77b1` | fix(docker): scope python chmod 550 to business dir in monitor.sh | `Refs #129` |
| `f1723f96` | fix(docker): tighten business python scripts to chmod 400         | `Refs #129` |

关键 diff：

- `0e1d77b1`：全盘 find 删除 `-o -name "*.py"`；新增注释与 `find /opt/app/openlibing -type f -name "*.py" -exec chmod 550 {} +`。
- `f1723f96`：上述命令 `chmod 550` → `chmod 400`。

验证方式：

- 静态核实：`monitor.sh` L17-L23 当前形态；全盘 find 无 `*.py`，业务目录专项命令仅命中 `/opt/app/openlibing`。
- 未验证：未在容器内执行 `monitor.sh` 后复核 `/usr/lib/python3.11` 与 `/usr/lib64/python3.11` 的权限位，也未实际运行 lcsca 扫描与 `ossinfo_extraction` 公告扫描（本次为回溯归档，业务仓只读）。
- 无自动化测试：`monitor.sh` 为镜像内 shell 脚本，仓库未配套脚本级测试。
