# #1 openLiBing用户&权限管理功能整改 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/34
* **需求名称**: openLiBing用户&权限管理功能整改
* **开发责任人**: zhuangzhiting
* **测试责任人**: fanshijing
* **最终结论：**： 通过
* **测试维度** ：
* [X] **功能自检测试**
* [X] **性能测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [ ] **安全与隐私测试**
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**

---

## 2. 测试过程

本次测试全面覆盖openLiBing用户与权限管理功能整改的各个核心业务场景，包括用户信息管理、权限审核、项目管理、权限申请和转审流程等，共执行10个功能性测试用例和1个性能测试用例，所有测试用例均通过验证。

### 2.1 功能测试专项

#### 2.1.1 用户信息管理功能测试

**1.华为用户信息查询接口验证**
* **用例编号**: 314
* 前置条件：已登录openLiBing系统，已绑定华为账号
* 测试步骤：
  1. 调用查询接口，验证能够查询出openLiBing绑定的华为用户信息
  2. 验证返回数据包含完整的时间段、uniportal账号信息
  3. 验证能够查询包含uniportal的某一时间段内的华为账号信息
  4. 验证能够查询并列出所有已绑定uniportal账号信息
* 预期结果：
  * 接口能够正确返回openLiBing绑定的华为用户信息
  * 数据格式符合规范，字段完整准确
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1n000117o1dmtk&detail=base

**2.权限审核页面信息展示**
* **用例编号**: 313
* 前置条件：已登录openLiBing系统，有权限审核权限
* 测试步骤：
  1. 进入权限审核页面
  2. 点击权限申请单中的"查看申请人信息"按钮
  3. 验证能够查看申请人邮箱、uniportal账号信息
  4. 验证信息展示字段完整准确，布局合理
* 预期结果：
  * 权限审核页面能够正确显示申请人邮箱、uniportal账号信息
  * 字段展示完整，信息准确，便于审核人员快速了解申请人详情
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1o000117nvt2kn&detail=base

**3.项目管理页面备注功能**
* **用例编号**: 312
* 前置条件：已登录openLiBing系统
* 测试步骤：
  1. 进入项目管理页面
  2. 验证未登录过openLiBing的账号在备注列进行展示备注
  3. 验证备注信息准确完整，便于管理员识别未激活账号
* 预期结果：
  * 未登录过openLiBing的账号在备注列正确展示备注信息
  * 备注内容清晰，便于项目管理
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb21000117nntlvs&detail=base

**4.用户邮箱解绑功能**
* **用例编号**: 311
* 前置条件：已登录openLiBing系统，已绑定邮箱
* 测试步骤：
  1. 进行用户邮箱解绑操作
  2. 验证解绑后不退出登录，保持当前登录状态
  3. 验证解绑状态正确更新，邮箱绑定关系解除
* 预期结果：
  * 用户邮箱解绑成功，操作流畅
  * 解绑后不退出登录，保持登录状态，用户体验友好
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1v000117nnqkm3&detail=base

#### 2.1.2 权限申请与审批流程测试

**5.权限申请按钮功能**
* **用例编号**: 310
* 前置条件：已登录openLiBing系统，在项目页面
* 测试步骤：
  1. 点击权限申请按钮
  2. 验证能够主动选中并申请项目权限
  3. 验证申请流程正常，界面交互清晰
  4. 验证申请成功后正确跳转到我的申请页面
* 预期结果：
  * 点击权限申请按钮后，能够主动选中并申请项目权限
  * 申请成功后跳转到我的申请页面，流程闭环
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1o000117nnmh7s&detail=base

**6.申请权限审批链接管理**
* **用例编号**: 309
* 前置条件：已提交权限申请
* 测试步骤：
  1. 申请权限，提交成功后跳转到我的申请页面
  2. 验证我的申请页面可以提供对应审批链接
  3. 点击链接验证能够复制功能，方便分享
  4. 验证分享链接能够跳转到我的申请页面，便于审批人快速访问
* 预期结果：
  * 我的申请页面提供审批链接，便于分享和追溯
  * 链接复制功能正常，分享链接跳转正确
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1v000117nng5c4&detail=base

**7.代办中心提示功能**
* **用例编号**: 308
* 前置条件：有新的代办任务
* 测试步骤：
  1. 提交新的代办任务（如权限申请）
  2. 验证代办中心显示红色数字提示，醒目提醒
  3. 验证提示数量准确，与实际代办数量一致
  4. 验证点击提示能够正确跳转到代办详情页面
* 预期结果：
  * 代办中心显示红色数字提示，视觉醒目
  * 提示数量与实际代办数量一致，信息准确
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb21000117nn8eud&detail=base

**8.重复提交申请验证**
* **用例编号**: 307
* 前置条件：已提交过项目权限申请
* 测试步骤：
  1. 申请项目成员权限，提交成功
  2. 重复申请同一项目权限
  3. 验证提示申请已存在并跳转页面，避免重复申请
  4. 验证跳转到我的申请页面，展示已有申请详情
* 预期结果：
  * 重复提交申请时，提示申请已存在，防止重复操作
  * 正确跳转到我的申请页面，便于查看申请状态
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1v000117nmtkki&detail=base

#### 2.1.3 权限转审与接口规范测试

**9.接口权限返回值规范验证**
* **用例编号**: 345
* 前置条件：已登录openLiBing系统，无接口权限
* 测试步骤：
  1. 对openLiBing配置接口发起403异常请求
  2. 验证返回格式为"无权限，需申请权限账号"提示信息
  3. 验证无权限提示格式为"无权限，请申请权限账号"
  4. 验证openLiBing无权限提示页面显示无权限账号信息
  5. 验证openLiBing合法访问提示权限后颜色提示用户
* 预期结果：
  * 接口403异常返回格式符合规定，提示信息规范统一
  * 提示信息准确，符合设计规范，便于用户理解权限状态
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1p000119057fbm&detail=base

**10.申请单转审流程验证**
* **用例编号**: 315
* 前置条件：已登录openLiBing系统，有转审权限，用户有权限申请单等待审核
* 测试步骤：
  1. 进入转审按钮，跳转转审列表页面
  2. 对比用户是否有审批单，对比列表页，确保数据一致性
  3. 选择转审人，点击转审按钮
  4. 验证转审成功，被转审人收到转审邮件通知
  5. 验证转审日志记录正确，便于追溯审批流程
* 预期结果：
  * 转审按钮跳转正确，转审列表页面数据与审批单列表一致
  * 转审成功，邮件发送正常，日志记录完整准确
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb21000117o85j6b&detail=base

### 2.2 性能测试专项

**11.接口响应时间性能验证**
* **用例编号**: 350
* 前置条件：已登录openLiBing系统
* 测试步骤：
  1. 全量查询绑定openLiBing的uniportal账号的华为信息
  2. 验证接口响应时间不超过3秒，满足性能指标
  3. 进行时间段查询验证响应时间不超过3秒
  4. 进行编号查询验证响应时间不超过3秒
  5. 验证不同查询方式下性能表现稳定
* 预期结果：
  * 接口响应时间不超过3秒，满足性能要求
  * 不同查询方式响应时间均满足性能指标，性能稳定
* **测试结果**： Passed
* **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1n00011709qaqn&case_id=vb1v000119964if7&detail=base

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 10    | 覆盖用户信息管理、权限审核、项目管理、权限申请、转审流程等全流程核心业务逻辑 | 10   | 0    | Pass           |
| **性能测试**    | 1    | 接口响应时间不超过3秒的性能基准验证 | 1   | 0    | Pass           |
| **集成测试**    | 0    | -      | 0   | 0    | Pass           |
| **安全与隐私测试** | 0    | -     | 0   | 0    | Pass           |

---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| **无遗留问题** | 本次测试无遗留问题，所有功能实现符合设计预期 | - | - |

---

## 5. 测试总结

本次测试全面覆盖了openLiBing用户与权限管理功能整改的11个测试用例，包括10个功能性测试和1个性能测试。所有测试用例均通过验证，功能实现符合设计预期，接口响应时间满足性能要求（不超过3秒）。

### 测试覆盖范围：

测试用例覆盖了以下核心业务场景：
- **用户信息管理**（用例314, 313, 312, 311）：华为用户信息查询、权限审核页面、项目管理页面备注、邮箱解绑
- **权限申请流程**（用例310, 309, 308, 307）：权限申请按钮、审批链接管理、代办中心提示、重复申请验证
- **权限转审与规范**（用例345, 315）：接口权限返回值规范、转审流程验证
- **性能指标验证**（用例350）：接口响应时间不超过3秒

### 测试结论：

本次openLiBing用户与权限管理功能整改测试全面覆盖核心业务场景，所有功能实现符合设计预期，性能指标达标，用户体验优化显著，权限管理流程完善规范。建议按计划上线。