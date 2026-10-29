# openlibing-sbom InternalController 联调契约清单

> 用途：sca 侧 Feign client 联调依据 ｜ Controller：`InternalController`（已交付，见业务 PR openlibing/openlibing-sbom!157）
> 口径版本：v3（queryPackageDependencyTypes 为原始数据透传，最终交付口径）｜ 本文为该契约的归档副本，随 spec 一并归档

## 0. 通用约定

| 项        | 约定                                                                    |
| --------- | ----------------------------------------------------------------------- |
| Base Path | `/internal-api`（feign 直连 sbom 服务，不经网关；服务名以注册中心为准） |
| 请求编码  | `Content-Type: application/json`（除 5 号接口响应为二进制流）           |
| 鉴权      | 无（内网机机接口，无需 token / 用户上下文）                             |
| userId    | 所有接口均无 `userId` 入参                                              |
| 响应包裹  | `DataResult<T>`：`{ "code": int, "msg": string, "data": T }`            |
| 成功      | HTTP 200 + `{ "code": 200, "msg": "success", "data": ... }`             |
| 参数错误  | HTTP 400 + `{ "code": 400, "msg": "<原因>", "data": null }`             |
| 业务失败  | HTTP 500 + `{ "code": 500, "msg": "<原因>", "data": null }`             |

---

## 1. 查询制品名清单（新增）

```
POST /internal-api/queryProductNamesByMultiFilter
```

**入参**（JSON body）：

| 字段                                     | 类型                 | 必填 | 说明                                                                                                                                                                                                                                                                                                                                                                                                       |
| ---------------------------------------- | -------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| productType                              | String               | 是   | 制品类型，与 SBOM 页面 productType 一致                                                                                                                                                                                                                                                                                                                                                                    |
| filters                                  | Map\<String,String\> | 否   | 与 `/sbom-api/queryProductListMultiFilter` 的 filters 完全同构，sca 直接透传页面当前筛选条件。合法 key：`NAME`（制品名多选，逗号分隔）、`INCLUDE_VUL_SEVERITIES` / `EXCLUDE_VUL_SEVERITIES`（漏洞级别多选：CRITICAL/HIGH/MEDIUM/LOW/NONE/UNKNOWN，逗号分隔）、`PACKAGE_COUNT_MIN` / `PACKAGE_COUNT_MAX`（数值字符串）、`SCAN_STATUS`（解析状态多选）、动态配置键（product_config 字段名）。未知 key 报 500 |
| sortField / sortDir / pageNum / pageSize | —                    | 忽略 | 可不传，接口全量返回                                                                                                                                                                                                                                                                                                                                                                                       |

**出参** `data: List<String>`：制品名清单，按名称 COLLATE "C" 升序，全量不分页。

```json
// 请求
{ "productType": "binaries", "filters": { "NAME": "chl_test,test_chl" } }
// 响应
{ "code": 200, "msg": "success", "data": ["chl_test_0921", "test_chl"] }
```

**错误场景**：productType 空 → 400；filters 含未知 key → 500 `query product names failed.`；无条件命中 → 200 + `[]`。

---

## 2. 批量查询软件包依赖类型（新增）

```
POST /internal-api/queryPackageDependencyTypes
```

**入参**（JSON body）：

| 字段        | 类型   | 必填 | 说明   |
| ----------- | ------ | ---- | ------ |
| productName | String | 是   | 制品名 |

**出参** `data: List<PackageDependencyTypeVo>`（**原始数据透传，不去重、不做优先级归并**）：

| 字段             | 类型    | 说明                                                                                   |
| ---------------- | ------- | -------------------------------------------------------------------------------------- |
| name             | String  | 软件包名（package.name）                                                               |
| version          | String  | 版本（package.version，可能为 null）                                                   |
| downloadLocation | String  | 原始下载地址（package.download_location 原值，NOASSERTION/NONE 不做处理，可能为 null） |
| purl             | String  | package_statistics.purl（可能为 null）                                                 |
| dependencyType   | Integer | 0 直接依赖 / 1 间接依赖 / 2 直接&间接依赖；**未刷新时为 null**（不做 -1 归一化）       |

- 同名同版本多行（dependencyType 不同）**原样返回**，取舍逻辑由 sca 侧处理；
- 列表按 name / version 升序；制品不存在 / 无 sbom / 无软件包 → 200 + `[]`。

```json
// 请求
{ "productName": "chl_test_0921" }
// 响应（原始数据，同名同版本多行原样返回）
{ "code": 200, "msg": "success", "data": [
  { "name": "openssl", "version": "1.1.1k", "downloadLocation": "https://www.openssl.org/source/openssl-1.1.1k.tar.gz", "purl": "pkg:generic/openssl@1.1.1k", "dependencyType": 0 },
  { "name": "zlib", "version": "1.2.11", "downloadLocation": "NOASSERTION", "purl": "pkg:npm/zlib@1.2.11", "dependencyType": null }
] }
```

**错误场景**：productName 空 → 400。

---

## 3. 查询制品动态列配置（迁移副本，同 `/sbom-api/queryProductConfig`）

```
GET /internal-api/queryProductConfig?productType={productType}
```

**入参**（query）：

| 字段        | 类型   | 必填 | 说明     |
| ----------- | ------ | ---- | -------- |
| productType | String | 是   | 制品类型 |

**出参** `data: ProductConfigVo`（递归树结构）：

| 字段              | 类型                           | 说明                                      |
| ----------------- | ------------------------------ | ----------------------------------------- |
| name              | String                         | 配置字段名（即 filters 动态键）           |
| label             | String                         | 展示名                                    |
| valueLabel        | String                         | 值显示名                                  |
| valueToNextConfig | Map\<String, ProductConfigVo\> | 值 → 下一级配置（级联），叶子节点为空 Map |

```json
// 响应（示意）
{
  "code": 200,
  "msg": "success",
  "data": {
    "name": "version",
    "label": "版本",
    "valueLabel": null,
    "valueToNextConfig": {
      "8.5.4": {
        "name": "arch",
        "label": "架构",
        "valueLabel": null,
        "valueToNextConfig": {}
      }
    }
  }
}
```

**错误场景**：productType 空 → 400；查询异常 → 500 `query product config failed.`。

---

## 4. 按属性查询制品（迁移副本，同 `/sbom-api/queryProduct`）

```
POST /internal-api/queryProduct?productType={productType}
Content-Type: application/json
```

**入参**：query `productType`（必填）+ JSON body `Map<String,String>`（制品属性精确匹配，全属性须命中；productType 会合入 attributes 后比对）。

**出参** `data: Product`（实体直接序列化，⚠️ 非 VO）：

| 字段                                | 类型                 | 说明                                                                                        |
| ----------------------------------- | -------------------- | ------------------------------------------------------------------------------------------- |
| id                                  | UUID                 | 制品 ID                                                                                     |
| name                                | String               | 制品名                                                                                      |
| attribute                           | Map\<String,String\> | 制品属性                                                                                    |
| createTime                          | Timestamp            | 创建时间（feign 反序列化注意 Timestamp 格式）                                               |
| sbom / rawSboms / productStatistics | 关联实体             | ⚠️ 实体级联序列化可能带出关联对象，payload 较大，feign 消费方按实际响应解析，勿依赖未列字段 |

**错误场景**：productType 空 → 400；制品不存在 → 500 `product is not exist`；查询异常 → 500 `query product info failed.`。

---

## 5. 导出 SBOM 文件（迁移副本，同 `/sbom-api/exportSbom`）

```
GET 或 POST /internal-api/exportSbom?productName=..&spec=..&specVersion=..&format=..
```

**入参**（query，均必填）：

| 字段        | 类型   | 合法值                                                            |
| ----------- | ------ | ----------------------------------------------------------------- |
| productName | String | 制品名                                                            |
| spec        | String | `SPDX` / `CycloneDX`（以 `/sbom-api/exportSbomOptions` 返回为准） |
| specVersion | String | SPDX：`2.2` / `3.0.1`；CycloneDX：`1.4`                           |
| format      | String | `json` / `xml` / `yaml`                                           |

**成功响应**（⚠️ 非 DataResult，二进制流）：

| 项                  | 值                                                                                                                            |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| HTTP Status         | 200                                                                                                                           |
| Content-Type        | `application/octet-stream`                                                                                                    |
| Content-Disposition | `attachment;filename={productName}-{spec}-{specVersion}-sbom.{format}.tar.gz`                                                 |
| Body                | **tar.gz 压缩包**（SBOM 文件 + 校验文件，`generateVerificationAndTar` 产出）——feign 侧需以 `byte[]`/`Response` 接收并自行解包 |

**失败响应**（⚠️ 非 JSON）：HTTP 500 + `text/plain`，body 为错误消息字符串（如 `export sbom metadata failed`）。

**错误场景**：format/spec 组合非法 → 500（text/plain）；制品无数据 → 500（text/plain）。

---

## 6. Feign 消费注意事项汇总

1. **接口 5 与其他接口响应结构不同**：1~4 号为 `DataResult` JSON，5 号为二进制流 / 纯文本，feign client 建议分开定义（5 号方法返回 `feign.Response` 或 `byte[]`，勿用统一 decoder 解析）。
2. **4 号返回实体**：字段以实际响应为准，关联对象级联，勿强依赖固定 schema。
3. **接口 2 为原始数据透传**：不去重、无 downloadKey 计算、dependencyType 可能为 null——同名同版本多行与 NOASSERTION/NONE 口径判断、优先级取舍均由 sca 侧处理。
4. **接口 1 的 filters 直接透传页面查询条件**：无需 sca 侧做键值翻译。
5. 多选值统一为**逗号分隔字符串**，无数组入参。

---

## 7. 验证用例（gamma 部署后人工执行）

Base URL 二选一：网关形式 `https://gamma.openlibing.com/openlibing-sbom`，或服务直连 `http://<sbom-host>:<port>`。`<type>` 替换为实际制品类型（如页面 URL / 项目所用 productType），`<product>` 替换为 SBOM 页面列表中任一制品名。

### 用例 1：queryProductNamesByMultiFilter

```bash
curl -s -X POST "https://gamma.openlibing.com/openlibing-sbom/internal-api/queryProductNamesByMultiFilter" \
  -H "Content-Type: application/json" \
  -d '{"productType": "<type>", "filters": {"NAME": "chl_test,test_chl"}}'
```

预期（HTTP 200）：

```json
{ "code": 200, "msg": "success", "data": ["chl_test_0921", "test_chl"] }
```

校验点：data 为全量制品名且与 SBOM 页面同条件列表一致；`filters: {}` 传空对象时返回全部；未知 filters key（如 `LICENSE_COUNT`）返回 HTTP 500。

### 用例 2：queryPackageDependencyTypes

```bash
curl -s -X POST "https://gamma.openlibing.com/openlibing-sbom/internal-api/queryPackageDependencyTypes" \
  -H "Content-Type: application/json" \
  -d '{"productName": "<product>"}'
```

预期（HTTP 200）：

```json
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "name": "openssl",
      "version": "1.1.1k",
      "downloadLocation": "https://www.openssl.org/source/openssl-1.1.1k.tar.gz",
      "purl": "pkg:generic/openssl@1.1.1k",
      "dependencyType": 0
    },
    {
      "name": "zlib",
      "version": "1.2.11",
      "downloadLocation": "NOASSERTION",
      "purl": "pkg:npm/zlib@1.2.11",
      "dependencyType": null
    }
  ]
}
```

校验点：字段与表列一一对应透传（NOASSERTION/NONE 原样保留）；同名同版本多行不去重原样返回；未刷新依赖类型的包 dependencyType=null；不存在的制品名返回 `data: []`；空 productName 返回 HTTP 400。

### 用例 3：queryProductConfig

```bash
curl -s "https://gamma.openlibing.com/openlibing-sbom/internal-api/queryProductConfig?productType=<type>"
```

预期（HTTP 200）：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "name": "version",
    "label": "版本",
    "valueLabel": null,
    "valueToNextConfig": {
      "1.0": {
        "name": "arch",
        "label": "架构",
        "valueLabel": null,
        "valueToNextConfig": {}
      }
    }
  }
}
```

校验点：data 树结构与页面筛选级联配置一致；缺 productType 返回 HTTP 400。

### 用例 4：queryProduct

```bash
curl -s -X POST "https://gamma.openlibing.com/openlibing-sbom/internal-api/queryProduct?productType=<type>" \
  -H "Content-Type: application/json" \
  -d '{ "version": "1.0", "arch": "x86" }'
```

预期（HTTP 200，data 为 Product 实体）：

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "id": "3f7a1c2e-...",
    "name": "<product>",
    "attribute": { "productType": "<type>", "version": "1.0", "arch": "x86" },
    "createTime": "2026-09-21T10:00:00.000+00:00"
  }
}
```

校验点：attributes 全属性精确匹配才返回；属性组合不存在 → HTTP 500 `product is not exist`。

### 用例 5：exportSbom

```bash
curl -s -o sbom-export.tar.gz -D - \
  "https://gamma.openlibing.com/openlibing-sbom/internal-api/exportSbom?productName=<product>&spec=SPDX&specVersion=2.2&format=json"
```

预期（HTTP 200）：

```
Content-Type: application/octet-stream
Content-Disposition: attachment;filename=<product>-SPDX-2.2-sbom.json.tar.gz
```

校验点：响应体为 tar.gz（解包后含 SBOM json 与校验文件）；非法 spec/format 组合返回 HTTP 500 + text/plain 错误串（非 JSON）。
