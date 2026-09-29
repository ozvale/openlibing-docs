# ci-env-info-metadata-validation — 实现任务

## 进度: 6/9 complete

### 已完成

- [x] Task 1: 插件侧采集与透传
      `test-action/pytest-orch/index.js` 新增 `buildCiEnvInfo()`，把 5 个 `ATOMGIT_*`
      组装成 `{"ci_env_info": {...}}`；`mainPyArgs.push("--ci_env_info", JSON.stringify(...))`
      透传给 `main.py`；入参回显与命令行打印各补一行。
      同步 ncc 重打包 `pytest-orch/dist/index.js`。

- [x] Task 2: 契约常量与校验器落位
      `scheduler_config.py` 新增 `ci_env_info` 默认值、`CI_ENV_INFO_GROUP`、
      `CI_ENV_INFO_KEYS`、`CI_ENV_INFO_VALUE_MAX_LEN`、`_CI_ENV_CONTROL_CHARS`，
      以及 `validate_ci_env_info` / `_clean_ci_env_value` 两个 staticmethod
      （置于既有 `set` 之后，保持静态方法集中在实例方法之前的仓内约定）。

- [x] Task 3: CLI 接入
      `main.py` 新增 `--ci_env_info`（`required=False`）；`_parse_ci_env_info`
      委托 `Config.validate_ci_env_info(parse_json_param(raw, "ci_env_info"))`；
      `_init_config` 中 `Config.set("ci_env_info", ...)`。

- [x] Task 4: 三种执行模式注入
      `pytest_executor.py` 新增 `_ci_env_vars`（含读取侧二次校验与 `ensure_ascii` 序列化）
      与 `_ci_env_exports`（`shlex.quote`）；`runner` / `remote` 走 `run_env.update()`，
      `local` 在命令装配中插入 `ci_exports`，保持与外层 `bash -lc` 的双重引用结构。

- [x] Task 5: 单元测试
      新增 `tests/test_ci_env_info.py`，24 个测试函数（参数化展开共 47 例），
      覆盖校验器 / CLI 解析 / 执行器注入三层。

- [x] Task 6: 安全链路实测
      9 个真实恶意载荷经完整双重引用后 `bash -c` 执行 → 零逃逸、canary 未生成；
      13 类编码/类型边界载荷 → 无一抛异常，照出两个字符类缺口；
      全仓 grep 确认 `Config.ci_env_info` 仅一处读取，排除路径/URL/SQL/上报类 sink。
      临时探针脚本全部置于 `/tmp` 并已删除，未留在工作区。

### 待办

- [ ] Task 7: 值清洗字符类收窄（**需授权后开工**）
      `_CI_ENV_CONTROL_CHARS` 补 Unicode `Cf` 类别与孤立代理区间，或改用字符白名单策略；
      同步补充对应回归测试。当前该缺口已实测确认存在且未修复，
      详见 design.md「已识别但未修复的缺口」。

- [ ] Task 8: 用户自测验收
      在真实流水线上确认三种执行模式的用例都能
      `json.loads(os.environ["ci_env_info"])` 取到 5 个字段。

- [ ] Task 9: 业务 PR 交付
      两个仓各自成 PR 并关联业务 Issue、补 `ai-assisted` 标签；
      发布顺序：先 `openlibing-pytest-executor`，后 `test-action`
      （旧调度框架遇到新插件传入的未定义参数会报错）。
      本仓改动含一处与需求无关的预存 `requirements.txt` 变更，提交前需自行定夺。
