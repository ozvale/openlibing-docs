# 1 标签管理-支持工具标签管理 测试策略

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **需求名称**: openLiBing发布-欧拉发布流程增加require字段收集；通用流程增加页面提示和提升易用性、通过已有tag创建代码仓发行版
- **开发责任人**: disiqi,liting,lidebing,gaojiangning
- **测试责任人**: zhangchuang
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.openlibing发布评审_通过已有tag创建代码仓发行版**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击新建发布评审，填写信息，选择线下评审-制品包-代码仓发行版，选择通过tag创建代码仓的发布评审单所在的代码仓，选择tag名称
- **预期结果**: 输入框弹出列表，显示已存在的预期tag列表
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dbtqkun&detail=result

- **步骤二**：选择软件包路径
- **预期结果**: 表格中显示tag名称校验结果
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dbtqkun&detail=result

- **步骤三**：点击发起评审，评审人评审通过
- **预期结果**: 发起评审单成功，发布评审通过
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dbtqkun&detail=result

**2.openlibing发布评审_线上评审同步病毒扫描和完整性校验执行结果**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击发布设置-安全领域
- **预期结果**: 存在完整性校验和病毒扫描两个，且两个是默认项，不可修改和删除
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dbvah4p&detail=result

- **步骤二**：返回后点击新建发布评审，选择线上评审
- **预期结果**: 安全领域中完整性校验和病毒扫描两项默认必选
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dbvah4p&detail=result

- **步骤三**：选择制品包-代码发行版，填写信息，选择软件包路径，保存
- **预期结果**: 表格中病毒扫描结果和完整性校验结果显示扫描中，等待后状态回显，显示扫描结果
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dbvah4p&detail=result

**3.openlibing发布评审_发布流程交互优化_tag/release旁边出现提示**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：新建发布评审，制品包-代码仓发行版
- **预期结果**: tag/release旁边有问号提示
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1o00011de9omeq&detail=result

- **步骤二**：鼠标悬浮问号上
- **预期结果**: 提示"tag和release名称不能和已有的重复"
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1o00011de9omeq&detail=result

- **步骤三**：选择源码包
- **预期结果**: 显示问号，鼠标悬浮有提示文字
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1o00011de9omeq&detail=result

**4.openlibing发布评审_发布流程交互优化_选择软件包时有提示**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：新建发布评审单，选择制品包，添加软件包路径
- **预期结果**: 出现提示文字"需要先在obs桶模块接入"
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1o00011dea1viq&detail=result

**5.openlibing发布评审_发布流程交互优化_新增手动同步桶信息按钮**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击新建发布评审单，选择制品包，选择添加软件包，进入一个桶内
- **预期结果**: 出现刷新按钮
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb2100011dea7ku8&detail=result

- **步骤二**：点击刷新
- **预期结果**: 桶内信息同步刷新，显示最新桶内信息
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb2100011dea7ku8&detail=result

**6.openlibing发布评审_发布流程交互优化_评审人进入评审单出现提示**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：评审人点击链接进入发布评审单
- **预期结果**: 出现提示文字，提示需要在评审信息栏中填写评审意见，是否给予通过
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011deahuhb&detail=result

**7.openlibing发布评审_通过已有tag创建代码仓发行版_越权失败**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：进入openLiBing项目-发布管理-发布评审
- **预期结果**: 未显示创建评审单按钮
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dgetf1a&detail=result

- **步骤二**：管理员为授权项目成员，新建发布评审单，选择一个公共代码仓，选择tag
- **预期结果**: 显示新建发布评审单，tag列表可以显示
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dgetf1a&detail=result

- **步骤三**：选择私有代码仓
- **预期结果**: 无法显示tag列表
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dgetf1a&detail=result

**8.openlibing发布评审_欧拉update发布流程增加require字段**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/33
- **步骤一**：点击一个评审单
- **预期结果**: 列表中类型除bugfix外新增了requires字段
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dr6uf78&detail=result

- **步骤二**：点击进入发布issue页面
- **预期结果**: 统计bugfix的issues列表，新增统计requires的issues列表
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1o00011ca92si9&case_id=vb1v00011dr6uf78&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述           | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|----------|------|-------------------|-----|------|----------------|
| **功能测试** | 8    | 覆盖核心业务逻辑与 API 契约。 | 8   | 0    | Pass           |