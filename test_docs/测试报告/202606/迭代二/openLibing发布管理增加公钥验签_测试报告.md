# openLibing发布管理增加公钥验签 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-platform-release/issues/44
- **需求名称**: openLibing发布管理增加操作提示、公钥验签、对接华为云流水线发布
- **开发责任人**: 邸思奇,姜智超
- **测试责任人**: 张创
- **最终结论：**： 通过
- **测试维度** ：
- [x] **功能自检测试**
- [x] **安全与隐私测试**

## 2. 测试过程

### 2.1 功能测试专项

**1.发布评审对软件包验签**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/44
- **前置条件**: openlibing项目发布评审
- **步骤一**：
  - 1.新建发布评审单，选择线下评审，自定义发布，https://gitcode.com/Richard-bean/lidebin.git代码仓，软件包openlibing-platform-release/1/torch-2.3.1+cpu-cp39-cp39-linux_x86_64.whl，发起评审，等待验签结果
- **预期结果**:
  - 1.回显软件包的验签结果，通过
- **步骤二**：
  - 1.篡改软件包，或上传不合法软件包，同目录不含json文件
- **预期结果**:
  - 1.验签失败
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-south-west-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&case_id=vb1o00011gi7mku3&detail=result

**2.发布评审对压缩包验签**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/44
- **前置条件**: openlibing项目发布评审
- **步骤一**：
  - 1.新建发布评审单，选择线下评审，自定义发布，platform-release-beta-release-test流水线，压缩包openlibing-platform-release/openUBMC/openUBMC-26.03.01.01-20260623_095910-debug.zip，发起评审，等待验签结果
- **预期结果**:
  - 1.回显压缩包的验签结果，通过
- **步骤二**：
  - 1.篡改压缩包，或上传不合法压缩包
- **预期结果**:
  - 1.验签失败
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-south-west-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&case_id=vb1o00011gi7bfts&detail=result

### 2.4 安全与隐私测试专项

**1.篡改软件包验签拦截**: 篡改软件包或上传不合法软件包（同目录不含json文件），发起发布评审，查看验签结果

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/44
- **预期结果**: 验签失败，拦截不合法/被篡改的软件包，保障发布产物完整性。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-south-west-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&case_id=vb1o00011gi7mku3&detail=result

**2.篡改压缩包验签拦截**: 篡改压缩包或上传不合法压缩包，发起发布评审，查看验签结果

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-platform-release/issues/44
- **预期结果**: 验签失败，拦截不合法/被篡改的压缩包，保障发布产物完整性。
- **测试结果**： Passed
- **证明截图**: https://devcloud.cn-south-west-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?type=0&branch_id=vb1v00011ef7p9q0&case_id=vb1o00011gi7bfts&detail=result

---

## 3. 测试结果汇总表

| 测试维度        | 用例总数 | 重点测试点描述                       | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|-------------|------|------------------------------|-----|------|----------------|
| **功能测试**    | 2    | 软件包/压缩包公钥验签通过场景与失败场景覆盖。      | 2   | 0    | Pass           |
| **安全与隐私测试** | 2    | 篡改/不合法包验签拦截，保障发布产物完整性与防篡改。  | 2   | 0    | Pass           |

---

## 4. 遗留问题与风险说明

| 缺陷 ID         | 缺陷描述 | 严重程度 | 处理意见 (修复/忽略/转运维) |
|---------------|------|------|------------------|
| **https://gitcode.com/openlibing/openlibing-platform-release/issues/51** | bug(评审): 验签失败时评审单内验签结果列一直显示校验中   | 一般    | 修复                |
