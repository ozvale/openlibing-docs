# ossinfo-gbk-decoding — 实现任务

## 进度: 14/14 complete

### A. 工具链同步与 GBK 解码（解码层）

- [x] `0db8a95a` fix(ossinfo): sync tool with infrastructure master and GBK fix —— 同步 `-p` 路径越界校验、
      SPDX 版本后缀识别、copyright 保留非空声明、嵌套根目录循环检测、ScanCode 部分结果容错、
      `headers` 空列表容错、license 全文 chardet 自动识别编码；`chardet` 加入直接依赖
      （`requirements.txt`、`pyproject.toml`）；改动文件 9 个，+729/-430
- [x] `6a9fb2cd` fix(ossinfo): 区分 license 路径不存在与不是文件 —— `main.py` 拆分存在性检查与 `is_file()`
      检查，分别输出 `License file not found` / `License path is not a file`
- [x] `66b38d55` fix(ossinfo): license 文件优先按 UTF-8 解码，完善 GBK 回退与失败兜底 ——
      `utf-8-sig` 快路径（含 NUL 跳过）、chardet 回退、GB2312/GBK → GB18030 超集、最后编码替换解码

### B. license 名称修正（重扫）

- [x] `8784f5de` fix(ossinfo): 非 UTF-8 license 文件重扫修正 license 名称 —— 新增 `license_rescan.py`（151 行）；
      `main.py` 在写报告前调用 `rescan_license_records`；`scancode.py` 新增 `scan_copyright` 参数；
      `readme_opensource.py` 抽出 `_decode_license_text_with_status`
- [x] `4cb7b14f` fix(ossinfo): 加固 license 重扫异常处理与名称一致性 —— 逐文件捕获解码异常、
      含 NUL 按非 UTF-8 处理、pass2 空结果保留第一遍、spdx/expression 互相回填
- [x] `b29b57a1` fix(ossinfo): `-l` 指定 SPDX 名称时覆盖 LicenseRef 检出 ——
      `license_extraction.py` 新增 `_is_non_spdx_reference` / `_apply_user_name_for_non_spdx`
- [x] `16a47f4e` refactor(ossinfo): 拆分 rescan 超大函数并改用绝对导入 ——
      拆出 `_group_records_by_file`、`_collect_rescan_candidates`、`_write_utf8_copies`、
      `_apply_rescan_results`、`_rescan_candidates`；降低圈复杂度/嵌套深度

### C. copyright 噪声过滤

- [x] `c0b53a3b` fix(ossinfo): 过滤 ScanCode 将代码宏误识别为版权声明的噪声 —— 新增
      `_COPYRIGHT_MARKER`、`_MEANINGFUL_TOKEN`、`_is_meaningful_copyright`，含 copyright 单词直接保留，
      否则去标记后要求至少 2 个字母或 2 个中文字符
- [x] `35274906` fix(ossinfo): 按 Unicode 字母判断 copyright 有效性 —— 用 `unicodedata` 字母类别（L*）
      替换 `[A-Za-z]`/`[一-鿿]` 固定字符区间，避免误删非拉丁声明
- [x] `1ff6d5d9` fix(ossinfo): 修复检视意见指出的 license 匹配与重扫缺陷 —— `_mutually_contains` 空串守卫、
      覆盖后按最终名称 `_dedup_by_final_name` 重新去重、`_find_license_by_path` 删除失效形参并外提 resolve、
      `_load_partial_result` 返回 `Optional[dict]`、copyright 增加 `_COPYRIGHT_FEATURE` 前置判定、
      单字节猜测编码跳过重扫、重扫仅统计变化记录、预处理异常保护、ruff format 与未用导入清理、
      移除 pyproject 作者邮箱（gitleaks email-address 规则）；共 12 文件，+400/-251
- [x] `a1f9fdd5` fix(ossinfo): copyright 特征判定对齐 ScanCode 全部关键字变体 —— 覆盖
      `copr`（点可选）、`Copyrighy`、`opyright`、`opylefted` 等无年份变体

### D. 版本与代码风格

- [x] `26ddb075` chore(ossinfo): 工具版本号对齐到 4.0 —— `pyproject.toml` version `2.0` → `4.0`
- [x] `be7ffbbf` style(ossinfo): 修复行宽超 120 的导入与函数签名 —— `main.py` 导入分组与 `_write_reports` 签名换行
- [x] `d2092e08` style(ossinfo): 修复行宽 132 与空格冒号两处格式问题 —— `logger.py`、`readme_opensource.py`

## 交付记录

| commit     | 主题                  | 变更规模          |
| ---------- | --------------------- | ----------------- |
| `0db8a95a` | 工具链同步 + GBK 解码 | 9 文件 +729/-430  |
| `6a9fb2cd` | `-p` 目录/文件区分    | 1 文件 +3/-1      |
| `c0b53a3b` | copyright 噪声过滤    | 1 文件 +23        |
| `35274906` | Unicode 字母判定      | 1 文件 +20/-4     |
| `66b38d55` | UTF-8 优先 + GBK 回退 | 1 文件 +35/-8     |
| `8784f5de` | 非 UTF-8 license 重扫 | 5 文件 +234/-26   |
| `4cb7b14f` | 重扫异常加固          | 1 文件 +19/-7     |
| `b29b57a1` | `-l` 覆盖 LicenseRef  | 1 文件 +23        |
| `16a47f4e` | rescan 函数拆分       | 2 文件 +132/-87   |
| `26ddb075` | 版本 4.0              | 1 文件 +1/-1      |
| `be7ffbbf` | 行宽 120              | 1 文件 +6/-3      |
| `1ff6d5d9` | 检视意见缺陷修复      | 12 文件 +400/-251 |
| `a1f9fdd5` | copyright 变体对齐    | 1 文件 +7/-4      |
| `d2092e08` | 行宽 132 / 空格冒号   | 2 文件 +4/-2      |

- 分支：`ms_scan`（业务仓 `openlibing-sca`）
- 关联 Issue：`openlibing/openlibing-sca#153`
  - 14 个 commit 的 message 均未写 `Refs #153`（批次内直接提交），issue 关联以本 spec 为准。
  - 同主题但不在本 issue 映射表内的历史提交：`0e848187`（copyright 过滤改为 pygments 来源上下文判断）
    与 `7865ee5d`（Revert 该提交），最终落地为 `c0b53a3b` 的最小有效性判断方案。
- 验证方式：
  - `0db8a95a` 记录：非端到端 164 项通过；真实包 requests / six / is-number / itoa / requests-github /
    libboundscheck 提取正确，GBK 输出 0 个 U+FFFD（作者本地执行，仓库内无对应测试可复核）。
  - `4cb7b14f`、`b29b57a1`：配套测试由 OSSchecktools 仓库统一维护，本仓不包含测试目录。
  - 本仓未执行 `pytest`/端到端回归，**未验证**。
- 代码静态自检：`1ff6d5d9` 按社区 pre-commit 要求执行 ruff format 与未用导入清理；`be7ffbbf`、
  `d2092e08` 修复行宽超限。
