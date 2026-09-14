# openLibing对接接口管理获取全量接口，菜单管理进行全量接口权限管理 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/83
- **需求名称**: openLibing对接接口管理获取全量接口，菜单管理进行全量接口权限管理
- **开发责任人**: zhuangzhiting、liting
- **测试责任人**: caolongheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**
- [ ] **体验测试**
- [ ] **集成测试**
- [ ] **安全与隐私测试**：
- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.菜单管理的接口列表页面正确识别已接入接口的用途/类型**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/83
- **步骤一**：访问管理中心->菜单管理->接口列表
- **预期结果**: 接口列表中出现已对接仓库的接口
- **测试结果**： Passed
- **步骤二**：检查扫描的接口用户/类型
- **预期结果**: 人机接口正确匹配菜单中接口（没有则为未配置接口）
- **测试结果**： Passed
- **步骤三**：手动编辑接口类型/用户
- **预期结果**: 可以未配置接口为接口或者服务内接口
- **测试结果**： Passed
- **步骤四**：进行请求url的查询和类型的筛选
- **预期结果**: 查询功能和筛选功能正常
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb2100011la4u87f&detail=result

**2.测试访问白名单接口页面基本功能_功能正常**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/83
- **步骤一**：新增访问白名单接口，配置对应的白名单类型
- **预期结果**: 新增成功
- **测试结果**： Passed
- **步骤二**：编辑已经新增的白名单接口，切换请求方式类型等
- **预期结果**: 编辑成功
- **测试结果**： Passed
- **步骤三**：在搜索框搜索对应的接口URL
- **预期结果**: 返回接口正确
- **测试结果**： Passed
- **步骤四**：删除对应的接口URL
- **预期结果**: 删除成功
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb2100011la5d4ep&detail=result

**3.测试已下线页面功能_功能正常**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/83
- **步骤一**：访问菜单管理->已下线接口
- **预期结果**: 列表中展示菜单管理已配置，但接口列表（全量接口）未配置的接口或者菜单进行模糊匹配的接口
- **测试结果**： Passed
- **步骤二**：在菜单中配置测试接口，点击同步按钮
- **预期结果**: 已下线接口列表中出现配置的测试接口
- **测试结果**： Passed
- **步骤三**：使用搜索框搜索测试接口
- **预期结果**: 搜索功能正常返回测试接口
- **测试结果**： Passed
- **步骤四**：点击测试接口的删除按钮
- **预期结果**: 测试接口（即已下线接口）不在列表中显示，菜单中同步删除对应的测试接口
- **测试结果**： Passed
- **步骤五**：重新在菜单中配置测试接口，点击同步按钮
- **预期结果**: 已下线接口列表中出现配置的测试接口
- **测试结果**： Passed
- **步骤六**：对测试接口点击误报
- **预期结果**: 测试接口不在列表中出现，菜单中保留对应的测试接口
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1n00011la8etec&detail=result

**4.菜单管理新增接口配置_支持模糊查询和手动输入**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/83
- **步骤一**：访问菜单管理->菜单页面
- **预期结果**: 菜单页面加载正常
- **测试结果**： Passed
- **步骤二**：点击新增按钮，填写手动填写URL地址配置和其他配置
- **预期结果**: 接口增加成功
- **测试结果**： Passed
- **步骤三**：点击新增按钮，模糊搜索选择URL地址配置并填写其他配置
- **预期结果**: 接口增加成功
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1v00011laj82qd&detail=result

**5.对已下线接口进行误报和撤销操作_操作成功**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/83
- **步骤一**：在已下线接口中，选择一个测试接口，点击误报按钮
- **预期结果**: 已下线接口列表测试接口消失，出现在误报列表页面中
- **测试结果**： Passed
- **步骤二**：选择刚才误报的接口，点击撤销
- **预期结果**: 误报列表页测试接口消失，回到已下线接口列表
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1v00011lf50720&detail=base

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 5        | 覆盖核心业务逻辑与 API 契约。 | 5      | 0        | Pass             |
