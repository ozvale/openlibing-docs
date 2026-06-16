# Tasks: fragment 代码片段加密存储及日志泄露防护

## 实现步骤

- [x] 1. 新增 FragmentCryptoUtil 工具类
  - encryptFragments(DefectVo) / encryptFragments(List<DefectVo>)
  - decryptFragments(DefectVo) / decryptFragments(List<DefectVo>)
  - decryptFragmentsInMaps(List<Map>) 用于 Map 类型聚合结果
  - tryDecryptLineContent() 返回 Optional<String>，采用两阶段验证
  - 加密失败使用占位提示词，解密失败兼容历史数据

- [x] 2. 入库加密 - task_result_details / task_inc_result_details（3 个 Operation 类）
  - FullDetailsOperation.saveInfo() 入库前深拷贝+加密
  - IncDetailsOperation.insertList() 入库前深拷贝+加密
  - DatarecoveryOperation.insertList() 入库前深拷贝+加密

- [x] 3. 查询解密 - task_result_details / task_inc_result_details（2 个 Operation 类，11 个方法）
  - FullDetailsOperation: 7 个查询方法返回前解密
  - IncDetailsOperation: 4 个查询方法返回前解密

- [x] 4. 修复日志泄露
  - DatarecoveryDelegateImpl: successDefects/failDefects 改为打印 size

- [x] 5. 防御性 @ToString.Exclude
  - DefectVo.fragment
  - CodeCheckIssueFragment.lineContent
  - 5 个规则类的 rightExample/errorExample

- [x] 6. 入库加密 - full_shield_detail / inc_shield_detail（ProblemShieldOperation）
  - saveInfo() 入库前深拷贝+加密
  - saveShieldDetail() 入库前深拷贝+加密
  - getAddFullShieldDetails() 入库前深拷贝+加密

- [x] 7. 查询解密 - full_shield_detail / inc_shield_detail
  - ProblemShieldOperation: getShieldDetailById(), getShieldDetailByUserId(), getInReviewAndUpdateStatu(), fullShieldDetail(), incShieldDetail()
  - ShieldDetailOperation: shieldDetail()（Map 类型，使用 decryptFragmentsInMaps）

- [x] 8. 修复 Base64.isBase64 解码安全漏洞
  - 采用两阶段验证：isBase64 快速过滤 + 回检验证（decode → re-encode → 比对）
  - 纯字母明文（如 "pass"、"return"）不再被误解码为乱码
  - tryDecryptLineContent 返回 Optional<String> 替代 null

- [x] 9. 单元测试更新
  - FragmentCryptoUtilTest 覆盖两阶段验证场景
  - 新增纯字母明文保留测试、回检验证测试、编解码往返测试
