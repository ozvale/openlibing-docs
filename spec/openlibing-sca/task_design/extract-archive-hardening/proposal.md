# #137 — license-scanner extractUtil.py 解压路径穿越与 zip 炸弹防护

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/137
（【安全】【安全隐私】license-scanner extractUtil.py 解压未校验路径穿越且无 zip 炸弹资源限制，当前状态 closed）

影响文件：`openlibing-sca/tools/license-scanner/src/util/extractUtil.py`。

压缩包内容来自外部上传/采集的源码包，属不可信输入，原实现存在两类缺陷：

1. **路径穿越（Zip Slip，CWE-22）**：`un_zip` 将 `zip_file.namelist()` 条目直接传给 `extract()`；`un_tar` 依赖外部 `tar xf <file> -k`（`-k` 只防覆盖，不防穿越，且行为随系统 tar 版本变化）；`un_rar` 直接 `extractall()`，三者均未校验条目路径。
2. **资源无限制（CWE-409 / CWE-770）**：未限制条目数量、单条目大小、累计解压大小，恶意高压缩比压缩包可耗尽磁盘/inode 或内存。

影响：可写出扫描工作目录之外的任意路径（覆盖配置/脚本，进而可能导致远程代码执行）；高压缩比炸弹或海量小文件可打垮 license-scanner 宿主节点。

## 功能描述

**做什么**：

1. 统一成员名校验 `isSafeMemberName`：拒绝空名、绝对路径（`/` 开头）、反斜杠、盘符（`X:`）与任何 `..` 路径段；zip 额外跳过符号链接条目（`external_attr` 类型位 0xA000），tar 仅接受普通文件/目录，rar 跳过 `is_symlink()` 条目；违规条目按归档整体跳过并记录 error 日志；
2. 资源预算（均可用环境变量覆盖）：
   - `MAX_COMPRESSION_RATIO`（`SCA_EXTRACT_MAX_RATIO`，默认 100）；
   - `MAX_TOTAL_UNCOMPRESSED_BYTES`（`SCA_EXTRACT_MAX_TOTAL_BYTES`，默认 16 GiB）；
   - `MAX_ENTRY_COUNT`（`SCA_EXTRACT_MAX_ENTRIES`，默认 200000）；
3. 两级预算：先用归档声明值做快速预检（`checkEntryBudget` / `isTotalBudgetExceeded`），再在解压时**流式统计实际写入字节**（`_writeMemberWithBudget`，块大小 1 MiB）作为硬上限，防伪造 zip 中央目录/rar 头部绕过；
4. 硬上限触发时 fail-closed：中止该归档并删除本次已写出的文件（`_abortOnBudget` / `_removeExtractedFiles`），不留半成品；
5. 单条目超压缩比只跳过该条目（`continue`），不再让整个归档失败，避免误伤合法高压缩包（如 opencv 类大包）；
6. `un_tar` 由外部 `tar xf -k` 子进程改为 Python `tarfile` 逐成员校验与 `extractfile` 流式写出，保留「目标已存在则跳过」的 `-k` 不覆盖语义，并容忍带尾斜杠的 REGTYPE 目录成员；
7. `.jar` 仍由 `checkWrar` 归入 zip 分支，自动继承全部 zip 防护。

**不做什么**：

- 未改为「先解压到临时目录再决定落盘」的两阶段策略（issue 修复建议 1 的后半段，本轮未覆盖）；
- 未引入外部解压白名单/沙箱或对解压后内容做病毒扫描；
- 未改变 `extractCode` 的归档发现与调度逻辑（仍只遍历第一层目录并对识别的压缩包就地解压）；
- rar 分支仅做代码级防护，无自动化用例覆盖（rar 依赖 `rarfile` 与外部 unrar 能力，本轮未验证）。

## 验收标准

- [x] zip/tar/rar 三类归档均在解压前校验成员路径（`isSafeMemberName`，代码证据）
- [x] zip 路径穿越条目被拒绝，整包不解压（`tests/test_extractUtil.py::test_un_zip_rejects_path_traversal`）
- [x] tar 路径穿越条目被拒绝（`test_un_tar_rejects_path_traversal`）
- [x] 声明总大小超预算时整包中止（`test_un_zip_declared_budget_precheck_aborts`）
- [x] 流式实际字节超预算时写入中止（`test_write_member_with_budget_enforces_streaming_hard_cap`）
- [x] 流式中止后清理已写文件（fail-closed，`test_un_zip_cleans_up_written_files_when_streaming_aborts`）
- [x] 单条目超压缩比只跳过该条目，其余条目正常解压（`test_un_zip_over_ratio_entry_skipped_not_whole_archive`）
- [x] 正常包可解压：zip 多级目录、tar 目录成员，且 tar 保持不覆盖语义（`test_un_zip_extracts_normal_package`、`test_un_tar_extracts_normal_package_and_keeps_no_overwrite`）
- [ ] rar 分支自动化用例（本轮未覆盖）
- [ ] 条目数量上限 `MAX_ENTRY_COUNT` 的专门用例（本轮未覆盖，仅有代码路径）
- [ ] 实际执行 `python -m pytest tools/license-scanner/tests -q` 结果（本轮为回溯补写文档，未执行，未验证）

## 影响范围

- 业务仓 `openlibing-sca`：仅 `tools/license-scanner`（`src/util/extractUtil.py`、新增 `tests/test_extractUtil.py`）
- 接口 / 契约：Python 工具内部函数；`un_zip` / `un_tar` / `un_rar` 签名不变，新增异常/跳过行为
- 配置：新增 3 个可选环境变量（不设置时使用默认阈值）
- 部署：license-scanner 随容器镜像发布，需重建镜像后生效；无 Java 侧改动
