# 技术方案

## 方案概述

本轮改动均为前端局部增强，按功能拆分为四块，彼此无依赖。

## 1. 账号管理：旧密码与确认新密码

编辑态点击"修改登陆密码"后，表单区由单个密码输入改为三个字段：

- `oldPassword`：旧密码，必填
- `password`：新密码（创建态即"登陆密码"），必填
- `confirmPassword`：确认新密码，必填 + 一致性校验

保存逻辑：

```javascript
const data = { projectId: app.projectInfo?.projectId, ...formInfo.value };
delete data.confirmPassword;
// 未修改密码时不提交密码相关字段，避免覆盖原密码
if (!data.password) {
  delete data.password;
  delete data.oldPassword;
}
```

补充：进入编辑态时清空三个密码字段；新密码变化且确认密码已填写时重新触发确认密码校验。

| 文件                                                               | 改动说明                                       |
| ------------------------------------------------------------------ | ---------------------------------------------- |
| `apps/web-openlibing/src/views/AccountManage/accountFormInfor.vue` | 密码表单结构、校验规则、保存参数与编辑态初始化 |

## 2. CVE 七彩数据看板：合计行导出

`handleDownloadByMonth` 中按行类型组装导出时间区间：

- `yearMonth === '合计'`：`startTime = year[0]`，`endTime = addMonth(year[1])`；无年份时导出全部
- 其他行：`startTime = yearMonth`，`endTime = addMonth(yearMonth)`

`seriesTime` 直接构造为 `[{ startTime, endTime }]`，导出文件名改为 `七彩数据_<区间>_<统计类型>_统计报表`。`addMonth` 复用 `views/cve/columns.js` 已导出的工具函数。

| 文件                                                                        | 改动说明                                       |
| --------------------------------------------------------------------------- | ---------------------------------------------- |
| `apps/web-openlibing/src/views/cve/cvePerception/ColorfulDataDashboard.vue` | 合计行时间区间、文件名与 `seriesTime` 组装逻辑 |

## 3. 工具箱管理：软件包上传健壮性

1. 分片上传循环包裹 `try/catch/finally`：接口非 200 时抛出 `msg`，`catch` 中提示并回滚文件列表，`finally` 复位 `btnLoading`。
2. 选择文件时前置校验 `file.raw.size`，为 0 直接提示并清空文件列表，避免 `totalChunks = 0` 导致加载态无法结束。
3. 分片上传参数调整：`projectId` 与 `toolInfo` 各字段改为 `FormData` 表单字段提交，`params` 仅保留 `chunkIndex` / `totalChunks` / `uploadId`。

| 文件                                                                          | 改动说明                                   |
| ----------------------------------------------------------------------------- | ------------------------------------------ |
| `apps/web-openlibing/src/views/ToolManagement/MyTool/components/toolItem.vue` | 上传异常处理、空文件校验、分片请求参数调整 |

## 4. 我的流程：病毒扫描列

在 `config.ts` 中定义共享列配置 `virusScanColumns`，通过展开运算符插入三张"工具创建申请"表（我的申请 / 我的待办 / 我已审批）的"操作"列之前；"社区使用"表不插入。

`toolTable.vue` 新增 `column.options` 渲染分支：按列配置的枚举对象映射展示文本，值为 `undefined` / `null` / 空字符串时展示 `--`。

```javascript
const virusScanColumns = [
  {
    label: "病毒扫描结果",
    prop: "virusScanResult",
    options: virusScanResultList,
  },
  {
    label: "病毒扫描任务状态",
    prop: "virusScanStatus",
    options: virusScanStatusList,
  },
  { label: "病毒扫描执行时间", prop: "virusScanCreateTime" },
];
```

| 文件                                                                    | 改动说明                              |
| ----------------------------------------------------------------------- | ------------------------------------- |
| `apps/web-openlibing/src/views/ToolManagement/config.ts`                | 新增病毒扫描列配置并插入三张创建表    |
| `apps/web-openlibing/src/views/ToolManagement/components/toolTable.vue` | 新增 `options` 枚举映射渲染与空值兜底 |

## 影响范围

- **影响页面**：账号管理、CVE 七彩数据看板、工具箱管理（新建/编辑工具）、我的流程（我的申请/我的待办/我已审批）
- **数据来源**：病毒扫描三列字段由后端列表接口返回（`virusScanResult` / `virusScanStatus` / `virusScanCreateTime`）
- **不影响**：接口地址、权限控制、其他列表与其他业务页

## 风险分析

1. **后端字段依赖**：病毒扫描三列依赖后端返回对应字段，字段缺失时统一展示 `--`，不会报错但无法体现扫描状态，需后端同步发布。
2. **上传参数变更**：`projectId` 与 `toolInfo` 从 query 参数改为表单字段，需与后端上传接口解析方式保持一致，否则分片上传会失败。
3. **合计行年份为空**：未选择年份时导出全部数据，数据量可能较大，属于既有导出能力范围。
4. **密码清空策略**：编辑态始终清空密码输入，用户不修改密码时不会提交密码字段，避免误覆盖；若后端要求密码必填需另行确认。
