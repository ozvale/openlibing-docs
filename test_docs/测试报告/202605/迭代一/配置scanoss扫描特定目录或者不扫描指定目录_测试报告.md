# 1 配置scanoss扫描特定目录或者不扫描指定目录 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/issues/36
- **需求名称**: 配置scanoss扫描特定目录或者不扫描指定目录
- **开发责任人**: musheng,jiangzhichao
- **测试责任人**: caolongheng
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.在合法合规页面的社区管理中选择对应的社区点击添加SCANOSS规则_表单中出现过滤目录字段**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/36
- **步骤一**：在合法合规页面的社区管理中选择对应的社区点击编辑SCANOSS规则->点击添加规则
- **预期结果**: 添加规则表单中出现过滤目录字段
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/76/93/1778720877693319577.png


**2.配置扫描过滤目录_扫描结果中对应目录的文件消失**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-sca/issues/36
- **步骤一**：在合法合规页面版本扫描下选择openlibing-sca代码release_20260508_fix分支
- **预期结果**: 确认风险项中存在如`src/main/java/com/openlibing/sca/analysis`目录下的文件
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/35/59/1778660303559325350.png

- **步骤二**：在合法合规页面pr扫描下选择openlibing-sca代码仓的某个pr
- **预期结果**: 确认风险项中存在如`src/main/java/com/openlibing/sca/analysis`目录下的文件
- **测试结果**：Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/08/91/1778660350891624005.png

- **步骤三**：在社区管理页面，编辑openlibing-sca的SCANOSS规则，添加过滤目录src/main/java/com/openlibing/sca/analysis后重启执行对应的版本扫描和pr扫描
- **预期结果**: 版本扫描和pr扫描结果中对应目录下的风险项不再显示
- **测试结果**：Passed
- **证明截图**: 
- https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/07/04/1778660420704590486.png
- https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/95/62/1778662189562402848.png
- https://devcloud.cn-southwest-2.huaweicloud.com/api/cloudtestportal/v1/tmss/resourcemanagement/709968f4a69145deba5559c5faf4eca8/images/03/78/1778662300378095894.png
---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                | 通过数 | 不通过数 | 结论 (Pass/Fail) |
| ------------ | -------- | ----------------------------- | ------ | -------- | ---------------- |
| **功能测试** | 2        | 覆盖核心业务逻辑与 API 契约。 | 2      | 0        | Pass             |
