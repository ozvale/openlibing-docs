# Design: migrate-issue-scanner-lcsca

- **业务 Issue**: openlibing/openlibing-sca#78
- **交付 PR**: https://gitcode.com/openlibing/openlibing-sca/pull/313（dev_scanner -> release_20260923，11 commits，已合入）
- **上游依赖**: openlibing/openlibing-sca-issue-scanner@dev_20260730（与 master 的 src/ 内容一致，仅 requirements.txt 行尾差异；原 Dockerfile 引用的 scancode 分支已删除）

## 1. 现状调用链

```text
OpenPersonDMScanDMServiceImpl#getCopyrightAndLicense(path, workdir)
  workdir = <PROJECT_HOME>/tools/license-scanner   ← DMContastName.ISSUESCANNER（最终值）
  ProcessBuilder(python, "src/command.py", "-m", "lcsca", path)
    → command.py: CommSca().scaResult(path, thread)
        → extractCode(path)                       ← util/extractUtil（压缩包解压）
        → subprocess: scancode -l -c <path> --json <tmp> -n <thread>
        → getSourceData(scaJson, type)            ← reposca/sourceAnalyze
            → LicenseCheck（reposca/config/Licenses.yaml 白黑名单）
            → infixToPostfix（util/postOrdered + util/stack）
      stdout: JSON 结果 → Java 解析
```

## 2. lcsca 最小依赖闭包（最终迁移清单，15 个源文件）

模块级 import 全量追踪结果（command.py → 全部可达模块），并叠加交付期死代码清理（§4 决策 3）后的最终状态：

| 目录           | 迁移文件                                                                                                                    | 说明                                                               |
| -------------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `src/`         | `command.py`                                                                                                                | CLI 入口（`-m pr` 入口已随 DB 层删除）                             |
| `src/reposca/` | `__init__.py`                                                                                                               | 包标记                                                             |
|                | `commSca.py`                                                                                                                | CommSca.scaResult 核心（DB init 已移除）                           |
|                | `analyzeSca.py`                                                                                                             | getScaAnalyze（模块级被引）                                        |
|                | `sourceAnalyze.py`                                                                                                          | getSourceData（lcsca 实际执行）                                    |
|                | `licenseCheck.py`                                                                                                           | license 白黑名单判定                                               |
|                | `config/Licenses.yaml`                                                                                                      | licenseCheck 的数据文件（相对 `__file__` 定位，必须随迁）          |
| `src/util/`    | `authApi.py`、`catchUtil.py`、`downUtil.py`、`extractUtil.py`、`formateUtil.py`、`popUtil.py`、`postOrdered.py`、`stack.py` | util 闭包（无 `__init__.py`，靠 PEP 420 命名空间包工作，保持原样） |

**初版迁移含、最终删除的 DB 模块**（commit `3d93edb9`）：`repoDb.py`、`prSca.py`、`itemLicSca.py`、`takeRepoSca.py`——均为 lcsca 路径死代码（见 §4 决策 3），删除后 lcsca 闭包自洽（commSca 对 itemLicSca 的模块级 import 一并清理）。

**不迁移**（lcsca 闭包外）：`main.py`、`dbSyn.py`、`scheduleUtil.py`、`tempSca.py`、`fixSca.py`、`makeRepoCsv.py`、`queryBoard.py`、`queryMeasure.py`、`resonseSca.py`、`scheduleSca.py`、`token.yaml`。

## 3. 目标结构

```text
openlibing-sca/
├── Dockerfile                          # 修改
├── tools/
│   ├── OSSinfo_extraction/             # 既有先例
│   └── license-scanner/                # 新增（初版命名 issue-scanner，交付期重命名，commit 731f5ba2）
│       ├── requirements.txt            # 最终 16 项
│       └── src/                        # 结构与上游一致（command.py 相对路径不变）
└── src/main/java/.../DMContastName.java # ISSUESCANNER 常量改值
```

### 3.1 Dockerfile 变更

删除（L76-79 附近）：

```dockerfile
RUN git config --global credential.helper store && \
    echo "https://${GIT_USERNAME}:${GIT_PASSWORD}@gitcode.com" > ~/.git-credentials
RUN git clone -b scancode https://gitcode.com/openlibing/openlibing-sca-issue-scanner.git ./issue-scanner && \
    rm ~/.git-credentials
RUN pip3 install --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ -r ./issue-scanner/requirements.txt
```

替换为（对齐 OSSinfo_extraction 先例）：

```dockerfile
COPY ./tools/license-scanner $PROJECT_HOME/tools/license-scanner
RUN pip3 install --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ -r $PROJECT_HOME/tools/license-scanner/requirements.txt
```

- 容器内路径 `$PROJECT_HOME/tools/license-scanner`，`src/command.py` 相对路径不变，无需 `ENV PYTHONPATH`（Java 以 workdir 方式调用，非 `-m` 模块方式）；
- GIT_USERNAME / GIT_PASSWORD 构建参数一并删除 ARG 声明；
- 构建期预创建 `/home/repo/tempRepo` 并赋权给非 root 用户 `openlibing`（commit `1a8e5600`，见 §4 决策 2）。

### 3.2 Java 侧变更

| 文件                                     | 变更                                                                                 |
| ---------------------------------------- | ------------------------------------------------------------------------------------ |
| `DMContastName.java`                     | `ISSUESCANNER = "issue-scanner"` → `"tools/license-scanner"`                         |
| `PrCommonName.java`                      | 同步改为 `"tools/license-scanner"`（定义未被 main 引用，但语义应一致，避免后续误用） |
| `DMContastNameTest` / `PrCommonNameTest` | 断言值同步更新                                                                       |
| `OpenPersonDMScanDMServiceImpl`          | **零改动**（workdir 由常量拼接，`src/command.py` 相对路径不变）                      |

### 3.3 requirements.txt 裁剪与升级（27 → 最终 16 项）

**裁剪过程**：

1. 迁移期按 lcsca 直接 import + scancode-toolkit 31.0.1 冲突 pin 裁剪：27 → 19 项；
2. 构建验证发现上游原版 `commoncode==31.2.1` 与 scancode-toolkit 31.0.1 要求的 `commoncode==31.0.0b4` 冲突（上游文件本就不自洽，因 scancode 分支早已停止构建从未暴露），lcsca 源码不直接 import commoncode，删除该 pin（commit `dc38260f`）；
3. DB 层删除后移除 `PyMySQL` / `DBUtils` / `SQLAlchemy`（commit `3d93edb9`），最终 16 项。

**最终 16 项**（`tools/license-scanner/requirements.txt`，以 release_20260923 合入版为准）：

```text
scancode-toolkit==31.0.1    # scancode 本体
beautifulsoup4==4.11.1      # scancode 传递依赖 pin
jsonpath==0.82              # sourceAnalyze/analyzeSca
PyYAML==6.0                 # sourceAnalyze/licenseCheck/authApi
requests==2.34.2            # authApi/downUtil（漏洞升级，原 2.26.0）
setuptools==80.10.2         # 安装兼容（漏洞升级，原 58.1.0）
tqdm==4.62.3                # downUtil
urllib3==2.8.0              # commSca/authApi（漏洞升级 1.25.8 → 2.x）
python-rpm-spec==0.11       # sourceAnalyze/analyzeSca: pyrpm.spec
rarfile==4.0                # extractUtil
GitPython==3.1.62           # commSca: git.repo（漏洞升级，原 3.1.27）
packaging==21.3             # scancode 传递依赖 pin
spdx-tools==0.7.0a3         # 必须：alpha 版不会被 pip 自动选中
attrs==22.1.0               # 依赖冲突 pin
pdfminer.six==20260107      # scancode 传递依赖（漏洞升级，原 20221105）
click==8.1.7                # 必须：scancode 31.0.1 与 click 8.2+ 不兼容
```

**漏洞依赖升级**（commit `7c84168c`，42 个 High/Critical 归零）：requests / setuptools / urllib3（1.x → 2.x）/ GitPython / pdfminer.six；同时修正 Dockerfile 尾部对 pdfminer.six 的降级覆盖安装（pip install 顺序导致安全版本被旧版覆盖）。其余 16 项已逐项对照 scancode-toolkit v31.0.1 setup.cfg 的 install_requires 核实，均兼容。

注：`from packageurl import PackageURL`（commSca）不在 requirements 中，依赖 scancode-toolkit 传递安装（packageurl-python），保持原状不显式添加。

## 4. 关键行为决策

| 决策点                                                                    | 结论                                                       | 依据                                                                                                                                                                                                                                                                                                                                                                           |
| ------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `CommSca.__init__` 的 MySQL 构造                                          | **删除**（commit `68dacc3a`，2026-09-17）                  | 初判"保持原样"，但部署环境缺 `MYSQL_PORT` 时 `int(None)` 抛 TypeError 直接断掉 lcsca 路径。核实 `_dbObject_` 仅被 `infoSca` 使用，而 `infoSca` 在 command.py 无任何调用入口（死代码）；lcsca/repo/local 三条实际路径均不触库                                                                                                                                                   |
| `/home/repo/tempRepo` 临时目录                                            | **Dockerfile 构建期预建**（commit `1a8e5600`，2026-09-17） | 初判"makedirs 递归创建"不成立：容器以非 root 用户 `openlibing` 运行，`/home` 归 root，`os.makedirs('/home/repo/tempRepo/tempJson')` 抛 PermissionError 且被 `catch_error` 吞掉 → stdout 输出 `null` → Java `processJsonFile` JSON 解析失败。旧镜像的 git clone 目标是 `./issue-scanner`，从未创建过 /home/repo。构建期 `mkdir -p /home/repo/tempRepo` 并 chown 给 `openlibing` |
| DB 层整体删除（repoDb / prSca / itemLicSca / takeRepoSca + `-m pr` 入口） | **删除**（commit `3d93edb9`，2026-09-23）                  | 决策 1 的延伸：四个 DB 模块仅服务于已确认死代码的 infoSca/pr 路径，保留只会引入 PyMySQL 连接池等无用依赖面；requirements 同步移除 PyMySQL/DBUtils/SQLAlchemy；src 下零残留引用（py_compile + 引用核查）                                                                                                                                                                        |
| 漏洞依赖升级                                                              | **升级 5 项 pin**（commit `7c84168c`，2026-09-23）         | 迁移引入的 requirements 承担了旧仓 42 个 High/Critical 漏洞；升级至当前无漏洞版本并核对 API 兼容（urllib3 1.x → 2.x 为主风险点）；顺带修正 Dockerfile 尾部 pdfminer.six 降级覆盖                                                                                                                                                                                               |
| 工具目录命名 `issue-scanner` → `license-scanner`                          | **重命名**（commit `731f5ba2`，2026-09-23）                | 迁入本仓后工具职责是 license/copyright 扫描，`license-scanner` 语义更准确；Java 常量、测试断言、Dockerfile 路径同步更新                                                                                                                                                                                                                                                        |
| `util/` 无 `__init__.py`                                                  | 保持原样                                                   | PEP 420 命名空间包，上游原样可跑                                                                                                                                                                                                                                                                                                                                               |
| Python 语法/缺陷修复                                                      | 不做                                                       | 行为一致性优先，缺陷在上游仓修                                                                                                                                                                                                                                                                                                                                                 |

## 5. 测试策略（Full）与验证结果

1. **Java 单测**（`python scripts/run-mvn.py`，私仓 401 不能直接 mvn）：
   - 更新 `DMContastNameTest`、`PrCommonNameTest` 断言；✅ 通过（4/4）
   - `OpenPersonDMScanDMServiceImplTest` 中 getCopyrightAndLicense 相关用例核对（不依赖 workdir 具体值：测试走两参重载，workdir 由参数传入）；
2. **Python 静态验证**：`python -m py_compile` 全部迁移文件 ✅；DB 模块在 src 下零残留引用 ✅；
3. **Dockerfile 验证**：文本级检查无 clone/凭证残留 ✅；Docker 构建通过（pip 依赖解析无冲突，版本 pin 已核对 scancode-toolkit 31.0.1 / 32.5.0 约束）✅；
4. **容器内端到端扫描**：`python src/command.py -m lcsca` 实扫验证 ⏳（PR #313 测试计划遗留项，依赖升级跨度大，需实扫确认）。

## 6. Commit 拆分与最终交付记录

初版按 3 commit 规划（源码迁移 / Dockerfile / Java 常量），最终 PR #313 共 11 个 commit：

| #   | commit     | 说明                                                                                              |
| --- | ---------- | ------------------------------------------------------------------------------------------------- |
| 1   | `ada506c1` | feat(tools): 引入 issue-scanner lcsca 最小闭包源码（19 文件，纯拷贝）                             |
| 2   | `5cb5d0ff` | build(docker): 移除 issue-scanner git clone，改用 tools 目录 COPY                                 |
| 3   | `dc862567` | feat(scanner): 容器内 issue-scanner 路径改至 tools/issue-scanner                                  |
| 4   | `dc38260f` | fix(tools): remove commoncode pin conflicting with scancode-toolkit 31.0.1                        |
| 5   | `68dacc3a` | fix(tools): remove unused DB init from CommSca constructor                                        |
| 6   | `1a8e5600` | fix(docker): pre-create /home/repo/tempRepo for issue-scanner lcsca                               |
| 7   | `7c84168c` | fix(deps): upgrade vulnerable python deps in issue-scanner requirements                           |
| 8   | `3d93edb9` | refactor(tools): remove unused db layer from issue-scanner lcsca path                             |
| 9   | `7024c898` | chore(deps): bump openlibing-common-sdk to 1.0.21.0（随分支带入的独立依赖升级，与迁移无直接关系） |
| 10  | `731f5ba2` | refactor(tools): rename tools/issue-scanner to tools/license-scanner                              |
| 11  | `3db76de7` | merge upstream/release_20260923 into dev_scanner                                                  |

## 7. 影响范围

- **openlibing-sca**：Dockerfile、`tools/license-scanner/`（新增 16 文件）、DMContastName、PrCommonName、2 个常量测试类、openlibing-common-sdk 版本；
- **部署**：镜像构建不再需要 GIT_USERNAME/GIT_PASSWORD；镜像内工具路径为 `tools/license-scanner`（外部脚本若有硬编码旧路径需同步）；
- **运行时**：lcsca 路径不再依赖 `MYSQL_*` 环境变量（DB init 与 DB 模块已删除）；命令、stdout JSON 协议不变；
- **上游仓**：`openlibing-sca-issue-scanner` 后续以 master 分支为准，本仓 `tools/license-scanner` 为 lcsca 的权威副本。
