# SBOM 导出异步化改造（Excel 软件成分数据 + 规范文档接入统一导出框架）

> change-name: `sbom-excel-export`　分支：`feat-sbom-excel-export`（openlibing-sbom / openlibing-web，基于 prod/master）
> 设计文档：`D:\work\design\202610\sbom-excel-export.md`

## 需求背景

SBOM 组件分析页的导出能力存在两类问题：

1. **格式缺口**：用户需要将制品软件成分数据导出为 Excel 便于离线分析，当前仅支持 SPDX/CycloneDX 规范文档格式。
2. **同步导出体验差**：现有 SPDX/CycloneDX 导出为单 HTTP 请求内全量内存构建（`findByProductNameWithPackages` 整树加载 → 文档对象 → byte[]），大制品导出占请求线程、易超时、无进度、失败无任务记录；平台已有统一《我的导出》异步导出框架（framework `obs_file` + 异步生成 + OBS + 签名 URL，codecheck/cicd 已接入），sbom 尚未接入。

另有一个与导出无关联的顺带改动并入本次交付（独立 commit）：制品信息列表与 SCA 侧全量制品名接口过滤「无解析状态」数据。

## 需求范围

### 主需求：SBOM 导出异步化双改造

1. 「全量导出」弹窗顶部新增**「类型」单选框**：
   - **软件物料清单（SBOM）**（默认）：下方规范/版本/格式三级联动正常展示，导出 SBOM 规范文档（异步）
   - **软件成分数据（.xlsx）**：隐藏三级联动（仅保留「类型」），导出全量软件成分 Excel（异步，不跟随列表筛选）
2. 弹窗标题「导出SBOM信息」→「导出软件物料清单（SBOM）」；「全量导出」tooltip →「导出SPDX、CycloneDX格式的全量制品数据或者xlsx格式的软件成分数据」
3. 两类导出统一接入平台《我的导出》链路：framework `obs_file` 任务记录 + 本地线程池异步生成（Excel/文档双池隔离，无 MQ 依赖）+ OBS 上传 + 签名 URL 下载，前端浮窗展示进度与自动下载
4. 现有 `exportSbom` 同步接口保留（Internal/Apig 机机调用方不受影响），仅前端切异步

### 附带改动（独立 commit）

制品信息列表（`getProductListMultiFilterPage` 主+count）、SCA 全量制品名接口（`getProductNamesMultiFilter`）、筛选徽标（`countProductsByAttributeKey/countProductsByName`）将 `LEFT JOIN raw_sbom` 改 `INNER JOIN + task_status IS NOT NULL`，过滤无解析状态数据。

## 验收标准

1. 「类型=软件物料清单（SBOM）」：选择规范/版本/格式后导出，任务提交成功，浮窗轮询至完成并自动下载，文件内容与原同步导出一致（json/xml/yaml）
2. 「类型=软件成分数据（.xlsx）」：三级联动隐藏，导出任务完成后下载 xlsx，包含制品全量软件包（14 列：名称/版本/依赖类型/语言/包管理器/6 列漏洞分布/License/PURL/Supplier/来源信息），与列表口径一致
3. 任务失败时《我的导出》与浮窗可见「导出失败：原因」
4. 大制品导出不再占用 HTTP 请求线程，无超时
5. 现有同步导出接口行为不变
6. 制品列表不再出现解析状态为 `--` 的数据；SCA 名单口径与列表一致；筛选徽标计数与列表条数一致

## 跨仓影响

- openlibing-sbom（主）：导出编排/生成/上传 + 附带 SQL 改动
- openlibing-web：导出弹窗重构 + 提交接口对接 + 《我的导出》类型标签
- openlibing-framework：零改动（复用 `/export/internal-server/*` 与 `/export/*` 既有契约）
