# #137 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: `extractUtil.py` 增加 `isSafeMemberName` / `checkEntryBudget` / `isTotalBudgetExceeded` 与阈值常量；`un_tar` 改用 `tarfile` 替换外部 `tar xf -k`；`un_zip` / `un_rar` 改为逐条目校验后解压（`c58582a7`）
- [x] Task 2: 增加流式字节硬上限 `_writeMemberWithBudget`、超限中止清理 `_abortOnBudget` / `_removeExtractedFiles`；单条目超压缩比改为跳过；tar 目录成员尾斜杠兼容（`cc8aeb7e`）
- [x] Task 3: 新增 `tools/license-scanner/tests/test_extractUtil.py`（8 个 pytest 用例）并交付 commit（`cc8aeb7e`）

## 交付记录

| commit     | 日期       | 标题                                                                    | 关联      |
| ---------- | ---------- | ----------------------------------------------------------------------- | --------- |
| `c58582a7` | 2026-11-03 | fix(license): harden extractUtil against path traversal and zip bombs   | Refs #137 |
| `cc8aeb7e` | 2026-11-11 | fix(extract): enforce streaming byte budget and skip over-ratio entries | Refs #137 |

- 分支：`ms_scan`（`openlibing-sca`）
- 验证方式（代码内证据）：
  - `tests/test_extractUtil.py`：`test_un_zip_rejects_path_traversal`、`test_un_tar_rejects_path_traversal`、`test_un_zip_declared_budget_precheck_aborts`、`test_write_member_with_budget_enforces_streaming_hard_cap`、`test_un_zip_cleans_up_written_files_when_streaming_aborts`、`test_un_zip_over_ratio_entry_skipped_not_whole_archive`、`test_un_zip_extracts_normal_package`、`test_un_tar_extracts_normal_package_and_keeps_no_overwrite`
  - 运行入口：`python -m pytest tools/license-scanner/tests -q`（`tests/conftest.py` 已将 `src` 加入 `sys.path`）
  - 本轮为回溯补写文档，未实际执行 pytest（结果未验证）
- 未覆盖：rar 分支自动化用例、`MAX_ENTRY_COUNT` 专项用例、「先解压到临时目录」两阶段策略
