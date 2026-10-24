-- =====================================================================
-- dwi_rd_efc_security_pinned_dep_detail 接口测试数据
-- 接口：POST /security/pinned-dep-list（SecurityPinnedDepFileService）
-- 说明：MCP 写通道被拦，本文件需在生产 Doris 客户端手工执行。
--       UNIQUE KEY (repo_id, scan_time, dep_id) 幂等覆盖，可重复执行。
-- 造数仓库：401712 = Ascend/msdebug（master，fileUrl 可拼装）
--           401286 = Ascend/RecSDK（develop，仓库隔离对照）
-- 生成：ai-assisted 2026-10-16
--
-- 【预期结果对账单】（执行后按下列断言逐项验证接口）
-- 1) 不传 startDate：取 401712 最新批次 2026-10-16 10:00:00，total=28
--    page=1 返回 20 条，page=2 返回 8 条；排序按 file_path, line, dep_id
-- 2) startDate=2026-10-15：取旧批次 2026-10-15 10:00:00，total=3
-- 3) startDate=2026-10-14：无批次，total=0、records/typeSummary 均为空数组
-- 4) pinned=true：total=9（不含 pinned=NULL 条目）
-- 5) pinned=false：total=18
-- 6) depType=containerImage：total=5（含 1 条 pinned=NULL）
-- 7) depType=containerImage & pinned=false：total=3
-- 8) typeSummary（无筛选）：容器镜像5 / pip命令11 / npm命令2 / Go命令3 /
--    下载即执行3 / Chocolatey1 / NuGet·.NET1 / 未识别1 / conanCommand1(未知码尾部追加)
-- 9) typeSummary（pinned=true）：容器镜像1 / pip命令3 / npm命令1 / Go命令2 /
--    下载即执行1 / NuGet·.NET1；零值类型不返回
-- 10) repoId=401286：total=3（仓库隔离，与 401712 互不可见）
-- 11) fileUrl 形如 https://gitcode.com/Ascend/msdebug/blob/master/<file_path>
-- =====================================================================

-- ---------- 401712 msdebug · 新批次 2026-10-16 10:00:00（28 行） ----------
INSERT INTO dwi_rd_efc_security_pinned_dep_detail
(repo_id, scan_time, dep_id, dep_type, file_path, line, dep_ref, pinned, signal, reason, etl_time)
VALUES
-- .gitcode/workflows/build.yml（8 条：镜像4 + pip2 + 下载即执行2）
(401712, '2026-10-16 10:00:00', 1, 'containerImage', '.gitcode/workflows/build.yml', 12, 'image: cann-server:8.0.0.alpha002@sha256:3f2a9d41...', 1, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 2, 'containerImage', '.gitcode/workflows/build.yml', 25, 'image: ubuntu:latest', 0, 'mutableTag', '镜像使用可变 tag（latest）：改为 @sha256 摘要引用', NOW()),
(401712, '2026-10-16 10:00:00', 3, 'containerImage', '.gitcode/workflows/build.yml', 38, 'image: ${{ env.BASE_IMAGE }}', 0, 'variableRef', '镜像名由构建变量拼接：写死镜像全名并按摘要引用', NOW()),
(401712, '2026-10-16 10:00:00', 4, 'containerImage', '.gitcode/workflows/build.yml', 51, 'uses: docker/build-push-action@v5', NULL, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 5, 'pipCommand', '.gitcode/workflows/build.yml', 63, 'pip install --require-hashes -r requirements.txt', 1, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 6, 'pipCommand', '.gitcode/workflows/build.yml', 71, 'pip install pytest', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
(401712, '2026-10-16 10:00:00', 7, 'downloadThenRun', '.gitcode/workflows/build.yml', 84, 'curl -sL https://example.com/install.sh | bash', 0, NULL, '下载即执行未按哈希固定：下载后校验 40 位提交 SHA', NOW()),
(401712, '2026-10-16 10:00:00', 8, 'downloadThenRun', '.gitcode/workflows/build.yml', 92, 'curl -sL https://example.com/tool@1f3e5a7b9c2d4f6a8e0b2c4d6f8a1e3c5b7d9f0a -o tool', 1, NULL, NULL, NOW()),
-- .gitcode/workflows/nightly.yml（5 条：镜像1 + npm2 + go2）
(401712, '2026-10-16 10:00:00', 9, 'containerImage', '.gitcode/workflows/nightly.yml', 8, 'image: swr.cn-north-4.myhuaweicloud.com/opensource/ascend/cann:latest', 0, 'mutableTag', '镜像使用可变 tag（latest）：改为 @sha256 摘要引用', NOW()),
(401712, '2026-10-16 10:00:00', 10, 'npmCommand', '.gitcode/workflows/nightly.yml', 20, 'npm ci', 1, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 11, 'npmCommand', '.gitcode/workflows/nightly.yml', 28, 'npm install lodash', 0, NULL, 'npm install 未用 lockfile：改用 npm ci 固定依赖树', NOW()),
(401712, '2026-10-16 10:00:00', 12, 'goCommand', '.gitcode/workflows/nightly.yml', 40, 'go install golang.org/x/lint/golint@v0.0.0-2024.01.01', 1, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 13, 'goCommand', '.gitcode/workflows/nightly.yml', 47, 'go get github.com/stretchr/testify', 0, NULL, 'go get 未固定版本：加 @vX.Y.Z 版本号', NOW()),
-- scripts/install.sh（7 条：pip2 + 下载即执行1 + choco1 + nuget1 + unknown1 + 未知码1）
(401712, '2026-10-16 10:00:00', 14, 'pipCommand', 'scripts/install.sh', 15, 'pip3 install -r requirements-dev.txt', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
(401712, '2026-10-16 10:00:00', 15, 'pipCommand', 'scripts/install.sh', 22, 'pip3 install torch --index-url https://download.pytorch.org/whl/cpu', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
(401712, '2026-10-16 10:00:00', 16, 'downloadThenRun', 'scripts/install.sh', 34, 'wget -qO- https://repo.anaconda.com/miniconda/Miniconda3-latest.sh | bash', 0, NULL, '下载即执行未按哈希固定：下载后校验 40 位提交 SHA', NOW()),
(401712, '2026-10-16 10:00:00', 17, 'chocoCommand', 'scripts/install.sh', 46, 'choco install cmake --version 3.28.1', 0, NULL, 'Chocolatey 安装未按哈希固定', NOW()),
(401712, '2026-10-16 10:00:00', 18, 'nugetCommand', 'scripts/install.sh', 55, 'dotnet add package Newtonsoft.Json --version 13.0.3', 1, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 19, 'unknown', 'scripts/install.sh', 61, 'conan install . --build missing', 0, NULL, '依赖判据暂不支持（unknown），无整改路径', NOW()),
(401712, '2026-10-16 10:00:00', 20, 'conanCommand', 'scripts/install.sh', 68, 'conan install . -r conancenter', 0, NULL, '依赖判据暂不支持（conanCommand），无整改路径', NOW()),
-- scripts/install_deps.sh（4 条：pip，凑分页第 2 页）
(401712, '2026-10-16 10:00:00', 21, 'pipCommand', 'scripts/install_deps.sh', 5, 'pip install --require-hashes -r ci-requirements.txt', 1, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 22, 'pipCommand', 'scripts/install_deps.sh', 12, 'pip install flake8', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
(401712, '2026-10-16 10:00:00', 23, 'pipCommand', 'scripts/install_deps.sh', 13, 'pip install mypy', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
(401712, '2026-10-16 10:00:00', 24, 'pipCommand', 'scripts/install_deps.sh', 20, 'pip install coverage', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
-- tests/requirements.txt（2 条）
(401712, '2026-10-16 10:00:00', 25, 'pipCommand', 'tests/requirements.txt', 3, 'pytest==8.1.1 --hash=sha256:1234abcd', 1, NULL, NULL, NOW()),
(401712, '2026-10-16 10:00:00', 26, 'pipCommand', 'tests/requirements.txt', 7, 'hypothesis', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
-- tools/setup.py（2 条）
(401712, '2026-10-16 10:00:00', 27, 'pipCommand', 'tools/setup.py', 10, 'pip install -e .', 0, NULL, 'pip 安装未固定哈希：加 --require-hashes 或固定版本', NOW()),
(401712, '2026-10-16 10:00:00', 28, 'goCommand', 'tools/setup.py', 18, 'go install mvdan.cc/gofumpt@v0.6.0', 1, NULL, NULL, NOW());

-- ---------- 401712 msdebug · 旧批次 2026-10-15 10:00:00（3 行，测批次定位） ----------
INSERT INTO dwi_rd_efc_security_pinned_dep_detail
(repo_id, scan_time, dep_id, dep_type, file_path, line, dep_ref, pinned, signal, reason, etl_time)
VALUES
(401712, '2026-10-15 10:00:00', 1, 'containerImage', '.gitcode/workflows/build.yml', 12, 'image: ubuntu:latest', 0, 'mutableTag', '镜像使用可变 tag（latest）：改为 @sha256 摘要引用', NOW()),
(401712, '2026-10-15 10:00:00', 2, 'pipCommand', 'scripts/install.sh', 15, 'pip3 install --require-hashes -r requirements.txt', 1, NULL, NULL, NOW()),
(401712, '2026-10-15 10:00:00', 3, 'npmCommand', 'package.json', 8, 'npm install lodash', 0, NULL, 'npm install 未用 lockfile：改用 npm ci 固定依赖树', NOW());

-- ---------- 401286 RecSDK · 2026-10-16 11:00:00（3 行，测仓库隔离） ----------
INSERT INTO dwi_rd_efc_security_pinned_dep_detail
(repo_id, scan_time, dep_id, dep_type, file_path, line, dep_ref, pinned, signal, reason, etl_time)
VALUES
(401286, '2026-10-16 11:00:00', 1, 'containerImage', '.gitcode/workflows/ci.yml', 6, 'image: ascend/cann-toolkit:8.0.0', 0, NULL, '镜像仅版本号无哈希：改为 @sha256 摘要引用', NOW()),
(401286, '2026-10-16 11:00:00', 2, 'goCommand', 'Makefile', 30, 'go install golang.org/x/tools/cmd/goimports@v0.21.0', 1, NULL, NULL, NOW()),
(401286, '2026-10-16 11:00:00', 3, 'unknown', 'build.sh', 12, 'bazel build //...', NULL, NULL, NULL, NOW());

-- =====================================================================
-- 测试完清理（按需执行）
-- DELETE FROM dwi_rd_efc_security_pinned_dep_detail
-- WHERE repo_id IN (401712, 401286)
--   AND scan_time IN ('2026-10-15 10:00:00', '2026-10-16 10:00:00', '2026-10-16 11:00:00');
-- =====================================================================
