# openLiBing代码仓分支webhook实时同步 测试报告

## 1. 基本信息

* **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2104857422
* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/86
* **需求名称**: openLiBing代码仓分支webhook实时同步
* **开发责任人**: 陈明旭
* **测试责任人**: 徐愚冰
* **最终结论:**： 通过
* **测试维度** ：
* [x] **功能自检测试**
* [x] **体验测试**
* [x] **集成测试**
* [ ] **安全与隐私测试**
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [x] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1. openlibing代码仓管理页面新录入代码仓时自动添加webhook成功**:
* 前置条件:openlibing代码仓管理页面可访问，gitcode/github仓库地址有效，且已配置有权限的令牌
* 测试步骤:
* 1.在openlibing代码仓管理页面点击录入仓库
* 2.输入gitcode/github仓库地址
* 3.提交录入请求
* 4.验证仓库是否成功录入openlibing代码仓管理
* 5.登录gitcode/github仓库的Settings > Webhooks页面，确认webhook已自动创建
* 6.检查webhook的Payload URL、Content type、触发事件（如Branch creation/deletion）配置是否正确
* 预期结果:
* 新录入代码仓时自动创建webhook，webhook配置正确（Payload URL指向openlibing服务，触发事件包含分支创建/删除）
* **测试结果**： Passed
* **证明截图**: xxx

**2. 存量代码仓通过定时任务添加webhook成功**:
* 前置条件:openlibing代码仓管理中已存在存量代码仓（此前未配置webhook）
* 测试步骤:
* 1.确认存量代码仓当前无webhook配置
* 2.等待定时任务触发执行（或手动触发定时任务）
* 3.定时任务执行后，检查该存量代码仓是否被扫描到
* 4.登录gitcode/github仓库的Settings > Webhooks页面，确认webhook已创建
* 5.验证webhook配置（Payload URL、触发事件等）与预期一致
* 6.确认定时任务执行日志中该仓库的webhook创建记录
* 预期结果:
* 定时任务成功扫描存量代码仓并为缺失webhook的仓库自动创建webhook，配置正确
* **测试结果**： Passed
* **证明截图**: xxx

**3. 添加webhook后，在代码仓进行分支的增加操作，实时同步到openlibing代码仓管理页面**:
* 前置条件:代码仓已成功添加webhook，openlibing代码仓管理页面可查看该仓库
* 测试步骤:
* 1.在gitcode/github仓库中创建一个新的分支（如feature/test-webhook）
* 2.等待webhook触发并回调openlibing服务
* 3.刷新openlibing代码仓管理页面中该仓库的分支列表
* 4.验证新创建的分支已出现在分支列表中
* 5.检查分支信息（名称、最新提交等）与gitcode/github一致
* 预期结果:
* 新增分支后，openlibing代码仓管理页面实时同步展示新分支，分支信息准确
* **测试结果**： Passed
* **证明截图**: xxx

**4. 添加webhook后，在代码仓进行分支的删除操作，实时同步到openlibing代码仓管理页面**:
* 前置条件:代码仓已成功添加webhook，openlibing代码仓管理页面可查看该仓库的多个分支
* 测试步骤:
* 1.在openlibing代码仓管理页面记录当前分支列表
* 2.在gitcode/github仓库中删除一个已有分支
* 3.等待webhook触发并回调openlibing服务
* 4.刷新openlibing代码仓管理页面中该仓库的分支列表
* 5.验证被删除的分支已从分支列表中移除
* 预期结果:
* 删除分支后，openlibing代码仓管理页面实时同步移除已删除分支，分支列表与gitcode/github一致
* **测试结果**： Passed
* **证明截图**: xxx

**5. 令牌权限不足时webhook创建失败并给出明确提示**:
* 前置条件:代码仓已录入openlibing代码仓管理
* 测试步骤:
* 1.在openlibing代码仓管理页面配置权限不足的令牌（如无repo/webhook管理权限）
* 2.录入新代码仓或触发存量代码仓的定时任务
* 3.验证webhook创建是否失败
* 4.检查openlibing页面或定时任务日志是否有明确的失败提示信息
* 5.确认提示信息包含失败原因（如权限不足、令牌无效等）
* 预期结果:
* 令牌权限不足时webhook创建失败，openlibing页面或日志给出明确的权限不足提示
* **测试结果**： Passed
* **证明截图**: xxx

**6. 重复添加webhook时，不会重复创建，复用已有webhook**:
* 前置条件:代码仓已存在openlibing创建的webhook
* 测试步骤:
* 1.确认该代码仓已有webhook
* 2.重新触发webhook添加流程（如重新录入同一仓库或再次执行定时任务）
* 3.检查gitcode/github仓库的Webhooks列表，确认未新增重复webhook
* 4.验证原有webhook配置保持不变
* 预期结果:
* 重复添加webhook时，openlibing检测到已有webhook，不会重复创建，避免冗余
* **测试结果**： Passed
* **证明截图**: xxx

**7. 删除webhook后，分支增删不再同步到openlibing**:
* 前置条件:代码仓已成功添加webhook，分支同步正常
* 测试步骤:
* 1.在gitcode/github仓库中手动删除openlibing创建的webhook
* 2.在gitcode/github仓库中创建一个新分支
* 3.刷新openlibing代码仓管理页面
* 4.验证新分支未同步到openlibing
* 5.后续定时任务或手动触发webhook重建后，确认同步恢复
* 预期结果:
* 删除webhook后分支同步停止，重建webhook后同步恢复
* **测试结果**： Passed
* **证明截图**: xxx

**8. 存量代码仓已存在手动创建的webhook时，定时任务不会重复覆盖**:
* 前置条件:存量代码仓已手动创建了webhook（非openlibing创建）
* 测试步骤:
* 1.确认存量代码仓已有手动创建的webhook
* 2.等待定时任务触发执行
* 3.检查定时任务执行日志，确认该仓库被跳过
* 4.验证手动创建的webhook未被修改或删除
* 预期结果:
* 存量代码仓已有webhook时，定时任务跳过该仓库，不覆盖手动创建的webhook
* **测试结果**： Passed
* **证明截图**: xxx

**9. 同时新增/删除多个分支时，同步结果准确无误**:
* 前置条件:代码仓已成功添加webhook，分支同步正常
* 测试步骤:
* 1.在gitcode/github仓库中同时创建多个新分支
* 2.在gitcode/github仓库中同时删除多个已有分支
* 3.等待webhook触发并处理
* 4.刷新openlibing代码仓管理页面
* 5.验证所有新增分支均已同步，所有已删除分支均已移除
* 6.确认分支列表与gitcode/github仓库实际分支列表完全一致
* 预期结果:
* 批量增删分支场景下，openlibing同步结果准确，不遗漏不错误
* **测试结果**： Passed
* **证明截图**: xxx

**10. 网络异常导致webhook回调失败时，openlibing有重试机制**:
* 前置条件:代码仓已成功添加webhook
* 测试步骤:
* 1.模拟openlibing服务短暂不可用（如停止服务）
* 2.在gitcode/github仓库中创建一个新分支，触发webhook回调
* 3.观察webhook回调失败
* 4.恢复openlibing服务
* 5.验证gitcode/github是否有重试机制发送webhook
* 6.确认openlibing恢复后成功接收并处理分支同步
* 预期结果:
* webhook回调失败后有重试机制，服务恢复后分支同步成功，数据不丢失
* **测试结果**： Passed
* **证明截图**: xxx

### 2.2 体验测试专项

**11. 代码仓管理页面分支信息展示实时性**:
* 前置条件:代码仓已成功添加webhook
* 测试步骤:
* 1.进入openlibing代码仓管理页面
* 2.在gitcode/github仓库中创建/删除分支
* 3.观察openlibing页面分支列表的更新时机
* 4.验证从分支变更到页面展示的延迟是否在可接受范围内（如≤10s）
* 5.检查页面是否有加载状态提示
* 预期结果:
* 分支变更后页面实时更新，延迟在可接受范围内，页面有加载状态反馈
* **测试结果**： Passed
* **证明截图**: xxx

**12. webhook配置状态可视化展示**:
* 前置条件:openlibing代码仓管理页面可访问
* 测试步骤:
* 1.进入代码仓管理页面查看仓库详情
* 2.检查webhook配置状态是否有直观展示（如已配置/未配置/异常）
* 3.验证webhook状态异常时（如令牌失效）是否有告警标识
* 4.确认是否可以方便的查看webhook配置详情
* 预期结果:
* webhook配置状态在页面中直观展示，异常时有提示，便于用户感知
* **测试结果**： Passed
* **证明截图**: xxx

### 2.3 集成测试专项

**13. 端到端完整链路验证（新录入代码仓→自动添加webhook→分支增删实时同步→存量代码仓定时任务补充webhook）**:
* 前置条件:openlibing代码仓管理页面可访问，gitcode/github令牌已准备
* 测试步骤:
* 1.录入一个新的gitcode/github仓库
* 2.验证自动创建webhook成功
* 3.在远程仓库中创建一个新分支，验证openlibing页面实时同步
* 4.在远程仓库中删除一个分支，验证openlibing页面实时同步移除
* 5.选择一个存量未配置webhook的仓库，触发定时任务
* 6.验证定时任务为其创建了webhook
* 7.在该存量仓库中增删分支，验证同步正常
* 预期结果:
* 从新仓库录入到自动添加webhook、分支增删实时同步、存量仓库定时任务补充webhook的完整端到端链路正常，各环节数据一致
* **测试结果**： Passed
* **证明截图**: xxx

### 2.4 性能测试专项

**14. 存量代码仓大规模批量添加webhook的定时任务执行性能**:
* 前置条件:openlibing代码仓管理中存在大量（≥100个）未配置webhook的存量代码仓
* 测试步骤:
* 1.触发定时任务执行
* 2.记录定时任务从开始到所有仓库webhook创建完成的总耗时
* 3.验证总耗时是否在可接受范围内（如≤5min）
* 4.检查所有仓库是否均成功创建了webhook
* 5.确认无漏创建或创建失败的情况
* 预期结果:
* 大规模批量添加webhook时定时任务在合理时间内完成，所有仓库均成功创建
* **测试结果**： Passed
* **证明截图**: xxx

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试**    | 10   | 覆盖新录入代码仓自动添加webhook、存量代码仓定时任务添加webhook、分支增删实时同步、令牌权限不足异常处理、重复添加幂等、删除webhook后同步停止、手动webhook不覆盖、批量增删同步、网络异常重试。    | 10  | 0    | Pass           |
| **体验测试**    | 2    | 分支信息展示实时性、webhook配置状态可视化。    | 2   | 0    | Pass           |
| **集成测试**    | 1    | 新仓库录入到自动添加webhook、分支增删实时同步、存量仓库定时任务补充webhook的端到端完整链路。    | 1   | 0    | Pass           |
| **安全与隐私测试** | 0    | -                   | 0   | 0    | Pass           |
| **可靠性与韧性测试** | 0    | -                   | 0   | 0    | Pass           |
| **可服务性与可观测性测试** | 0    | -                   | 0   | 0    | Pass           |
| **性能与伸缩性测试** | 1    | 存量代码仓大规模批量添加webhook的定时任务执行性能。    | 1   | 0    | Pass           |

## 4. 遗留问题记录

| 序号 | 问题描述 | 严重程度 | 负责人 | 状态 | 备注 |
| --- | ------- | ------ | ----- | ---- | ---- |
|    |         |        |       |      |      |

## 5. 补充说明

无