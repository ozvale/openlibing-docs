# notice增加版本级导出功能 测试策略设计说明书

## 1. 基本信息

- **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-sbom/issues/113
- **需求名称**: notice增加版本级导出功能
- **核心目标**:
  为 notice 文档版本级导出（当前筛选条件下全部制品的全量声明文档）提供 2 个纯新增只读查询接口：接口 1 queryProductNamesMultiFilter 按与页面 queryProductListMultiFilter 完全相同的筛选条件（filters 白名单 + 动态键）返回全量制品名（不分页、COLLATE "C" 升序、忽略 sortField/sortDir/pageNum/pageSize、productType 空 400、未知 filter key 500、横向鉴权 403）；接口 2 queryPackageDependencyTypes 按制品名返回全部软件包 (name, version, dependencyType)，归并 key=name+version+downloadurl（有地址取地址、无地址取 purl），相同 key 多依赖关系按 0 直接依赖 > 2 直接&间接依赖 > 1 间接依赖 优先级取一条，NULL 归一化 -1，空态宽松语义 200+空数组；2026.10.13 评审定案制品名称查询接口走 feign 调用，由 sca 侧编排导出；不改任何既有接口行为。
- **开发责任人**: xxx
- **测试责任人**: 赵威

---

## 2. 测试维度确认

- [x] **功能自检测试**

> - **测试重点:** 制品名清单查询接口契约与页面查询结果集一致性（同构 filters 全量返回/排序/分页参数忽略/400 与 500 边界）、包依赖类型归并规则（4 类输出、评审定案 key 与 0>2>1 优先级、(name,version) 唯一、空态宽松语义）、与 sca 联调契约（feign 链路、筛选条件透传、依赖类型字段映射）。
> - **目的:** 确保两个新增只读接口的契约、归并口径与联调行为符合评审定案，且与页面既有查询结果一致。
> - **触发条件:** 强制执行。

- [ ] **体验测试**
- [ ] **集成测试**
- [x] **安全与隐私测试**

> - **测试重点:** 横向鉴权（接口 1 checkPermissionByProductType 越权 productType 403、篡改 userId 防护）、未登录 401 边界（网关统一认证拦截）、接口 2 无鉴权设计定案边界、SQL 注入顺检。
> - **目的:** 确保接口 1 横向越权被拦截且不泄露无权限制品数据，未登录请求被网关 401 拦截；接口 2 无鉴权行为符合设计定案并留痕，注入无放大。
> - **触发条件:** 强制执行。

- [ ] **可靠性与韧性测试**
- [ ] **可服务性与可观测性测试**
- [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1.制品名清单查询接口契约与结果集一致性验证**:

- 前置条件: beta 环境可访问；测试账号具备目标 productType 权限；productType 下存在多制品（含可用 NAME/漏洞级别/包数量区间/扫描状态/动态列筛选区分的数据）；页面 queryProductListMultiFilter 接口可访问（一致性对照基准）
- 测试步骤:
  1. 无 filters（仅 productType）调用接口 1，断言 200 且返回全量制品名（不分页），与页面接口同参逐页汇总的制品名集合 diff 一致
  2. NAME 筛选（多值逗号分隔），断言返回制品名与页面同 filters 结果一致
  3. 其余白名单键（INCLUDE_VUL_SEVERITIES/EXCLUDE_VUL_SEVERITIES/PACKAGE_COUNT_MIN/PACKAGE_COUNT_MAX/SCAN_STATUS）逐一筛选，断言与页面同参结果一致
  4. 动态列键（product_config 配置的 attrFilters），断言与页面同参结果一致
  5. 断言返回列表按 COLLATE "C" 升序（区分大小写字节序）
  6. 请求体携带 sortField/sortDir/pageNum/pageSize，断言被忽略，返回结果与不携带时完全一致（全量）
  7. 无效类：productType 缺失/空串断言 400（productType is required）；filters 含未知 key 断言 500（query product names failed，设计内行为）
  8. 顺检 @LogApi 审计记录生成（OPERATION_MODULE_PRODUCT/QUERY_PRODUCT）
- 预期结果: 全量返回与页面逐页汇总在所有白名单筛选组合下一致；排序符合 COLLATE "C"；分页排序参数被忽略；productType 空 400、未知 key 500；审计记录生成

**2.包依赖类型归并规则验证**:

- 前置条件: beta 环境可访问；制品 P1 软件包数据覆盖 4 类归并输入（仅直接依赖 {0}、仅间接依赖 {1}、直接+间接混合 {0,1}、无 statistics 行或 dependency_type 为 NULL）；存在相同 (name, version, downloadurl) 多条依赖关系记录样本（验证优先级）；存在无地址包（downloadurl 取 purl）样本；制品 P2 无 sbom、制品 P3 无软件包、不存在的制品名 P404
- 测试步骤:
  1. 调用接口 2（productName=P1），断言 200 且返回非空列表，每行 {name, version, dependencyType}
  2. 归并判定表断言：仅 {0} 的包输出 0；仅 {1} 的包输出 1；{0,1} 混合的包输出 2；无 statistics/NULL 的包输出 -1
  3. 优先级断言（评审定案）：相同 key（name+version+downloadurl）存在多条依赖关系时，输出按 0 直接依赖 > 2 直接&间接依赖 > 1 间接依赖 取一条
  4. key 断言：无地址包的归并 key 使用 purl（有地址取地址、无地址取 purl），不与有地址的同名同版本包误合并
  5. 唯一性断言：返回列表 (name, version) 无重复；排序按 name/version 升序（COLLATE "C"）
  6. 空态宽松语义：productName=P404（不存在）/P2（无 sbom）/P3（无包），断言均 200 + 空数组 []
  7. 无效类：productName 缺失/空串断言 400；顺检 @LogApi 审计（OPERATION_MODULE_SBOM/QUERY_SBOM_PACKAGE）
- 预期结果: 4 类归并输出正确；相同 key 多依赖关系按 0>2>1 取一条；无地址包 key 取 purl；(name,version) 输出唯一且升序；三类空态均 200+[]；productName 空 400；审计生成

**3.与 sca 联调契约验证**:

- 前置条件: beta 环境 sbom/sca 均部署到位；sca 侧导出按钮与编排逻辑就绪（sca 团队提供）、feign 客户端配置指向 beta；目标 productType 下存在多制品且软件包覆盖 0/1/2/-1 四类依赖类型
- 测试步骤:
  1. SBOM 页面（或 sca 页面）设置筛选条件（含 NAME 多值 + 动态列），点击 sca"全量声明文档导出"按钮
  2. 断言 sca 侧 feign 调用接口 1 成功（评审定案：制品名称查询接口走 feign），透传的 filters 与页面当前筛选条件同构，返回制品名清单用于导出范围
  3. 断言 sca 按制品清单循环调用接口 2 取依赖类型，feign 链路稳定（无超时/熔断异常；循环调用量为制品数级）
  4. 断言导出的全量声明文档明细中"依赖类型"字段映射正确：0 直接/1 间接/2 直接&间接/-1 未知
  5. 断言导出文档覆盖筛选条件下全部制品（与接口 1 返回清单一致，无遗漏/多余）
  6. 联调异常路径：sbom 接口对某制品返回空数组时，sca 侧该制品明细按无依赖类型数据处理，导出不中断
- 预期结果: feign 链路通；筛选条件透传正确；依赖类型映射正确（含 -1）；导出范围与清单一致；单制品空数据不阻断整体导出

### 3.2 安全与隐私测试专项

**4.接口横向鉴权与无鉴权边界验证**:

- 前置条件: beta 环境可访问；账号 A 具备 productType T1 权限、不具备 productType T2 权限；T1 与 T2 下均存在制品（越权目标数据）
- 测试步骤:
  1. 接口 1 正向：账号 A（userId 透传）查询 T1，断言 200 正常返回
  2. 接口 1 横向越权：账号 A 查询 T2（无权限 productType），断言 403（no permission），不返回 T2 任何制品名
  3. 接口 1 篡改 userId 参数为他人 userId，断言按鉴权实际校验身份拒绝或按实现记录结论
  4. 接口 2 无鉴权设计定案：无用户上下文（不带 userId）调用 queryPackageDependencyTypes，断言 200 正常返回（与 querySbomPackagesMultiFilter 现状一致）
  5. 接口 2 越权数据面确认：任意制品名（含其他项目制品）均可查询，记录为设计定案边界
  6. 注入顺检：接口 1 filters 值、接口 2 productName 携带 SQL 注入串（`' OR 1=1 --`），断言参数化查询生效无放大、无异常泄露
  7. 未登录调用接口 1（网关认证层），断言被网关统一认证拦截（与既有 sbom-api 一致）
- 预期结果: 接口 1 越权 productType 403 且不泄露数据；接口 2 无鉴权行为符合设计定案（200）；注入无放大；网关认证生效（未登录拦截）
