# Tasks: fragment 代码片段加密存储及日志泄露防护

## 实现步骤

- [x] 1. 新增 FragmentCryptoUtil 工具类
  - encryptFragments(DefectVo) / encryptFragments(List<DefectVo>)
  - decryptFragments(DefectVo) / decryptFragments(List<DefectVo>)
  - 加密失败抛异常中断入库，解密失败兼容历史数据

- [x] 2. 入库加密（3 个 Operation 类）
  - FullDetailsOperation.saveInfo() 入库前加密
  - IncDetailsOperation.insertList() 入库前加密
  - DatarecoveryOperation.insertList() 入库前加密

- [x] 3. 查询解密（2 个 Operation 类，11 个方法）
  - FullDetailsOperation: 7 个查询方法返回前解密
  - IncDetailsOperation: 4 个查询方法返回前解密

- [x] 4. 修复日志泄露
  - DatarecoveryDelegateImpl: successDefects/failDefects 改为打印 size

- [x] 5. 防御性 @ToString.Exclude
  - DefectVo.fragment
  - 5 个规则类的 rightExample/errorExample
