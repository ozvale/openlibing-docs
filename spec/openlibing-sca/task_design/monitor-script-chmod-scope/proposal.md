# monitor-script-chmod-scope — monitor.sh 权限收紧范围收窄至业务目录

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/129
（【安全】【文件最小权限】monitor.sh 全盘 chmod 550 误伤系统 Python 库）

`monitor.sh#delete_file()` 在容器启动 300 秒后对全盘（仅排除 `/proc`、`/sys`）所有 `.py` / `.sh` / `.js` 等脚本执行 `chmod 550`。该命令在收紧业务文件权限的同时，把 root 属主的系统 Python 库（`/usr/lib/python3.11/site-packages` 下 scancode-toolkit、scipy、pluggy 等，以及 `/usr/lib64/python3.11` 标准库）一并改为 `550`，others 位为 `---`。

运行用户 `openlibing` 既非 root 也不在 root 组，将无法读取这些系统 `.py` 源码。当前未立即故障的原因是 pip 安装生成 `__pycache__/*.pyc`（644）且 Python import 走字节码；一旦触发 `.pyc` 失效重编译、`inspect.getsource()`、traceback 源码展示或 scancode 插件惰性导入，就会出现 `PermissionError`。

归类：CWE-732（Incorrect Permission Assignment for Critical Resource）。

## 功能描述

**做什么**：

1. 从全盘 `find /` 的脚本类型列表中移除 `*.py`，系统目录下 Python 库保持发行版默认权限。
2. 新增业务目录专项命令 `find /opt/app/openlibing -type f -name "*.py" -exec chmod 400 {} +`，仅收紧业务脚本。
3. 业务 `.py` 权限由 `550` 进一步收紧为 `400`：运行用户通过 `python3` 解释器调用业务脚本，只需要读权限，无需 owner 执行位与 group 读权限，与同目录 `*.jar` 的 `400` 级别对齐。

**不做什么**：

- 不把全盘 find 的其它脚本类型（`*.sh` / `*.bash` / `*.zsh` / `*.ksh` / `*.csh` / `*.pl` / `*.rb` / `*.php` / `*.js` / `*.lua` / `*.sql` / `*.tcl` / `*.awk`）一并收窄到业务目录，本轮仅处理 issue 指出的 `*.py`。
- 不改变 `monitor.sh` 的触发时机（启动 300 秒后执行一次）与其它权限规则（`/opt/app/openlibing` 目录 700、`cert` 600、`jre` 500 等）。

## 验收标准

- [ ] chmod 550 的 find 范围限定在 `/opt/app/openlibing`（或至少排除 `/usr`、`/etc`）：本轮仅将 `*.py` 从全盘 find 移除并改为业务目录专项 `chmod 400`；其它脚本类型仍走全盘 find（部分覆盖）
- [x] 容器运行 300s 后 `/usr/lib/python3.11`（含 site-packages）`.py` 权限保持默认 644：全盘 find 中已无 `*.py`，业务目录专项命令路径不覆盖 `/usr`（基于代码静态核实）
- [ ] 容器运行 300s 后 lcsca 扫描与 `ossinfo_extraction` 公告扫描仍正常工作：未验证（无容器运行证据；代码层面业务 `.py` 为 400，运行用户具备读权限，理论上可被 `python3` 读取）
- [x] `/opt/app/openlibing` 下脚本文件权限仍为收紧目标：非 `.py` 脚本仍为 `550`；`.py` 为 `400`（比原 `550` 更严格，属有意变更）

## 影响范围

- 仓库：`openlibing-sca`（`monitor.sh`，镜像运行时脚本）。
- 接口 / 配置 / schema：无。
- 部署：容器启动 300 秒后生效；`/usr` 下 Python 库权限恢复为默认值，业务 `.py` 变为 400。
- 行为风险：若后续业务脚本需要以 `./xxx.py` 方式直接执行（依赖 owner 执行位），`400` 会拒绝；当前业务均通过 `python3` 解释器调用。
