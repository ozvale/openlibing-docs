# #137 — 技术设计

## 方案概述

在 `extractUtil.py` 内建立「统一校验 + 两级预算 + fail-closed 清理」的安全解压路径：所有成员先过 `isSafeMemberName` 与声明值预算，再逐条目流式写出并累计实际字节，任何超限立即中止归档并删除本次已写文件；单个高压缩比条目降级为跳过而非整包拒绝。

## 数据流（修复后，以 un_zip 为例）

```
un_zip(filePath, tarPath)
  ├─ 遍历 infolist()
  │    ├─ 目录 → 跳过
  │    ├─ isSafeMemberName 不通过 → error + return（整包跳过）
  │    ├─ 符号链接（external_attr & 0xF000 == 0xA000）→ error + continue
  │    ├─ 条目数 > MAX_ENTRY_COUNT → error + return
  │    ├─ checkEntryBudget(file_size, compress_size) 超 ratio → error + continue
  │    └─ 收集 safeMembers / 累计声明 totalSize
  ├─ isTotalBudgetExceeded(totalSize, archiveSize) → error + return
  └─ 逐条目：zip_file.open(info) → _writeMemberWithBudget(剩余预算)
        ├─ 正常 → 记录 totalWritten / writtenFiles
        └─ 超限 → _abortOnBudget（删除 writtenFiles + 半成品）→ return
```

`un_tar` 结构与上一致，改为 `tarfile` 逐成员 `extractfile` 流式写；`un_rar` 用 `rar.open(info)` 流式写。

## 架构决策

| 决策                                     | 理由                                                                                                |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------- |
| D1 路径校验统一前置到 `isSafeMemberName` | zip/tar/rar 共用一套规则；拒绝绝对路径、盘符、反斜杠和 `..` 段，避免各库规范化行为差异被利用        |
| D2 拒绝符号链接/非普通文件               | 链接条目可绕过路径校验指向目录外，直接跳过比事后校验更稳妥                                          |
| D3 声明值预检 + 流式实测双保险           | 仅靠声明值可被伪造的 zip 中央目录/rar 头部绕过；流式按实际写出字节计数形成硬上限                    |
| D4 超限 fail-closed 并清理已写文件       | 避免留下半成品被扫描器当作完整源码分析，符合「不安全归档不参与扫描」的定位                          |
| D5 单条目超比例只跳过该条目              | 整包拒绝会误伤合法高压缩包（高压缩比文本/资源）；跳过单个可疑条目保住其余扫描价值                   |
| D6 tar 用 `tarfile` 替代外部 `tar xf -k` | 可在代码中逐成员校验与限流，且不再依赖系统 tar 版本行为；通过「目标已存在则跳过」显式保留不覆盖语义 |
| D7 阈值默认宽松 + 环境变量覆盖           | 兼容真实大包（约 90MB / 数万文件），同时允许部署侧按宿主资源收紧                                    |

## 涉及文件

| 文件                                              | 操作 | 说明                                                                                                                                                                           |
| ------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `tools/license-scanner/src/util/extractUtil.py`   | 修改 | 新增 `isSafeMemberName`、`checkEntryBudget`、`isTotalBudgetExceeded`、`_writeMemberWithBudget`、`_removeExtractedFiles`、`_abortOnBudget`；重写 `un_tar` / `un_zip` / `un_rar` |
| `tools/license-scanner/tests/test_extractUtil.py` | 新增 | 8 个 pytest 用例：正常解压（zip/tar）、穿越拒绝（zip/tar）、声明预检、流式硬上限、中止清理、超比例单条目跳过                                                                   |

测试运行方式（见 `tools/license-scanner/tests/conftest.py`）：把 `src` 加入 `sys.path`，`python -m pytest tools/license-scanner/tests -q`。

## 风险 & 缓解

| 风险                                                    | 缓解                                                                                                                 |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 阈值过严导致合法大包被跳过                              | 默认 ratio=100、总量 16 GiB、条目 20 万；可用 `SCA_EXTRACT_*` 环境变量按需调整                                       |
| 流式中止后清理不完整                                    | `writtenFiles` 记录每个成功写出的目标路径，`_removeExtractedFiles` 逐个删除，`OSError` 忽略以免中断清理              |
| 解压失败被静默吞掉（沿用原 `try/except` + `traceback`） | 保持与既有扫描容错一致（不因单个坏包中断整次扫描），通过 error 日志暴露；`extractCode` 返回值语义未改                |
| tar 不覆盖语义被破坏                                    | 逐条目写出前 `os.path.exists(destPath)` 跳过，单测 `test_un_tar_extracts_normal_package_and_keeps_no_overwrite` 断言 |
| rar 库 `is_symlink()` / `compress_size` 行为差异        | 代码已按 `rarfile` 接口调用，缺自动化用例；需在部署环境验证（未验证）                                                |
| 大包流式写出带来的 I/O 开销                             | 1 MiB 块顺序写，与原有 `extract`/`extractall` 量级相当；换来可计量的硬上限                                           |

## 跨仓影响

无代码级跨仓依赖。license-scanner 源码随 `openlibing-sca` 仓内 `tools/` 管理并打入容器镜像，改动需重建镜像生效；spec 文档归档 openlibing-docs 仓（本目录）。
