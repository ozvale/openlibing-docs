# path-and-image-symlink-hardening — 路径校验、PR 扫描与镜像构建软链接/提权加固

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/86
（【安全】【提权专项检查】未进行软连接校验以及压缩包未进行校验）

提权专项检查针对 `openlibing-sca` 服务（openEuler 基础镜像，容器内以非 root 用户 `openlibing` 运行）提出三类问题：

1. 路径校验工具 `FileUtils#fileValidated` 仅做字符串前缀匹配，未解析真实路径、无路径分隔边界，可被软链接或同前缀兄弟目录绕过；导出链路把 `community` / `version` 等请求参数直接拼进文件名。
   归类：CWE-59（Link Following）、CWE-22（Path Traversal）。
2. `Dockerfile` 未处理 SUID/SGID：基础镜像与 dnf/yum 安装包自带 `passwd`/`su`/`mount`/`ping` 等 setuid 程序，容器内一旦获得代码执行即可作为本地提权跳板。
   归类：CWE-269（Improper Privilege Management）。
3. 构建期以 root 解压 `rasp.tgz` 与 JRE tar 包，未校验条目（绝对路径、`..` 穿越）、未拒绝软链接、未剥离压缩包内属主与特殊权限；投毒压缩包可覆盖系统文件或预置指向系统路径的软链接。
   归类：CWE-22、CWE-59。

除 issue 正文外，本轮整改还覆盖 PR 增量扫描下载链路的同类软链接/路径穿越风险（`DownLoadFilesUtils#copySingleFile`）：PR 中含断链软链接或祖先目录为软链接时，`Files.copy` 跟随链接，导致整个 PR 扫描以"下载 gitcode 文件失败"中断，或把仓外文件复制进扫描暂存目录。

## 功能描述

**做什么**：

1. `FileUtils#fileValidated` 改为真实路径解析：对目标路径取绝对路径后，从"最近的存在祖先"调用 `toRealPath()`（解析已有路径中的软链接），再逐级拼回不存在的尾部组件，最终用 `Path#startsWith` 按路径组件比较，限制在工作目录内；入参空值、`InvalidPathException`、断链软链接一律拒绝。
2. 新增 `FileUtils#isValidFileNamePart`：文件名片段白名单（`[A-Za-z0-9._-]+` 且不以 `.` 开头）；在 `OpenScanServiceImpl`（license 导出、docx 导出、社区统计导出）与 `LicenseServiceImpl`（workbook 导出）落盘前校验 `community` / `version`，非法输入抛 `ScaException(500)`。
3. `Dockerfile` rasp.tgz 解压加固：解压前条目校验（拒绝绝对路径与 `..` 穿越）、拒绝带 SUID/SGID 位的普通文件、`--no-same-owner --no-same-permissions` 解压、解压后校验软链接 `readlink -f` 目标不逃逸 `$PROJECT_HOME`。
4. `Dockerfile` JRE tar 包：保留条目校验（绝对路径/`..`）与 `--no-same-owner --no-same-permissions`；官方 Temurin 包 `legal/` 自带包内相对软链接，故不做解压后软链接校验。
5. PR 扫描下载 `DownLoadFilesUtils#copySingleFile`：在 `prepareFile` 之前逐段校验路径组件（任一组件为软链接、含 `..`、为绝对路径、最终组件为目录均跳过），跳过而非中断整个 PR 扫描；同时避免含穿越的文件名先触碰目标目录。

**不做什么**：

- 不做镜像全量 SUID/SGID 清理：`856fb863` 首版加入的 `find / -xdev -perm /6000 -type f -exec chmod a-s {} +` 被 `68d3f885` 撤回，改为在 `rasp.tgz` 条目级拒绝 SUID/SGID，基础镜像与 dnf 系统二进制保留发行版默认权限。
- 不校验官方 JRE tar 包的软链接（`29d4ae4e` 撤回该检查），仅依赖条目校验与解压参数。
- 不修复 `fileValidated` 的 TOCTOU 窗口（校验与打开之间路径被替换）：`30211ad6` 提交说明中明确留作后续加固，需要原子打开能力。
- 不改写导出文件名生成规则（仍为用户输入拼接时间戳），仅增加输入白名单。

## 验收标准

- [x] `fileValidated` 单测覆盖目录外软链接、父目录软链接、`..` 穿越、同前缀兄弟目录、空值：`FileUtilsTest` 新增 7 个用例（`shouldReturnFalseWhenTargetFileIsSymlinkOutsideHome`、`shouldReturnFalseWhenParentDirIsSymlinkOutsideHome`、`shouldReturnFalseWhenPathTraversesOutsideHome`、`shouldReturnFalseWhenSiblingDirectorySharesHomePathPrefix`、`shouldReturnFalseWhenPathIsNullOrEmpty`、`isValidFileNamePart_shouldAcceptNormalCommunityAndVersion`、`isValidFileNamePart_shouldRejectTraversalAndIllegalChars`）
- [x] 导出链路对 `community` / `version` 非法字符校验生效，恶意输入抛 `ScaException(500, ... param error, ...)`（`OpenScanServiceImpl#exportToFile` / `#exportDocx` / `#saveCommunityCountExport`、`LicenseServiceImpl#writeWorkbookToFile`）；单测仅覆盖 `isValidFileNamePart` 本身，链路级异常未单独建用例
- [ ] 镜像构建后 `find / -perm /6000 -type f` 无输出：本轮未覆盖。`68d3f885` 撤回镜像全量 `chmod a-s`，改为 `rasp.tgz` 条目级拒绝 SUID/SGID；基础镜像自带 setuid 程序（`passwd`/`su`/`mount` 等）保留
- [x] rasp.tgz 与 JRE 解压步骤均带 `--no-same-owner --no-same-permissions`，并先做条目校验；rasp 解压后校验软链接不逃逸 `$PROJECT_HOME`；JRE 软链接按官方包信任（未校验，属本轮明确的取舍）
- [x] PR 扫描跳过策略用例已补充：断链软链接、祖先目录软链接、`..`、绝对路径、最终组件为目录共 6 个 `copySingleFile_*` 用例（`DownLoadFilesUtilsTest`）
- [ ] PR 扫描跳过行为经测试验证：未执行 `mvn test`，行为未验证（与 tasks.md"未验证"声明一致）

## 影响范围

- 仓库：`openlibing-sca`（analysis 模块、`Dockerfile`）。
- 接口：无外部接口契约变化；导出接口对非法 `community` / `version` 由"写文件后失败"变为直接返回业务异常（`ScaException`）。
- 配置 / schema：无。
- 部署：镜像构建行为变化——rasp.tgz 含绝对路径/`..`/SUID-SGID 条目时构建失败；JRE 解压不再校验软链接。
- 行为变化：PR 扫描会静默跳过软链接/穿越类文件（日志 `skip unsafe PR file path`），不再整单失败。
