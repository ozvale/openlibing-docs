# path-and-image-symlink-hardening — 实现任务

## 进度: 8/8 complete

- [x] Task 1: `FileUtils#fileValidated` 真实路径解析 + 组件边界比较；新增 `isValidFileNamePart`（`856fb863`）
- [x] Task 2: 导出链路 `community` / `version` 白名单校验（`OpenScanServiceImpl` 3 处、`LicenseServiceImpl` 1 处，`856fb863`）
- [x] Task 3: `Dockerfile` rasp.tgz 条目校验 + 解压参数 + 软链接检查；JRE 条目校验 + 解压参数；镜像级 SUID 清理（首版，`856fb863`）
- [x] Task 4: 撤回 JRE 解压后软链接检查，保留条目校验与解压参数（`29d4ae4e`）
- [x] Task 5: rasp 软链接检查放宽为 `readlink -f` 不逃逸 `$PROJECT_HOME`（`ec34bfd3`）
- [x] Task 6: 撤回镜像级 `chmod a-s`，改为 rasp.tgz 条目级拒绝 SUID/SGID（`68d3f885`）
- [x] Task 7: `DownLoadFilesUtils#copySingleFile` 跳过软链接文件（`59e599f1`）
- [x] Task 8: `copySingleFile` 逐组件路径校验并前移到 `prepareFile` 之前（`30211ad6`），补 `FileUtilsTest` / `DownLoadFilesUtilsTest` 用例

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                                  | 关联            |
| ---------- | --------------------------------------------------------------------- | --------------- |
| `856fb863` | fix(security): harden path validation, input checks and image build   | `Fixes #86`     |
| `29d4ae4e` | fix(dockerfile): drop symlink check on official JRE tarball           | 承接 `856fb863` |
| `ec34bfd3` | fix(dockerfile): relax rasp symlink check to PROJECT_HOME containment | 承接 `856fb863` |
| `68d3f885` | fix(dockerfile): reject SUID/SGID entries in rasp archive             | 承接 `856fb863` |
| `59e599f1` | fix(pr-scan): skip symlink files instead of failing gitcode PR scan   | 关联 #86 场景   |
| `30211ad6` | fix(pr-scan): skip PR files behind symlinked directories              | `Refs #86`      |

验证方式：

- 单测：`FileUtilsTest` 新增 7 个用例；`DownLoadFilesUtilsTest` 新增 6 个 `copySingleFile_*` 用例（其中软链接相关用例在无法创建软链接的主机上自动跳过）。
- 静态核实：`Dockerfile` 当前 L61-L66 为 rasp 解压校验链，L124-L132 为 JRE 条目校验与解压参数，全文已无 `perm /6000` / `chmod a-s`。
- 未验证：未执行 `mvn test` 复核通过情况；镜像构建与容器内提权场景未做实际验证（本次为回溯归档，业务仓只读）。
