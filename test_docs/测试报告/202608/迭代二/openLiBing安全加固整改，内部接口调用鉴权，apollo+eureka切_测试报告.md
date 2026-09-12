# openLiBing安全加固整改，内部接口调用鉴权，apollo+eureka切换华为云CSE服务，命令执行公共组件 测试报告

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-framework/issues/84
* **需求名称**: openLiBing安全加固整改，内部接口调用鉴权，apollo+eureka切换华为云CSE服务，命令执行公共组件
* **开发责任人**: disiqi musheng linyapeng zhuangzhiting lidebing wangxing xiaofeng tangyunhui chentao
* **测试责任人**: dongsicheng
* **最终结论：**： 通过
* **测试维度** ：
* [X] **功能自检测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [ ] **安全与隐私测试**：
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项


**1.plateform-release、sca、framework、anti-position、common、vulnerability等模块切换华为云CSE服务，指导各个服务修改相关配置**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/84
* **步骤一**：进入华为云控制台，搜索cse，进入注册配置中心，选择到openlibing-nacos-prod实体，配置管理-配置列表，切换命名空间至openlibing-prod
* **预期结果**: 列表中存在各项目的配置项
* **测试结果**： Passed
* **步骤二**：登录openlibing，进入任意页面
* **预期结果**: 页面无异常
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1n00011l5lgdu5&detail=result


**2.plateform-release、sca、framework、anti-position、common、vulnerability等模块安全加固整改，内部接口调用请求头新增静态token**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/84
* **步骤一**：登录openlibing，进入任意页面
* **预期结果**: 页面无异常，无出现任何鉴权问题
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1v00011l5jciti&detail=result


**3.common修复重明平台发掘的漏洞及风险配置项修改，openLiBing安全加固，提供安全设计Skill，加入蓝区开发流程**:

* **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-framework/issues/84
* **步骤一**：登录openlibing，进入任意页面
* **预期结果**: 页面无异常，无出现任何鉴权问题
* **测试结果**： Passed
* **证明截图**:  https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011jhcp8u2&case_id=vb1v00011l5jciti&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|---------------------|-----|------|----------------|
| **功能测试** | 3 | 页面无异常 | 3 | 0 | Pass |
