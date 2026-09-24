# 【openlibing】GitCode插件流水线交互适配OIDC认证方案 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2106360192
* **对应task(issueID)链接**: https://gitcode.com/openlibing/code-metrics-action/issues/8
* **需求名称**: 【openlibing】GitCode插件流水线交互适配OIDC认证方案
* **核心目标**:
  将代码度量扫描插件（code-metrics-scan）上报链路由 APIG App 认证（apig-app-key / apig-app-secret）+ OBS 静态密钥（obs-ak / obs-sk）全面切换为 OIDC 联邦认证，插件零凭证接入，OIDC 链路（ID Token → STS 换证 → V11 签名 / OBS 临时凭证）全流程走通，上报接口契约（URL / payload / 响应）不变，后端 openlibing-coderepo 无感。
* **开发责任人**: 闫兆鸿
* **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

* [x] **功能自检测试**
> * **测试重点:** APIG 上报切 OIDC（SDK callApig 替代 ApigSigner）、OBS 上传切 OIDC（STS 临时凭证）、action.yml 凭证输入移除、workflow 前置声明（id-token: write）、README 文档同步。
> * **目的:** 确保插件 OIDC 链路各环节正常、零凭证接入生效、文档与实现一致。
> * **触发条件:** 强制执行。

* [ ] **体验测试**

* [x] **集成测试**
> * **测试重点:** 线上流水线（workflow_dispatch + schedule）端到端上报、后端 openlibing-coderepo 入库、上报接口契约不变。
> * **目的:** 确保切换后线上流水线上报成功且后端无感。
> * **触发条件:** 强制执行。

* [x] **安全与隐私测试**
> * **测试重点:** 运行时无任何 AK/SK 依赖、workflow secrets 不再分发 4 个长期静态凭证、OIDC 联邦认证可审计流水线身份、STS 临时凭证时效受限。
> * **目的:** 确保凭证泄露面收敛、接入成本降低、流水线身份可审计。
> * **触发条件:** 强制执行（认证方案改造必选）。

* [ ] **可靠性与韧性测试**

* [ ] **可服务性与可观测性测试**

* [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.APIG 上报切 OIDC 验证**:
* 前置条件: 已引入 `@openlibing/huaweicloud-oidc-client@0.0.3`，`CoderepoUploader` 改用 SDK `callApig`
* 测试步骤:
    1. 触发插件上报，验证 SDK `callApig` 自动换证 + V11 签名 + 携带 X-Security-Token
    2. 确认自研 `ApigSigner`（SDK-HMAC-SHA256）已移除、axios 依赖已移除
    3. 验证上报请求到达 APIG 且后端正常接收
* 预期结果: APIG 上报经 OIDC 链路正常完成，旧签名实现与 axios 已清除

**2.OBS 上传切 OIDC 验证**:
* 前置条件: obsutil 凭证改为 SDK `getCredentials()` 获取的 STS 临时凭证
* 测试步骤:
    1. 触发 OBS 上传，验证 obsutil 使用 `-t=<SecurityToken>` 携带临时凭证
    2. 确认不再读取静态 obs-ak / obs-sk
    3. 验证上传对象成功且语义与改造前一致
* 预期结果: OBS 上传使用 STS 临时凭证成功，静态 AK/SK 不再参与

**3.action.yml 凭证输入移除验证**:
* 前置条件: action.yml 已删除 apig-app-key / apig-app-secret / obs-ak / obs-sk
* 测试步骤:
    1. 检查 action.yml inputs，确认 4 个凭证输入项不存在
    2. 以零凭证方式接入 workflow，触发插件运行
    3. 验证插件无需任何凭证输入即可完成上报
* 预期结果: 插件零凭证接入，运行时不依赖任何静态凭证输入

**4.workflow 前置声明验证**:
* 前置条件: 接入方 workflow 已新增 `permissions: id-token: write`
* 测试步骤:
    1. 检查接入 workflow YAML，确认 `permissions: id-token: write` 已声明
    2. 缺失该声明时触发插件，验证 OIDC 换证失败并有明确报错
    3. 补齐声明后再次触发，验证 OIDC 链路正常
* 预期结果: 前置声明存在时 OIDC 链路正常，缺失时有明确报错指引

**5.README 文档同步验证**:
* 前置条件: README 参数表与使用示例已更新
* 测试步骤:
    1. 检查 README 参数表，确认 4 个凭证参数已移除、`permissions: id-token: write` 已写入示例
    2. 按README示例接入新 workflow，验证可跑通
* 预期结果: 文档与实现一致，按文档接入可正常运行

### 3.2 集成测试专项

**1.线上流水线端到端上报验证**:
* 前置条件: 线上 workflow（workflow_dispatch + schedule）已切换 OIDC 接入方式
* 测试步骤:
    1. 手动触发 workflow_dispatch，验证插件上报全流程成功
    2. 等待 schedule 触发，验证定时上报成功
    3. 在后端 openlibing-coderepo 验证度量数据入库正常
* 预期结果: 线上流水线上报成功，后端入库正常

**2.后端契约无感验证**:
* 前置条件: 插件已切 OIDC，后端 openlibing-coderepo 未做配套改动
* 测试步骤:
    1. 对比改造前后上报 URL、payload 结构、响应字段
    2. 验证后端按原契约正常解析入库
* 预期结果: 上报接口契约不变，后端 openlibing-coderepo 无感

### 3.3 安全与隐私测试专项

**1.静态凭证清零验证**:
* 前置条件: 插件已切 OIDC 接入
* 测试步骤:
    1. 全量检索插件源码与 action.yml，确认无 apig-app-key / apig-app-secret / obs-ak / obs-sk 引用
    2. 检查 workflow secrets，确认 4 个长期静态凭证不再被分发/引用
    3. 运行时抓包/日志确认无静态凭证明文
* 预期结果: 运行时无任何 AK/SK 依赖，凭证泄露面收敛

**2.OIDC 联邦认证与可审计验证**:
* 前置条件: OIDC 链路已打通
* 测试步骤:
    1. 验证 ID Token 由 GitHub/GitCode OIDC Provider 签发
    2. 验证 STS 换证返回临时凭证且时效受限
    3. 验证上报日志/审计可关联到具体流水线身份
* 预期结果: 联邦认证链路可信，流水线身份可审计
