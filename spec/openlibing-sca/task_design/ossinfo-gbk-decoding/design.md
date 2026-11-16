# ossinfo-gbk-decoding — 技术设计

## 方案概述

按"解码层 → 名称识别层 → 后处理层"三层修复：

1. 解码层：`readme_opensource._decode_license_text_with_status` 采用"UTF-8 快路径 → chardet →
   GB18030 超集 → 替换兜底"的确定性顺序，并返回 `(text, exact)`，供上层判断解码是否可信。
2. 名称识别层：新增 `license_rescan.py`，把最终选定的非 UTF-8 license 文件严格解码为 UTF-8 临时副本，
   用 ScanCode 单独重扫 license，把结果回填到记录，修正 `LicenseRef-scancode-*` 误判。
3. 后处理层：copyright 增加"版权特征 + 最小字母数"两级有效性判断，过滤代码宏噪声；`-l` 显式 SPDX
   名称覆盖非 SPDX 检出并按最终名称去重。

## 数据流（修复后）

```
main.main()
  ├─ _prepare_scan_target → run_extractcode + _detect_nested_root（循环检测嵌套根目录）
  ├─ _scan_source → run_scancode(scan_license=True, scan_copyright=True)
  │     └─ 非零退出 → _load_partial_result 读取部分有效结果，否则 RuntimeError
  └─ _write_reports
        ├─ extract_and_duplicate_copyright
        │     └─ _is_meaningful_copyright（版权特征 + 至少 2 个 Unicode 字母）
        ├─ process_license_params
        │     ├─ _find_license_by_path（相对扫描根路径分量精确比较）
        │     ├─ _apply_user_name_for_non_spdx（-l 覆盖 LicenseRef-scancode-*）
        │     └─ _dedup_by_final_name（按最终 spdx/expression 去重）
        ├─ rescan_license_records（仅最终记录中非 UTF-8 且严格解码成功的文件）
        │     ├─ _group_records_by_file / _collect_rescan_candidates
        │     ├─ _write_utf8_copies → run_scancode(scan_license=True, scan_copyright=False)
        │     └─ _apply_rescan_results（spdx/expression 互填，只统计真正变化的记录）
        ├─ write_license_report
        └─ write_readme_opensource
              └─ _decode_license_text（UTF-8 快路径 → chardet → GB18030 → 替换兜底）
```

## 架构决策

| 决策                                                                           | 理由                                                                                                                                                                         |
| ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1：UTF-8 严格解码优先于 chardet                                               | chardet 对"ASCII 为主 + 少量中文"的 UTF-8 常误判为 Latin-1/Windows-1252；UTF-8 严格解码失败才说明确实不是 UTF-8（`66b38d55`）                                                |
| D2：含 NUL 字节跳过 UTF-8 快路径                                               | 无 BOM 的 UTF-16 文本常含 NUL，先走 UTF-8 会报错或误解码；直接交给 chardet 判断（`66b38d55`、`4cb7b14f`）                                                                    |
| D3：GB2312/GBK 结果追加 GB18030 超集重试                                       | GB18030 是 GBK 的超集，chardet 报 GBK 但严格解码失败时用超集可覆盖扩展字（`66b38d55`）                                                                                       |
| D4：替换解码使用"最后识别到的编码"而非 utf-8                                   | 非 UTF-8 文件按 UTF-8 替换解码会整篇变成 U+FFFD；用最后候选编码尽量保留可读内容（`66b38d55`）                                                                                |
| D5：解可信度显式建模（`exact` + `_is_trusted_decoding`）                       | 单字节猜测编码（latin-1/windows-125x/koi8 等）对任意字节都能"严格成功"，不代表判断正确；只有可信多字节编码才允许驱动 license 重扫（`1ff6d5d9`）                              |
| D6：名称修正采用"UTF-8 临时副本二次扫描"而非改写 ScanCode 内部编码             | 不改第三方工具行为；重扫范围仅限最终记录涉及的少量文件，成本可控且可回退（`8784f5de`）                                                                                       |
| D7：重扫前剔除 UTF-8 文件、解码不精确、含 NUL、读取失败、用户 `-l` 场景        | 避免无意义的重复扫描与"用不可信解码覆盖正确结果"；`-l` 场景名称由用户决定（`8784f5de`、`4cb7b14f`、`1ff6d5d9`）                                                              |
| D8：重扫结果 spdx/expression 互相回填且只统计变化记录                          | Readme.opensource 取 `spdx_identifier`、license 报告取 `license_expression`，两处必须一致；只统计变化避免误导性日志（`4cb7b14f`、`1ff6d5d9`）                                |
| D9：`-l` 覆盖 `LicenseRef-scancode-*` 并按最终名称重新去重                     | `LicenseRef-*` 不是 SPDX 标识；用户显式给名时应以用户为准，同时保留检出文件用于读取全文；覆盖后可能产生同名记录，需再次去重（`b29b57a1`、`1ff6d5d9`）                        |
| D10：copyright 采用"特征前置 + 最小字母数"而非纯关键字过滤                     | 纯关键字过滤会误删 `(c) 1999 Entrust.net Limited` 等有效声明；纯字母数判断又会保留 `(c) == L` 这类宏噪声。两级判断兼顾两者（`c0b53a3b`、`35274906`、`1ff6d5d9`、`a1f9fdd5`） |
| D11：字母判定使用 `unicodedata` 字母类别（L*）                                 | 固定 `[A-Za-z]`/`[一-鿿]` 会误删西里尔、希腊、阿拉伯、泰文等非拉丁声明（`35274906`）                                                                                         |
| D12：版权特征正则对齐 ScanCode 词元变体                                        | ScanCode 会输出 `Copyrighy`、`Cppyright`、`copr`（无点）、`opyright` 等变体；特征正则须覆盖这些变体，否则前置判定误删真实检出（`a1f9fdd5`）                                  |
| D13：`-p` 路径以"合法性 / 存在性 / 是否文件"三段校验，并以绝对路径精确匹配记录 | 原实现用后缀匹配，可能误选 `docs/LICENSE`、`LICENSES/LICENSE`；绝对路径精确匹配同时消除路径越界（`0db8a95a`、`6a9fb2cd`）                                                    |
| D14：ScanCode 非零退出码时读取部分有效结果                                     | 大仓库/异常文件常导致 ScanCode 非零退出但已产出有效 JSON；直接抛错会让整次提取白跑（`0db8a95a`）                                                                             |

## 涉及文件

| 文件                                                                       | 操作 | 说明                                                                                                                                                                                                                         |
| -------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/readme_opensource.py`     | 修改 | `_decode_license_text_with_status`（`66b38d55`、`1ff6d5d9`）、`_decode_license_text`、`_TRUSTED_MULTIBYTE_ENCODINGS`、`_is_trusted_decoding`、`_clean_license_path` 行宽修正（`d2092e08`）                                   |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/license_rescan.py`        | 新增 | 重扫模块：`rescan_license_records`、`_group_records_by_file`、`_collect_rescan_candidates`、`_write_utf8_copies`、`_apply_rescan_results`、`_rescan_candidates`（`8784f5de` 新增，`16a47f4e` 拆分）                          |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/main.py`                  | 修改 | `_write_reports` 接入重扫（`8784f5de`）；`_normalize_license_path` 路径边界与"不是文件"提示（`0db8a95a`、`6a9fb2cd`）；`_detect_nested_root`（`0db8a95a`）；绝对导入（`16a47f4e`）；行宽修正（`be7ffbbf`）                   |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/scancode.py`              | 修改 | 新增 `scan_copyright` 参数（重扫只扫 license）；`_load_partial_result` 部分结果容错（`8784f5de`、`0db8a95a`）                                                                                                                |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/license_extraction.py`    | 修改 | `SPDX_VERSION_SUFFIX` 版本后缀识别、`headers` 空列表容错、`_mutually_contains` 空串守卫、`_find_license_by_path` 精确路径比较、`_apply_user_name_for_non_spdx`、`_dedup_by_final_name`（`0db8a95a`、`b29b57a1`、`1ff6d5d9`） |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/parse_and_duplication.py` | 修改 | `_COPYRIGHT_MARKER`、`_COPYRIGHT_FEATURE`、`_has_meaningful_letters`、`_is_meaningful_copyright`（`c0b53a3b`、`35274906`、`1ff6d5d9`、`a1f9fdd5`）                                                                           |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/config.py`                | 修改 | 按 ruff format 重排 / 未用内容清理（`1ff6d5d9`）                                                                                                                                                                             |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/cleanup.py`               | 修改 | 未用导入清理（`1ff6d5d9`）                                                                                                                                                                                                   |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/extract.py`               | 修改 | 未用导入清理（`1ff6d5d9`）                                                                                                                                                                                                   |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/logger.py`                | 修改 | 未用导入清理、行宽 132 修正（`1ff6d5d9`、`d2092e08`）                                                                                                                                                                        |
| `tools/OSSinfo_extraction/src/ossinfo_extraction/prerequisite.py`          | 修改 | 未用导入清理（`1ff6d5d9`）                                                                                                                                                                                                   |
| `tools/OSSinfo_extraction/pyproject.toml`                                  | 修改 | 新增 `chardet>=3.0.0`（`0db8a95a`）；版本 2.0 → 4.0（`26ddb075`）；移除作者邮箱以通过 gitleaks（`1ff6d5d9`）                                                                                                                 |
| `tools/OSSinfo_extraction/requirements.txt`                                | 修改 | 新增 `chardet>=3.0.0`（`0db8a95a`）                                                                                                                                                                                          |
| `tools/OSSinfo_extraction/README.md`                                       | 修改 | `-p` 路径约束、精确匹配说明、建议使用 `-o` 独立输出目录、许可证声明（`0db8a95a`）                                                                                                                                            |
| `tools/OSSinfo_extraction/DESIGN.md`                                       | 修改 | copyright 策略由"关键字验证"改为"扫描结果保留"；新增 license 重扫设计说明（`0db8a95a`、`8784f5de`）                                                                                                                          |

## 风险 & 缓解

| 风险                                                           | 缓解                                                                                                                                                     |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 单字节猜测编码（latin-1/windows-125x）被误信，重扫覆盖正确结果 | `exact` 标记 + `_TRUSTED_MULTIBYTE_ENCODINGS` 白名单，仅可信多字节编码才参与重扫（`1ff6d5d9`）                                                           |
| 重扫阶段抛异常导致主流程中断                                   | `rescan_license_records` 全链路 try/except，失败仅 `warn` 并保留第一遍结果（`4cb7b14f`）                                                                 |
| 单个坏文件解码失败影响整批                                     | `_collect_rescan_candidates` 逐文件捕获 `OSError`/异常并跳过（`4cb7b14f`）                                                                               |
| copyright 误删有效声明                                         | 特征前置 + Unicode 字母判定 + 覆盖 ScanCode 词元变体；commit 明确保留 `(c) 1999 Entrust.net Limited`、`copr. 2019 Vendor GmbH`、`版权所有`（`a1f9fdd5`） |
| copyright 噪声漏过（宏误判进入生产报告）                       | 去掉 `(c)/©/copr.` 标记后要求至少 2 个 Unicode 字母；`(c) == L` 这类只剩单字母的噪声被过滤（`c0b53a3b`、`35274906`）                                     |
| `-l` 覆盖后产生重复记录                                        | `_dedup_by_final_name` 按最终名称重新分组去重（`1ff6d5d9`）                                                                                              |
| `-p` 严格化导致既有脚本路径写法失效                            | README 补充"必须位于被测目标内"，且日志区分"不存在"与"不是文件"；属预期行为收紧（`6a9fb2cd`）                                                            |
| 重扫带来的额外 ScanCode 调用耗时                               | 仅重扫最终记录涉及的少量非 UTF-8 文件，且只扫 license（`scan_copyright=False`），并复用 `--max-in-memory`（`8784f5de`）                                  |

## 跨仓影响

- 工具链来源：本次同步自 `cann/infrastructure` 工具链的既有修复（`0db8a95a` commit message），并保留
  openlibing 侧版权头与仓库 URL。
- 测试：`OSSinfo_extraction` 的单元测试由 **OSSchecktools** 仓库统一维护，本仓不新增测试目录
  （`4cb7b14f`、`b29b57a1` commit message 明确说明）。
- 对 Java 侧无接口/契约影响；Java 侧仅通过 `python -m ossinfo_extraction` 调用，参数不变。
- spec 文档归档 openlibing-docs 仓（本目录）。
