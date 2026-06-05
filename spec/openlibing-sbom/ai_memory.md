# openlibing-sbom AI Memory

本文档保存 `openlibing-sbom` 代码仓可长期复用的 AI 开发规则。仅沉淀经过验证且会跨需求复用的通用规则，不记录特定需求的业务细节。

## 仓库定位

`openlibing-sbom` SBOM 制品软件物料清单管理与漏洞分析平台 — 提供 SBOM（Software Bill of Materials）的导入、解析、存储、查询，以及基于 SBOM 的漏洞追溯、License 合规分析、依赖关系图谱等能力

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 生成的测试文件目录需要在`sbom-web/src/test/java`目录下。
- 单个文件测试必须在`openlbing-sbom` 目录下执行`mvn test -pl sbom-web "-Dtest=测试类名"`命令
- 生成类时，如果是全新的类，则用@Data注解（lombok），不需要手写get和set方法，如果是已有的类，存在get\set方法，则保持原样

## Spring Data JPA 规则

### Repository 删除/更新方法注解要求

本项目存在两种 deleteBy 风格，AI 新增删除方法时必须按以下规则选择：

**风格一：Spring Data 派生方法**（方法名即查询，无需 `@Query`）
- 必须加 `@Modifying(flushAutomatically = true)` + `@Transactional(propagation = Propagation.REQUIRES_NEW)`
- 适用场景：简单的按字段删除，Spring Data 能自动派生 SQL
- 项目示例：`RepoMetaRepository.deleteByProductType()`、`FileRepository.deleteBySbomId()`、`ExternalPurlRefRepository.deleteByPkgIdAndCategory()`

**风格二：自定义 `@Query` 原生 SQL**
- 必须加 `@Modifying` + `@Transactional` + `@Query(value="...", nativeQuery=true)`
- 适用场景：派生方法无法表达的复杂删除条件，或需要精确控制 SQL
- 项目示例：`VulnerabilityLifecycleRepository.deleteByProductType()`、`ProductConfigValueRepository.deleteByProductConfigIdAndValue()`


## 远程 API 调用规则

本项目的 Feign Client 定义在 `sbom-web/src/main/java/.../util/feign/` 下，远程 API 返回结构中 `result` 字段可能为 null。

### 遍历调用远程 API 时单次失败不阻断整体

遍历多个维度（社区/租户/批次）调用远程 API 时，每次调用必须独立 try-catch，单次失败仅记录日志，不阻断后续维度的处理：

```java
for (Item item : items) {
    try {
        Response resp = client.call(item);
        // 判空 + 处理
    } catch (Exception e) {
        logger.error("call failed for item={}", item, e);
    }
}
```

## Service 层规则

### 循环外提前解析，循环内参数传入

当循环体内需要用到某个计算结果（如 productType、purl 信息），且该结果对所有迭代相同或可提前确定时，必须在循环外解析一次，作为参数传入循环内方法。禁止在每次迭代中重复解析。

### 分页必须在 SQL 层完成，禁止内存分页

所有分页查询必须通过 SQL 的 `OFFSET/FETCH`（或 `LIMIT/OFFSET`）在数据库层完成，禁止全量拉取数据后在内存中截取。同时禁止一次性加载大内存对象做中间处理。

### 公用逻辑提取到 utils 工具类

当两个或以上 Service 存在相同逻辑（如 purl 转换、字符串解析），必须提取到 `utils` 模块的公共工具类作为静态方法，各 Service 委托调用。禁止各 Service 各自实现一份。

当前已有工具类：
- `PurlUtil`：purl 解析、转换、规范化、版本匹配
- `SignatureUtil`：签名相关


## 测试规则

### 测试框架与风格

- 使用 `@ExtendWith(MockitoExtension.class)` + `@Mock` / `@InjectMocks`
- 不使用 Spring 上下文启动（避免 `@SpringBootTest`），纯 Mockito 单元测试
- 验证交互使用 `verify(..., times(n)).method()` 和 `verify(..., never()).method()`

## Clean Code 规则

### 代码注释规范

**G.CMT.01**：`public` 或 `protected` 修饰的元素（类、方法、字段）应添加 Javadoc 注释，说明其用途、参数含义、返回值语义及异常情况。
示例如下：
```java
    /**
     * 根据产品名，包id，验证登记，漏洞编号查询漏洞信息
     *
     * @param productName String
     * @param packageId   String
     * @param severity    String
     * @param vulId       String
     * @param pageable    Pageable
     * @return PageVo<ShowVulnerabilityVo>
     */
    PageVo<ShowVulnerabilityVo> queryVulnerability(String productName, String packageId, String severity,
                                                   String vulId, Pageable pageable);
```


### 代码格式规范

**G.FMT.10**：行宽不要超过 120 个窄字符，超过时应合理换行，保持代码可读性。

### 方法长度约束

**G.MET.01**：方法行数不应超过 50 行。超过时应考虑拆分方法，遵循单一职责原则。

### G.NAM.08 布尔型变量以 is/has 等动词开头

Boolean 字段必须使用 `is` 或 `has` 前缀：

### 代码清理规范

**G.OTH.03**：不用的代码行和 `import` 语句应直接删除，保持代码整洁，避免无用代码堆积。
