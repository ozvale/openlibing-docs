# oss-scan-action 插件开发迁移工作总结

> 日期：2026-09-22
> 范围：openlibing-ci `scan_vuls.sh` → GitCode Action 插件（oss-scan-action：oss-pr-scan-action + oss-version-scan-action）
> 关联业务仓：`openlibing-test/oss-scan-action`（master 主内容 + main 多仓测试）· `openlibing-test/openlibing-framework_nightly_test1`（验证仓）
> 关联实现文档：`spec/oss-scan-action/task_design/{oss-pr-scan-action,oss-version-scan-action}/{proposal,design,tasks}.md`

---

## 1. 需求与目标

将原 openlibing PR 流水线「开源漏洞 + license 扫描门禁」环节，从依赖明文 token + 服务端调度的
`openlibing-ci/scan/opensource/scan_vuls.sh`（trivy fs + jq 统计 + 阈值判定），迁移为**自包含、可复用的
GitCode Action 插件**，在目标仓 `.gitcode/workflows/` 中以标准 workflow 方式接入：

- **PR 级**（`oss-pr-scan-action`）：pull_request 预合并代码扫描
- **版本级**（`oss-version-scan-action`）：全量分支扫描（暂 workflow_dispatch 自测，schedule 预留）
- 判定逻辑与 scan_vuls.sh 对齐：高危漏洞/license 计数超门禁则阻断

---

## 2. 开发流程回顾

### 2.1 架构设计

| 决策      | 选择                                                                       | 原因                                                                    |
| --------- | -------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| 插件形态  | node16 + `dist/index.js`（ncc 打包）                                       | 与 malicious-code / sca 插件一致，GitCode 仅支持 node16                 |
| 共享核心  | 抽取 `shared/index.js`（扫描/解析/判定/summary）                           | PR/version 逻辑一致，单一维护点                                         |
| 认证/凭据 | 无 OIDC、无 AK/SK、插件不接收 token                                        | 本地 trivy 扫描不调平台 API；代码由 checkout + secrets.ROBOT_TOKEN 获取 |
| 漏洞库    | 复用 runner 预置 `/opt/cached_resources/trivy_db`；不传 `--skip-db-update` | 对齐原脚本，库过期自动联网更新                                          |
| 分支策略  | master（只扫本仓）/ main（多仓 scan-repository）                           | 避免 master 潜在越权，main 保留跨仓能力                                 |

### 2.2 核心开发与关键修复

1. **trivy 报告对象解析 bug**：`extractRiskCounts` 补齐顶层 `{SchemaVersion, Results:[...]}` 解包
   （此前永远 0 漏洞假通过）——commit `8ce19e6` / `39d05e1`。
2. **运行时依赖解析漏检（本次最大问题）**：
   - 现象：同一执行机第一次能扫出 9/50 漏洞，之后 0 漏洞
   - 根因：trivy 扫 pom 传递依赖需实时访问公共 Maven Central，被 **429 限流** + 私有构件 **404**
     → 传递依赖解析不出 → 漏洞全在间接依赖中 → 必漏检；且与"更新漏洞库"无因果关系（两条独立网络线）
   - 修复（方案 A）：扫描前 `mvn dependency:resolve` 填充 `~/.m2`（先离线 -o 后在线，超时 600s，失败降级）
     ——shared 新增 `findMavenProjectDir` + `runMavenResolve`（commit `8cc3159`）
   - 验证：a959 补齐环境后，10→255 包 / 0→50 漏洞
3. **四级别门禁参数**：从旧 `ignore-vuln-count/ignore-license-count`（HIGH/CRITICAL 合并）改为
   8 个独立 limit 参数（vuln/license × CRITICAL/HIGH/MEDIUM/LOW，默认 0/0/1000/1000）；
   CRITICAL/HIGH 超门禁阻断，MEDIUM/LOW 超门禁仅提示，UNKNOWN 不统计
   ——commit `3855f73`/`e828128`
4. **license 门禁默认值调整**：50/50/1000/10000（用户需求）——commit `142c3ae`/`f21689c`
5. **PR checkout 显式 ref（平台适配）**：
   - 现象：pull_request 事件下 checkout 报 `couldn't find remote ref refs/merge-requests/1/merge`
   - 根因：GitCode 平台只发布 `refs/merge-requests/N/head`，无 `merge` 预合并 ref；裸 checkout 拉 merge 失败
   - 修复：显式 `ref: ${{ atomgit.event.pull_request.head.sha }}`（commit `062c0b3`）
   - 二次踩坑：该 workflow 多事件共用（PR/push/dispatch），push 事件下 head.sha 为空 →
     checkout 报 `Input required: COMMIT_REF_NAME`
   - 最终：三事件兼容 `ref: ${{ event_name=='pull_request' && head.sha || atomgit.sha }}`（commit `cec6a24`/`4fac3f7`）
6. **undici 高危漏洞升级**：`@actions/core 1.11.1 → 3.0.1`（http-client 4.0.1 → undici 6.28.1），
   消除 CVE-2026-12151/1526/2229——commit `c5d123c`/`8ca2dd9`
   - **二次踩坑**：仅升两个插件子目录，漏了**根目录 `package.json`**，trivy 扫根 node_modules 仍报 5.29
     → 补升级根依赖（commit `a165dba`/`0d3ad2d`）

---

## 3. 执行机环境准备（非代码，但决定成败）

| 执行机        | 角色   | trivy                   | mvn/JDK          | 私仓凭据                        |
| ------------- | ------ | ----------------------- | ---------------- | ------------------------------- |
| ecs-vul-a959  | 版本级 | 0.69.0 @ /usr/local/bin | JDK17+Maven3.9.9 | **预置**于 `/etc/environment`   |
| ecs-2176-7dbc | PR 级  | 0.69.1 @ /usr/bin       | 后补             | **后补**写入 `/etc/environment` |

**关键结论**：

- 框架仓 `.mvn/settings.xml` 私仓凭据是占位符 `${openlibing_mvn_repo_username/password}`，
  必须由**执行机环境变量**提供；`.mvn/maven.config` 的 `-s` 强制项目级配置，替换系统 settings 无效。
- **systemd 服务默认不读 `/etc/environment`**——要让 runner 进程拿到变量，必须在 service 加
  `EnvironmentFile=/etc/environment` + `daemon-reload` + `restart`，并以 `/proc/<MainPID>/environ`
  为最终判据（不能只看 shell）。
- 两机均需首次 `mvn dependency:resolve` 填充 `~/.m2`，否则 trivy 只有直接依赖。

---

## 4. 经验教训（可复用）

1. **不迷信"更新漏洞库→能扫出"**：trivy 依赖解析（拉远程 pom）与漏洞库更新是两条独立网络线，
   能扫出多少取决于"那一刻能否躲开 Maven Central 限流"——是时序巧合，不是因果。
2. **排查漏检先看 `Packages` 结构，不看漏洞数**：包数≈直接依赖数且 `indirect=0` → 解析层问题，
   不是库/CVE 过滤问题。
3. **`trivy --debug` 的 `[pom] Failed to fetch ... statusCode=` 是最有效抓手**：404=不存在、429=限流。
4. **公共 Maven Central 高频拉取会限流**：把"运行时现拉公共仓库"当稳定通道是错误假设；
   正确姿势是让依赖字典（本地仓库 `~/.m2` / SBOM）先就绪再一次性查全。
5. **GitCode checkout 在 pull_request 事件需显式 ref**：平台只给 `refs/merge-requests/N/head`，
   无 `merge` 预合并 ref；裸 checkout 报 couldn't find remote ref。
6. **多事件共用 workflow 时 ref 要按事件兜底**：`event_name=='pull_request' && head.sha || atomgit.sha`，
   否则 push/dispatch 下空 ref → `COMMIT_REF_NAME`。
7. **"写进环境配置文件" ≠ "进程能读到"**：systemd 服务默认不读 `/etc/environment`，
   需 `EnvironmentFile=` + 重启，以 `/proc/<PID>/environ` 判据。
8. **升级依赖要覆盖所有包目录**：npm 多包仓（根 package.json + 各插件子包）都要升，只升子目录
   会让 trivy 扫根 node_modules 报旧版本。
9. **私有构件出现在中央仓库请求里 404**：本身就是"该走公司内网 Maven"的信号。

---

## 5. 交付物与当前状态

| 仓                      | 分支                                    | 产出                                                                       |
| ----------------------- | --------------------------------------- | -------------------------------------------------------------------------- |
| oss-scan-action         | master/main                             | 插件代码 + shared 引擎 + dist + 单测（PR 27 / version 22 全绿）+ workflows |
| openlibing-docs         | spec/oss-scan-action/oss-pr-scan-action | proposal/design/tasks（已更新四级别门禁 + maven 预解析 + checkout ref）    |
| framework_nightly_test1 | master                                  | 验证 workflow（checkout 显式 ref + oss-pr-scan 接入）                      |
| openlibing-ci           | fix/oss-scan-mvn-resolve-no-license     | scan_vuls.sh 同步 maven 预解析（license 保留）                             |

**验证通过项**：方案 A 并行验证（255 包/50 漏洞）、单测全绿、dist 重建、远端 workflows 实跑、7dbc 环境收尾。
**遗留/待办**：Phase 4 业务 PR 交付、Phase 5 最终归档（用户触发）。

---

## 6. 核心文档速查

- 平台 checkout/权限语义：`https://docs.gitcode.com/docs/help/home/org_project/pipeline/security-permissions/pr-mr-pipeline-security`
- 官方 PR checkout 示例（显式 ref）：`https://docs.gitcode.com/docs/help/home/org_project/pipeline/examples/pr-code-check-example`
- 运行时上下文变量：`https://docs.gitcode.com/docs/help/home/org_project/pipeline/action-development/runtime-environment-variables`
- trivy 官方：Java 覆盖 / air-gap / databases（依赖解析与限流依据）
