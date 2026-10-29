# 【openLiBing】扩展安全编译选项扫描覆盖产物类型 — 归档

## 关联

- FE 需求：【openLiBing】扩展安全编译选项扫描覆盖产物类型
- 业务 Issue：openlibing/security-compilation-options-action#14
- 业务 PR：openlibing/security-compilation-options-action#26（分支 `sec-option-artifact-coverage`，待合入 master）
- docs PR：本归档 PR（openlibing/openlibing-docs）
- 集成仓同步：openlibing/code-metrics-scan 分支 `fix-lizard-install-compat`（commit `0372351`，未随本需求单独提 PR）

## 需求摘要

嵌入式工具链构建产物中，可重定位目标文件常以 `.obj`、`.c.obj` 等非惯用后缀存放于构建中间目录，静态库以 `.a` 归档分发。原扫描器按目录位置与后缀约定识别产物，导致后缀不规范的 ELF 与归档内成员漏扫。本需求将产物识别统一改为按文件内容判定：单文件按 ELF 魔数（`.obj`、无后缀等任意命名均可）、归档包按 zip/tar/ar 魔数试探解包递归扫描；放开构建中间目录（`SKIP_DIRS` 移除 `CMakeFiles`）；对归档成员按内容 SHA256 去重（树内真实路径一律保留可见，不做跨路径合并）；两遍扫描（树内先行、成员第二遍）保证结果与遍历顺序无关。`.dbg` 调试符号文件与编译器探测桩文件为显式非核查对象，继续排除；14 项检测器判定逻辑、插件输入参数与上传协议均不变。

## 交付历程

### security-compilation-options-action（分支 sec-option-artifact-coverage，PR #26）

- commit `0614202`：feat(scan) 按内容识别归档与产物并做 SHA256 去重（初版方案）
- commit `7985b25`：fix(scan) 去重限定归档成员并改两遍扫描消除顺序依赖（自测复议后修正）

### code-metrics-scan（集成仓同步，分支 fix-lizard-install-compat）

- commit `0372351`：同步 sec-option-scan 插件最新源码，含本需求相关部分（内容识别/成员限定去重/两遍扫描）；同一 commit 一并承载详情链接需求的插件侧同步；`cicdUrl` 保持生产值

## 用户自测反馈

- diting 产物包全量回归通过：4842 行、两次全量扫描输出 sha256 一致，`.elf`/`a.out` 等树内独立路径全部可见
- 反馈 1：扫描文件数较历史报告大幅上升（10 → 4842）→ 确认为漏扫修正后的预期口径，交付说明已显式声明
- 反馈 2：与其他平台文件数存在差异（SP/FS/Ftrapv 统计）→ 已定位 Ftrapv 差异主因：其他平台将 731 个 `.a` 静态库作为独立扫描对象（4842 + 731 = 5573），本扫描器对内容重复的归档成员去重跳过；SP/FS 计数差异与 N/A 判定规则相关，差异明细另行对账；是否将 `.a` 作为独立对象输出待决策，未纳入本期实现
- Windows 本地兼容性问题（包内 `nul` 设备名文件、深路径 MAX_PATH 报错）不影响 Linux 扫描执行机，不作为验收项

## 最终验证

- 任意命名 ELF（`.obj`、`.c.obj`、无后缀）全部纳入扫描，判定口径与 `.o` 一致；`.dbg` 与探测桩文件排除保持（`SKIP_BASENAMES` 改按去后缀基名匹配命名变体）
- 任意后缀、改名或无后缀的归档（zip/tar/ar 魔数试探）解包递归扫描；`.run` 保留原后缀 + 载荷探测；损坏归档告警不阻断扫描
- 成员限定去重：diting 包 1659 个 `.a` 成员内容全部与树内重复、0 行进入结果；树内 4842 行全部保留（`.elf` 10 个路径、`a.out` 10 个路径均可见）
- 两遍扫描结果与遍历顺序无关、可复现；`.so`/可执行文件/`.deb`/`.jar`/`.whl`/`.run` 判定口径无回退
- 用例：本地构造 30 项 + 去重语义复议后合成断言 17 项，全部通过
- 双副本一致性：`dist/sec_option_scan.py` 与 `dist/bin/sec_option_scan.py` 字节一致
- 平台端到端：GitCode 项目 openlibing-cicd-test-new 的 `openlibing-security-compilation-options-diting.yml` 引用 `@sec-option-artifact-coverage` 实跑，扫描上报正常

## 设计偏差与取舍

1. `.a` 支持方式：关闭 PR #23（后缀白名单方式）与 Issue #11，统一由归档内容识别实现——`.a` 作为 ar 归档按魔数解包
2. 去重范围：初版全量内容去重会误合并树内独立路径（实测 `.elf` 原件与打包副本被合并不可见）→ 修正为仅归档成员侧去重，树内路径先行登记哈希、成员第二遍处理并按包内相对路径排序
3. 识别依据：内容魔数/试探替代后缀枚举；`.run` 保留后缀探测避免 Makeself 回归；7z/rar 需三方依赖本期不支持；LiteOS 等 RTOS 平台不纳入
4. 探测桩过滤：`SKIP_NAMES` 固定名改为 `SKIP_BASENAMES` 去后缀基名匹配，覆盖 `.o`/`.obj`/`.c.obj`/`.bin` 命名变体；探测目录下的链接产物 `a.out` 保留可见
5. 集成仓同步：code-metrics-scan 保持生产 `cicdUrl`，测试分支的 beta 直连地址不随同步落入集成仓

## 可复用经验

- 产物识别以内容为准（ELF 魔数 + 归档试探识别），后缀枚举必然遗漏；试探失败自然回退单文件处理，不阻断扫描
- 内容去重应限定在重复来源侧（归档成员）；全量去重会误合并不同归属的独立路径
- 两遍扫描（树内先行登记哈希、成员第二遍处理 + 排序）保证结果与遍历顺序无关、可复现
- 漏扫修正类改动会显著改变统计口径（本需求 10 → 4842 行），交付说明与测试移交口径需显式声明

## 归档日期

2026-10-13
