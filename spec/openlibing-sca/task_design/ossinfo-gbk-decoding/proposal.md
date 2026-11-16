# ossinfo-gbk-decoding — OSSinfo_extraction GBK 解码错误修复（#153）

## 需求背景

业务 Issue：[openlibing/openlibing-sca#153](https://gitcode.com/openlibing/openlibing-sca/issues/153)
（[缺陷] OSSinfo_extraction 存在 gbk 解码错误问题，label `bug`，2026-11-09 由 IceT_5 提出）。

- 现象：`OSSinfo_extraction` 提取 license 信息时，遇到 GBK 编码文本解码错误，输出乱码。
- 代码位置：`tools/OSSinfo_extraction/src/ossinfo_extraction/readme_opensource.py`
  license 全文读取/解码链路（`_decode_license_text`）。
- 根因（由 commit 记录确认，非 CVE）：
  1. 原实现直接把 `chardet.detect()` 的结果交给 `bytes.decode()`，以 ASCII 为主、仅含少量非 ASCII
     字符的 UTF-8 文本会被误判为 Latin-1 / Windows-1252，中文变成乱码；
  2. ScanCode 按原始字节识别 license，GBK 文件被其内部按 Latin-1 误解码，标准许可证被识别成
     `LicenseRef-scancode-*`（典型：双语木兰被判成 `LicenseRef-scancode-mulanpsl-2.0-en` 而非
     `MulanPSL-2.0`），导致 Readme.opensource / license 报告的许可证名称错误。
- 风险与影响：开源合规交付物（`Readme.opensource`、`*_license`、`*_copyright` 报告）出现乱码或错误的
  SPDX 标识，直接影响合规审核结论与对外声明；单字节误判还会让同一份文件在不同机器上产生不同结果。

## 功能描述

**做什么**：

1. license 全文解码加固：UTF-8（含 BOM）优先严格解码；失败或含 NUL 时走 chardet；
   GB2312/GBK 结果追加 GB18030 超集重试；全部严格解码失败时用最后识别到的编码做替换解码，
   最后退回 UTF-8 替换模式，并统一换行为 LF。
2. 非 UTF-8 license 文件名称修正：在写报告前把最终选定的非 UTF-8 license 文件严格解码为 UTF-8
   临时副本，单独重扫 license，用结果替换记录中的 SPDX/表达式（新增 `license_rescan.py`）。
3. `-l` 显式指定 SPDX 名称时覆盖 ScanCode 的 `LicenseRef-scancode-*` 检出，并保留检出文件用于读取全文。
4. copyright 噪声过滤：过滤 C 宏等代码文本被误识别成的版权声明，同时保留
   `(c) 1999 Entrust.net Limited`、`copr. 2019 Vendor GmbH`、`版权所有` 等有效变体。
5. 同步 infrastructure 工具链的其它既有修复：`-p` 路径越界校验与绝对路径精确匹配、
   SPDX 版本后缀识别、嵌套根目录循环检测、ScanCode 部分结果容错、`headers` 空列表容错。
6. 工具版本号对齐 4.0、依赖补充 `chardet>=3.0.0`、按社区 pre-commit 要求做格式与未用导入清理。

**不做什么**：

- 不同步外部仓库的 `tests` 目录（本仓 `tools/OSSinfo_extraction` 无测试目录，配套测试由 OSSchecktools 仓库统一维护）。
- 不修改 Java 侧调用方式、不新增编码相关配置开关或环境变量。
- 不重构 license 匹配的评分/优先级模型（仅修正空串守卫、路径精确匹配与 `-l` 覆盖）。
- 不做端到端真实包回归（仅 commit 记录作者本地验证结果）。

## 验收标准

- [x] GBK 编码 license 文本可正确解码：`0db8a95a` 记录真实包（requests / six / is-number / itoa /
      requests-github / libboundscheck）提取正确、GBK 输出 0 个 U+FFFD；`66b38d55` 补齐 UTF-8 优先与替换兜底
- [x] UTF-8 文本不再被 chardet 误判为 Latin-1/Windows-1252（`66b38d55`，`utf-8-sig` 快路径）
- [x] GB2312/GBK 失败时回退 GB18030；全部严格解码失败时用最后编码替换解码（`66b38d55`）
- [x] 非 UTF-8 license 文件重扫后 license 名称被修正（`8784f5de`，新增 `license_rescan.py`）
- [x] 重扫异常不中断主流程；含 NUL 字节按非 UTF-8 处理；spdx/expression 互相回填保证两份输出一致（`4cb7b14f`）
- [x] `-l` 指定 SPDX 名称时覆盖 `LicenseRef-scancode-*`（`b29b57a1`）
- [x] copyright 宏噪声被过滤，且不误删 `(c) 1999 Entrust.net Limited`、`copr. 2019 Vendor GmbH`、`版权所有` 等有效声明
      （`c0b53a3b`、`35274906`、`1ff6d5d9`、`a1f9fdd5`）
- [x] `-p` 指向目录时提示 `License path is not a file`，与"文件不存在"区分（`6a9fb2cd`）
- [x] 工具版本号 4.0（`26ddb075`）
- [ ] 仓库内单元测试：本轮未覆盖（本仓 OSSinfo 工具无测试目录，测试由 OSSchecktools 仓库维护，见 commit `4cb7b14f`/`b29b57a1` 说明）
- [ ] 端到端真实包回归：未验证（`0db8a95a` 仅记录作者本地"非端到端 164 项通过"与 6 个真实包结果）
- [ ] 无 BOM 的 UTF-16、极短 GBK 扩展字文本：已知限制，代码注释中保留说明，未在本轮修复

## 影响范围

- 仓库：`openlibing-sca`，仅 `tools/OSSinfo_extraction`（Python 工具，随镜像构建）。
- 接口：无变化（工具通过 CLI `cret` 调用，参数集合未变；`-p` 语义更严格：必须位于被测目标内）。
- 配置：无新增配置项；新增运行时依赖 `chardet>=3.0.0`（已在 `pyproject.toml` 与 `requirements.txt` 声明）。
- Schema：无变化。
- 输出形态：license 名称可能由 `LicenseRef-scancode-*` 变为标准 SPDX 标识；license 全文由乱码变为正确中文。
