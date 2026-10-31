# pr-label-action 安全 issue 分析（#3~#9，open 7 条）

> 分析基准：`fix-security-remediation` 分支（已合 PR #3：API base 白名单 + Bearer 头 + 全链路日志脱敏）。
> 分析日期：2026-10-12。结论仅作整改决策参考，暂不修改代码。
> **状态更新（2026-10-20）**：#3（集中配置化）与 #9（Bearer 收口）已在分支 `fix-issue3-9-config-bearer` 实施完成（src + dist 均已改，待 commit），进入待自测状态；其余 issue 定性不变。
> **状态更新（2026-10-26）**：#3 #9 #5（编码部分）已由 commit `2dd81f9` 提交并推送
> `fix-security-remediation`；#5（白名单拒绝部分）经用户批准后由 commit `ddd0116` 实施并推送
> （`parseLabels` 校验失败即终止，含 `/ ? # ,` 控制字符的标签名被拒，正常标签不受影响）。
> 本仓全部可实施项已完成，统一测试分支为 `fix-security-remediation`。

## 汇总

| 分类 | Issue | 处理建议 |
|---|---|---|
| 已实施待自测（2026-10-20） | #3 | 方案 B 集中配置化已在 `fix-issue3-9-config-bearer` 实施：`src/config/endpoints.js` 新建 + `resolveApiBase` 改读配置 + dist 重建；待 commit / 同步统一测试分支 / 用户自测。注意：dist 中 URL 以 `GITCODE_API_BASE:"https://api.gitcode.com/api/v5"` 配置值形态存在（ncc 打包注入），扫描器是否仍命中待下轮扫描验证 |
| 已修复（PR #3）+ 残留随 #9 收口（已实施待自测） | #4 | 日志脱敏 + Bearer 头已做；残留的 addLabel/fetchLabels `?access_token=` 拼接已随 #9 删除（2026-10-20），双通道已消除 |
| 已实施待自测（2026-10-20） | #9 | 两处 `?access_token=${token}` 拼接已删（addLabel / fetchLabels），全接口统一 Bearer 头（等价变换），src + dist 均已改，待 commit / 用户自测（实跑打标/清标签工作流，三接口 2xx 无 401） |
| 真问题·等价加固（可直接做，待实施） | #5（编码部分） | ✅ 已实施（`2dd81f9`）：标签名 `encodeURIComponent` |
| ✅ 已实施（2026-10-26 用户批准） | #5（白名单拒绝部分） | 新增输入拒绝，属硬规则 2 第 5 类；`ddd0116`：`parseLabels` 拒绝含 `/ ? # ,` 控制字符的标签名，当前调用点均为常量标签不受影响 |
| 不是问题 | #6 #7 | #6 见第四节详述；#7 见第四节详述（2026-10-13 用户决策） |
| 真问题·暂缓（2026-10-20 用户决策） | #8 | 属逻辑 bug，整改涉及业务逻辑改动，暂不处理 |

---

## 一、已部分修复

### #3 SecInfo：硬编码公网地址（GitCode API 默认地址）

- **状态**：✅ **已实施待自测（2026-10-20，方案 B 集中配置化）**
- **位置**：`resolveApiBase` 兜底返回值（src/index.js:111-112）
- **已做（PR #3，第一轮）**：默认值保留 + `gitleaks:allow` 白名单注释，注释说明"功能必需的 API 默认回退地址，运行时优先使用环境变量注入"（ATOMGIT_API_URL / ATOMGIT_SERVER_URL 优先级更高，属等价变换）
- **第一轮残留**：dist/index.js 为 ncc 打包产物，**注释在打包时被剥离**（dist 全文检索 `gitleaks:allow` 命中 0 次），而 issue #3 告警明细同时列了 src 与 dist 两处——扫描器下次扫 dist 仍会命中
- **已实施（方案 B，2026-10-20，与 upload-sarif-action #10 统一模式）**：
  - 新建 `src/config/endpoints.js`：`GITCODE_API_BASE`（https://api.gitcode.com/api/v5）迁入，默认值与原硬编码逐字一致（等价变换）
  - `resolveApiBase` 兜底返回值改 `require("./config/endpoints").GITCODE_API_BASE`（src/index.js:112），src 不再内联 URL 字面量
  - dist 已重建：URL 以配置模块形式打包（`e.exports={GITCODE_API_BASE:"https://api.gitcode.com/api/v5"}`），属性名 `GITCODE_API_BASE` 随包保留
  - ATOMGIT_API_URL / ATOMGIT_SERVER_URL 环境变量优先级不变
- **遗留观察**：dist 中 URL 字符串仍以配置值形态存在 1 处（ncc 打包的固有行为，与 upload-sarif-action #10 相同）；扫描器下轮是否仍命中 dist 待验证，若仍命中需评估扫描器白名单登记
- **分支状态**：分支 `fix-issue3-9-config-bearer`，src + dist 改动在工作区待 commit；commit 后需同步 `fix-security-remediation` 统一测试分支
- **不处理项**：issue 无其他噪音条目（本仓仅此一个地址）

### #4 SENS-11：access_token URL 传输 + 响应日志未脱敏

- **已做（PR #3）**：① 令牌改 `Authorization: Bearer` 头传递（httpRequest 统一注入，src/index.js:161-163）；② 全链路日志脱敏：请求 URL/请求头/请求体/响应头/响应体/错误消息统一过 `redact()`（src/index.js:44-59），含 URL query 形态与 Bearer 形态双重兜底
- **残留**：`addLabel` 与 `fetchLabels` 的 endpoint 仍拼 `?access_token=${token}`——双通道并存（与 #9 同一根因）
- **收口（2026-10-20，随 #9 已实施待自测）**：两处 query 拼接已删，双通道已消除；本 issue 全部整改点完成

---

## 二、真问题·方案已定（Bearer 官方支持）

### #9 红线 7.1.11：标签接口 access_token 拼入 URL 查询串

- **状态**：✅ **已实施待自测（2026-10-20）**
- **位置**：原 addLabel（src/index.js:170 附近）、fetchLabels（src/index.js:207 附近）；实施后两处 endpoint 均已回归纯路径形态（src/index.js:185 有收口注释）
- **核实**：真实（即已知的双通道半整改状态）。当前请求已带 Bearer 头，query 参数属历史遗留冗余
- **关键疑虑已消除（2026-10-16 用户确认）**：GitCode 官方文档明确**游客可使用 Bearer 头发起请求**——Bearer 通道为官方支持的合法鉴权方式，原"v5 规范仅支持 query 鉴权"的担忧不成立，无需再实测双通道对比
- **已实施（决策树「Bearer 可用」分支，2026-10-20）**：
  - 删除 addLabel / fetchLabels 两处 `?access_token=${token}` query 拼接，endpoint 回归纯路径形态（已核实 src 全文无残留 `access_token=` 拼接，仅 redact 正则保留该形态的脱敏匹配）
  - 全接口统一 `Authorization: Bearer` 头通道（httpRequest 已统一注入），消除双通道并存（半整改状态）
  - 属等价变换：鉴权协议语义不变（同一 token、同一接口、同一操作），仅传输通道收口；dist 已同步重建（dist 中 `access_token=` 仅命中 redact 正则 2 处，无真实拼接）
- **分支状态**：分支 `fix-issue3-9-config-bearer`（与 #3 同批，同属鉴权/配置链路强耦合，合并一个 PR），改动在工作区待 commit；commit 后需同步 `fix-security-remediation` 统一测试分支
- **自测要点**：实跑一次 PR 打标 / 清标签工作流，确认 addLabel（POST）、fetchLabels（GET）、removeLabel（DELETE）三接口均 2xx，无 401

---

## 三、真问题·等价加固（可直接做）

### #5 输入校验：标签名未校验未编码，拼入 URL 路径与请求体【低危】
- **位置**：`parseLabels`（[src/index.js:38-45](file:///e:/work/huawei/fork/pr-label-action/src/index.js#L38-L45)）仅拆分 trim；`removeLabel` 的 `labels/${labelName}`（src/index.js:171）直接拼路径
- **拆分定性**：
  - **`encodeURIComponent(labelName)` → 等价加固，可直接做**：正常标签名编码前后语义一致，行为不变
  - **白名单拒绝含 `/ ? # \n ,` 的标签名 → 新增输入拒绝（硬规则 2 第 5 类），须评审**：需确认现网工作流是否有传入特殊字符标签名的合法用法（当前所有调用点传入的都是字面量常量标签，实际风险低）
- **攻击前提**：需工作流把不可信事件数据（如 PR 自带标签）透传进 add_labels/remove_labels 输入，当前 workflow 均为常量传参，属纵深防御

---

## 四、不是问题

### #7 CI 供应链：Action 与 pre-commit 钩子以可变 tag 引用【非问题（2026-10-13 用户决策）】

- **原始描述**：[.gitcode/workflows/pre-commit.yml:31/70/83](file:///e:/work/huawei/fork/pr-label-action/.gitcode/workflows/pre-commit.yml#L31) 的 `pr-label-action@v1.0.0`、`pre-commit-action@v1.0.1`，及 [.pre-commit-config.yaml:8/25](file:///e:/work/huawei/fork/pr-label-action/.pre-commit-config.yaml#L8) 的 `rev: v6.0.0`、`rev: v8.30.1` 均为可变 tag 引用
- **定性理由**：tag 引用升级方便、易用性好，是**有意的易用性设计取舍**——固定 SHA 后每次升级都要手动换 40 位哈希，运维成本明显；且引用对象均为公司自维护仓（pr-label-action / pre-commit-action）与知名开源工具官方发布 tag，投毒面可控。插件侧不整改，可回复说明后关闭

### #6 pwn request：特权上下文执行不可信 PR 代码【非问题（2026-10-13 用户决策）】

- **原始描述**：`pull_request_target` + `pull_request_comment` 触发、checkout 与 pre-commit-action 均携带 ROBOT_TOKEN、npm install 于 PR 检出目录执行、自托管 runner + `pr: write`，构成 pwn request 风险面
- **定性理由**：与 pre-commit-action #20、upload-sarif-action #17 同类，**该工作流模式是平台 CI 门禁的业务设计确定**——PR 门禁必须在特权上下文对 PR 合并结果执行检查，属门禁系统的固有形态；issue 引用的 `allow-unsafe-pr-checkout: true` 在当前工作流中不存在，与实际版本不符。插件侧无可整改项，可回复说明后关闭
- **备注**：ROBOT_TOKEN 轮换与 CI 日志审计为平台侧运维事项，不属插件安全整改范畴

---

## 五、真问题·暂缓（用户决策）

### #8 PR 状态标签并发竞态（TOCTOU）【低危·暂缓（2026-10-20 用户决策）】

- **位置**：`fetchLabels`（src/index.js:198-225）读取 → main 过滤（src/index.js:330-340）→ 逐个 add/remove（src/index.js:369-388），全程无锁非原子
- **核实**：真实。并发触发（快速多次评论 / push 与 PR 事件交错）时 passed/failed 可并存；单步删除失败时互斥标签共存是确定性的。下游若以标签作合并门禁会误判
- **为什么暂缓**：三个候选修法都不是插件单方面等价变换，属业务逻辑改动——① 工作流层 concurrency 串行化（改各仓 workflow 配置）；② 平台原子批量标签接口（依赖 GitCode API 能力）；③ 写后复核重试（改变失败语义，可能引入重试循环）。**2026-10-20 用户决策：属逻辑 bug，有业务逻辑上的改动，暂时先不管**
- **缓解现状**：当前门禁消费方是否真正依赖标签互斥需业务确认，低危
