# 【openlibing】GitCode插件流水线交互适配OIDC认证方案 测试报告

## 1. 基本信息

* **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2106360192
* **对应task(issueID)链接**: https://gitcode.com/openlibing/code-metrics-action/issues/8
* **需求名称**: 【openlibing】GitCode插件流水线交互适配OIDC认证方案
* **开发责任人**: 闫兆鸿
* **测试责任人**: 徐愚冰
* **最终结论**: 通过
* **测试维度**:
* [x] **功能自检测试**
* [ ] **体验测试**
* [x] **集成测试**
* [x] **安全与隐私测试**
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.APIG 上报切 OIDC 验证**:
* 预期结果: APIG 上报经 OIDC 链路（SDK callApig 自动换证 + V11 签名 + X-Security-Token）正常完成，自研 ApigSigner 与 axios 已移除
* **测试结果**： Passed
* **证明截图**: 待补充

**2.OBS 上传切 OIDC 验证**:
* 预期结果: obsutil 使用 SDK getCredentials() 返回的 STS 临时凭证 + `-t=<SecurityToken>` 上传成功，静态 obs-ak/obs-sk 不再参与
* **测试结果**： Passed
* **证明截图**: 待补充

**3.action.yml 凭证输入移除验证**:
* 预期结果: action.yml 中 apig-app-key / apig-app-secret / obs-ak / obs-sk 4 个输入项已删除，插件零凭证接入可运行
* **测试结果**： Passed
* **证明截图**: 待补充

**4.workflow 前置声明验证**:
* 预期结果: 接入 workflow 声明 `permissions: id-token: write` 时 OIDC 链路正常，缺失时有明确报错指引
* **测试结果**： Passed
* **证明截图**: 待补充

**5.README 文档同步验证**:
* 预期结果: README 参数表已移除 4 个凭证参数、使用示例含 `permissions: id-token: write`，按文档接入可跑通
* **测试结果**： Passed
* **证明截图**: 待补充

### 2.2 集成测试专项

**1.线上流水线端到端上报验证**:
* 预期结果: workflow_dispatch + schedule 触发均上报成功，后端 openlibing-coderepo 入库正常
* **测试结果**： Passed
* **证明截图**: 待补充

**2.后端契约无感验证**:
* 预期结果: 上报 URL / payload / 响应契约不变，后端 openlibing-coderepo 无配套改动即可正常解析入库
* **测试结果**： Passed
* **证明截图**: 待补充

### 2.3 安全与隐私测试专项

**1.静态凭证清零验证**:
* 预期结果: 插件源码与 action.yml 无 4 个静态凭证引用，workflow secrets 不再分发，运行时无凭证明文
* **测试结果**： Passed
* **证明截图**: 待补充

**2.OIDC 联邦认证与可审计验证**:
* 预期结果: ID Token 由 OIDC Provider 签发，STS 临时凭证时效受限，流水线身份可审计
* **测试结果**： Passed
* **证明截图**: 待补充

## 3. 测试结果汇总表

| 测试维度 | 用例总数 | 重点测试点描述 | 通过数 | 不通过数 | 结论 |
| --- | --- | --- | --- | --- | --- |
| **功能测试** | 5 | APIG 切 OIDC、OBS 切 OIDC、凭证输入移除、workflow 前置声明、README 同步 | 5 | 0 | Passed |
| **集成测试** | 2 | 线上流水线端到端上报、后端契约无感 | 2 | 0 | Passed |
| **安全与隐私测试** | 2 | 静态凭证清零、OIDC 联邦认证可审计 | 2 | 0 | Passed |

## 4. 遗留问题记录

| 序号 | 问题描述 | 严重程度 | 负责人 | 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## 5. 补充说明

1. 本报告对应 issue https://gitcode.com/openlibing/code-metrics-action/issues/8 。
2. 测试维度在 8 月同类认证/服务切换模板基础上，新增集成测试、安全与隐私测试，以覆盖 OIDC 联邦认证、静态凭证清零、临时凭证过期与保底补导入语义等验收重点。
3. 验收以 issue 验收标准为准：插件运行时无任何 AK/SK 依赖、OIDC 链路全流程走通、线上流水线上报成功且后端入库正常、OBS 临时凭证保底补导入语义不变、上报接口契约不变且后端无感。
