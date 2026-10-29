# 插件结果输出增加openLiBing平台扫描结果链接 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/code-metrics-action/issues/25
- **对应task(issueID)链接**: https://gitcode.com/openlibing/code-metrics-action/issues/25
- **需求名称**: 插件结果输出增加openLiBing平台扫描结果链接
- **开发责任人**: 闫兆鸿
- **测试责任人**: 徐愚冰
- **最终结论**: 通过
- **测试维度**:
- [x] **功能自检测试**
- [ ] **体验测试**
- [ ] **集成测试**
- [ ] **安全与隐私测试**
- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

> 说明：被测对象为 security-compilation-options-action 与 code-metrics-action 两个 Node 自定义 action 在 CI 运行时向 `ATOMGIT_STEP_SUMMARY` / `ATOMGIT_OUTPUT` 的输出行为（对应系统测试/CI 输出），服务端（openlibing-cicd / openlibing-coderepo）上报接口由开发单测覆盖、测试侧不直连。安全 6 维度均豁免（上报接口鉴权方式与路径不变；无用户/资源维度变更；无角色模型变更；未变更协议与宿主地址；机机接口无 Web 会话；链接/tip 仅含 projectId、仓库、分支与平台授权标识）。

## 2. 测试过程

### 2.1 功能测试专项

**1.安全编译选项插件链接输出（子需求一）**:

- 预期结果: 上报成功后按每个产物包输出 1 条「安全编译选项扫描结果（<包名>）」链接（多包逐包、包名对应）；双通道输出（`ATOMGIT_STEP_SUMMARY` Markdown 超链接 + `ATOMGIT_OUTPUT` key=value，key 末尾为小写 `url`）
- **测试结果**： Passed（TC-ISSUE25-001 run 8fc296f3；TC-ISSUE25-002 run b019f5a3 / aef6eafb）
- **证明截图**: 待补充

**2.安全编译选项插件未录入 tip 与上报失败**:

- 预期结果: 仓未录入平台时输出服务端固定 tip 文案而非链接；上报失败时无链接/提示且主流程不中断
- **测试结果**： Passed（TC-ISSUE25-003 run 32ac8f4c；TC-ISSUE25-004 run 44f411ce）
- **证明截图**: 待补充

**3.安全编译选项插件双鉴权与存量输出无回退**:

- 预期结果: AK/SK 与 OIDC 两条上报路径均输出链接；既有安全编译选项开启率/计数输出格式与内容不变
- **测试结果**： Passed（TC-ISSUE25-007；TC-ISSUE25-008 run 8fc296f3）
- **证明截图**: 待补充

**4.代码度量插件链接输出（子需求二）**:

- 预期结果: 上报成功后输出固定单条「代码度量指标扫描结果」链接（不按 5 类指标拆分）；双通道输出；点击落地平台代码仓度量详情页并按仓库筛选置顶
- **测试结果**： Passed（TC-ISSUE25-009 run 6e3339de；TC-ISSUE25-010）
- **证明截图**: 待补充

**5.代码度量插件两类提示与上报失败**:

- 预期结果: 仓未录入/分支未登记两类场景输出对应 tip 文案；上报失败不输出链接/提示、扫描正常完成
- **测试结果**： Passed（TC-ISSUE25-011，仓未录入 tip 通过 run c473f6ec；分支未登记 tip 未复现，见遗留项；TC-ISSUE25-012 run 44f411ce）
- **证明截图**: 待补充

**6.代码度量插件双鉴权与存量指标无回退**:

- 预期结果: AK/SK 与 OIDC 两条上报路径均输出链接；既有 5 项代码度量指标输出正常
- **测试结果**： Passed（TC-ISSUE25-015 run 3563c194；TC-ISSUE25-014 run 6e3339de）
- **证明截图**: 待补充

**7.跨插件联合场景**:

- 预期结果: 同一流水线内两个插件任务均输出各自链接
- **测试结果**： Passed（TC-ISSUE25-022 run 6d9b14b5）
- **证明截图**: 待补充

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                                                                                  | 通过数 | 不通过数 | 结论   |
| ------------ | -------- | ----------------------------------------------------------------------------------------------- | ------ | -------- | ------ |
| **功能测试** | 13       | 双插件双通道链接输出、多包/单条、未录入 tip、上报失败不输出、双鉴权、存量输出无回退、跨插件联合 | 13     | 0        | Passed |

> 用例等级 L0 3 / L1 10；手工 13；通过率 100%，无失败、无阻塞、无跳过。

## 4. 遗留问题与风险说明

| 缺陷 ID | 缺陷描述                 | 严重程度 | 处理意见 |
| ------- | ------------------------ | -------- | -------- |
| —       | 无 fail 用例，本轮无缺陷 | —        | —        |

**遗留项 / 范围说明**：

- **服务端接口契约不单独做测试侧直连**：`/build-artifact/sec-option/report`（cicd）与 `/metrics/code/report`（coderepo）仅由插件内部机机调用、非用户入口；接口契约与边界逻辑由开发服务端单测覆盖（cicd `SecOptionScanServiceImplTest` 54/54；coderepo `CodeMetricsServiceImplTest` 46/46、`CodeMetricsControllerTest` 5/5、`CodeMetricsImportConsumerTest` 5/5）。
- **「分支未登记」tip 未复现（TC-ISSUE25-011）**：全新未登记分支上运行仍返回链接，疑似上报入库即建立分支记录；属极端场景，已记录。
- **AK/SK 成功路径**：本轮以 OIDC 路径验证通过；AK/SK 成功路径遗留待网关侧为 app 开通/更换有效 AK/SK 后重跑。
- **缺环境变量、特殊字符/编码等 CI 环境无法构造的场景**，由开发《需求开发自验证》覆盖（24/24 通过）。

## 5. 补充说明

1. 本报告对应 issue https://gitcode.com/openlibing/code-metrics-action/issues/25；关联实现 PR：code-metrics-action #32（`scan-result-drilldown-link`）、security-compilation-options-action #27（`scan-result-drilldown-link`）、openlibing-cicd #598、openlibing-coderepo #215。
2. 测试范围按"用户入口"收敛：仅覆盖插件链路（用户可见），不对非用户入口的服务端接口做直连测试。
3. 数据来源：issue 目录 `测试过程数据/测试策略.md`、`测试过程数据/测试报告.md`、`测试反串讲.md`、`需求开发自验证.md`。
