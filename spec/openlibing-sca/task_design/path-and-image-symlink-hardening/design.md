# path-and-image-symlink-hardening — 技术设计

## 方案概述

按"校验点前移 + 真实路径解析 + 构建期条目校验"三条线整改：

1. Java 侧路径校验从字符串前缀比较升级为真实路径 + 路径组件比较；导出文件名片段增加白名单校验；PR 扫描下载在复制前逐段检查路径组件并按策略跳过。
2. 镜像构建期对 `rasp.tgz` 做条目级校验（绝对路径 / `..` / SUID-SGID）并校验软链接不逃逸业务目录；JRE 官方包只保留条目校验与解压参数。
3. SUID 治理由"镜像全量剥离"调整为"投毒压缩包条目级拒绝"，避免破坏发行版系统二进制。

## 架构决策

| 决策                                                               | 理由                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 `fileValidated` 解析真实路径后再比较                            | `Paths.get(path).toAbsolutePath().normalize()` 后，向上找到最近存在的祖先调用 `toRealPath()`（解析软链接），再把不存在的尾部组件逐级 `resolve` 回去；最终 `realPath.startsWith(homePath)` 按组件比较，天然消除同前缀兄弟目录绕过与软链接写穿 |
| D2 目标不存在时对"最近存在祖先"解析                                | 导出流程创建的是尚不存在的文件，直接 `toRealPath()` 会抛 `NoSuchFileException`；对祖先解析可拦截祖先目录为软链接的场景（与 `FileUtilsTest#fileValidated_shouldReturnFalseWhenParentDirIsSymlinkOutsideHome` 对应）                           |
| D3 空路径 / 非法路径 / 断链一律返回 false                          | 保持返回 boolean 的既有签名，调用方无需改异常处理；`InvalidPathException` 与 `toRealPath()` 的 `IOException` 均按拒绝处理                                                                                                                    |
| D4 新增 `isValidFileNamePart` 白名单而非黑名单                     | 黑名单易漏（编码、全角、分隔符变体）；白名单 `[A-Za-z0-9._-]+` 且不以 `.` 开头，直接排除 `/`、`\`、`..`、空白与特殊字符                                                                                                                      |
| D5 导出链路在写文件前抛 `ScaException(500)`                        | 复用仓内既有 `ScaException` + `ErrorCode` 风格，REST 层由统一异常处理返回；避免先落盘后失败留下临时文件                                                                                                                                      |
| D6 rasp.tgz 解压前做 `tar -tzf` 条目校验                           | 构建期以 root 解压，必须在落盘前拒绝绝对路径与 `..` 穿越；再以 `--no-same-owner --no-same-permissions` 剥离包内属主/权限，防止投毒包覆盖系统文件                                                                                             |
| D7 rasp 软链接校验从"禁止任意软链接"放宽为"不逃逸 `$PROJECT_HOME`" | `856fb863` 的严格版 `find ... -type l -print -quit \| grep -q .` 会把包内合法互链也判失败；`ec34bfd3` 改为 `readlink -f` 后与 `$PROJECT_HOME/` 前缀比较，只拒绝指向系统路径的链接                                                            |
| D8 JRE 包不做解压后软链接校验                                      | 官方 Temurin JRE tar 包 `legal/` 目录自带约 145 个指向 `../java.base/` 的相对软链接（许可证去重），严格校验会导致镜像构建在解压后静默失败（`29d4ae4e`）                                                                                      |
| D9 SUID 治理收敛为 rasp.tgz 条目级拒绝                             | `68d3f885` 撤回镜像全量 `chmod a-s`：该命令会一并剥离基础镜像/dnf 安装的 `passwd`、`su`、`mount` 权限，影响系统行为；改为 `tar -tvzf \| grep -Eq '^-..[sS]\|^-.....[sS]'`，投毒包无法植入提权二进制，系统文件保持原权限                      |
| D10 PR 扫描逐组件校验并跳过                                        | 仅检查最终组件会漏掉祖先目录软链接（`Files.copy` 会跟随）；逐段 `Files.isSymbolicLink` + `..` + 绝对路径 + 最终组件为目录（gitlink）任一命中即跳过，与 `license-scanner/extractUtil.py` 跳过软链接成员的策略一致                             |
| D11 校验前移到 `prepareFile` 之前                                  | `prepareFile` 会建目录、删旧目标文件；含穿越的文件名若先执行会触碰仓外路径，故先校验再准备目标                                                                                                                                               |
| D12 TOCTOU 暂不处理                                                | `fileValidated` 与后续 `open` 之间仍存在路径替换窗口，完整修复需原子打开；已在 `30211ad6` 说明中留作后续加固，本轮不做                                                                                                                       |

## 关键实现

`FileUtils#fileValidated`（`src/main/java/com/openlibing/sca/analysis/utils/FileUtils.java`）：

```
target = Paths.get(path).toAbsolutePath().normalize()
homePath = Paths.get("").toRealPath()
while (!Files.exists(existing, NOFOLLOW_LINKS)) { 记录文件名，上移父目录 }
realPath = existing.toRealPath()   // 断链/不可解析 -> false
for (name : remaining) realPath = realPath.resolve(name)
return realPath.startsWith(homePath)
```

`DownLoadFilesUtils#isUnsafeCopySource`（私有静态方法，被 `copySingleFile` 调用）：绝对路径 → 不安全；逐段 `..` → 不安全；逐段 `Files.isSymbolicLink` → 不安全；最终 `Files.isDirectory(current, NOFOLLOW_LINKS)` → 不安全。

## 涉及文件

| 文件                                                                                   | 操作 | 说明                                                                                                                         |
| -------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/utils/FileUtils.java`                       | 修改 | `fileValidated` 真实路径解析；新增 `isValidFileNamePart`                                                                     |
| `src/main/java/com/openlibing/sca/analysis/service/impl/OpenScanServiceImpl.java`      | 修改 | `exportToFile`、docx 导出、`saveCommunityCountExport` 增加 `community`/`version` 白名单校验                                  |
| `src/main/java/com/openlibing/sca/analysis/service/impl/LicenseServiceImpl.java`       | 修改 | `writeWorkbookToFile` 增加 `community` 白名单校验                                                                            |
| `Dockerfile`                                                                           | 修改 | rasp.tgz 条目/SUID/软链接校验与解压参数；JRE 条目校验与解压参数；最终形态无镜像级 SUID 清理                                  |
| `src/main/java/com/openlibing/sca/analysis/utils/security/DownLoadFilesUtils.java`     | 修改 | `copySingleFile` 前置路径安全校验 + `isUnsafeCopySource`                                                                     |
| `src/test/java/com/openlibing/sca/analysis/utils/FileUtilsTest.java`                   | 修改 | 新增 7 个用例（软链接/穿越/同前缀/空值/白名单），软链接类用例在不支持创建软链接的主机上 `Assumptions.assumeTrue(false)` 跳过 |
| `src/test/java/com/openlibing/sca/analysis/utils/security/DownLoadFilesUtilsTest.java` | 修改 | 新增 6 个 `copySingleFile_*` 用例（断链软链接、目录软链接、`..`、绝对路径、目录终组件、常规嵌套路径回归）                    |

## 风险 & 缓解

| 风险                                                 | 缓解                                                                                                               |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `fileValidated` 仍存在 TOCTOU 窗口（D12）            | 已记录为后续加固项；当前校验降低触发面，导出目标目录由服务自身控制                                                 |
| 收紧白名单误拒合法社区/版本名（含空格、`+`、中文等） | `community` 来源于平台元数据，实测样例 `22.03-LTS`、`openGauss_3.0` 均通过；若出现新命名需扩展白名单               |
| rasp.tgz 未来引入合法 SUID 程序或包内软链接          | 构建会失败并暴露在校验步骤；包内互链已允许，仅拒绝逃逸 `$PROJECT_HOME` 的链接                                      |
| JRE 官方包软链接被信任                               | 包源固定为清华镜像 Adoptium 21 JRE，且条目校验仍拒绝绝对路径/`..`；如需彻底校验需引入白名单                        |
| 撤回镜像级 SUID 清理后基础镜像仍带 setuid 程序       | 服务以非 root 运行，且入口/监控脚本已收紧权限；残余风险由容器运行时策略（非 root、只读挂载等）分担，本轮明确不覆盖 |
| PR 扫描静默跳过软链接文件导致漏扫                    | 日志打印 `skip unsafe PR file path`，与 license-scanner 跳过策略一致；如需提升可见性可在结果中标注跳过文件         |
| 软链接类单测在 Windows 无开发者模式下跳过            | 用例使用 `Assumptions` 跳过，Linux CI 正常执行                                                                     |

## 跨仓影响

无业务代码跨仓依赖；`Dockerfile` 变更影响镜像构建流水线（`rasp.tgz`/JRE 下载源需保持当前形态）。spec 文档归档 `openlibing-docs` 仓。

## 明确不在范围

- 镜像全量 SUID/SGID 清理（被 `68d3f885` 撤回）。
- 官方 JRE 包软链接校验（被 `29d4ae4e` 撤回）。
- `fileValidated` TOCTOU 原子打开改造。
