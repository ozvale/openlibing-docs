# 【漏洞看板】提供SBOM漏洞软件包+版本查询支持多社区查询 测试报告

## 1. 基本信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-vulnerability/issues/19
- **需求名称**: [需求]: 欧拉社区漏洞修复多元化数据统计展示
- **开发责任人**: wurongqiang
- **测试责任人**: linyapeng
- **最终结论：**： 通过

* [X] **功能自检测试**
* [ ] **体验测试**
* [ ] **集成测试**
* [ ] **安全与隐私测试**：
* [ ] **可靠性与韧性测试**
* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

## 2. 测试过程

### 2.1 功能测试专项

**1. 【漏洞看板】提供SBOM漏洞软件包+版本查询支持多社区查询**:

- **对应task(issueID)链接:** https://gitcode.com/openlibing/openlibing-vulnerability/issues/19
- **步骤一**: 请求接口：openlibing-vulnerability-view/admin/ci-portal/ci-admin/cve/issue/info，参数携带社区名称与要查询的软件包信息
- **预期结果**: 若查询社区采用的软件包，返回对应软件包的漏洞信息；否则无信息返回
- **测试结果**: Passed
- **证明截图**: https://devcloud.cn-southwest-2.huaweicloud.com/cloudtestportal/project/709968f4a69145deba5559c5faf4eca8/testcase?branch_id=vb1o00011ca92si9&case_id=vb2100011cscjmof&detail=result

---

## 3. 测试结果汇总表

| 测试维度     | 用例总数 | 重点测试点描述                             | 通过数 | 不通过数 | 结论 (Pass/Fail) |
|----------|------|-------------------------------------|-----|------|----------------|
| **功能测试** | 1    | 【漏洞看板】提供SBOM漏洞软件包+版本查询支持多社区查询 | 1   | 0    | Pass           |
