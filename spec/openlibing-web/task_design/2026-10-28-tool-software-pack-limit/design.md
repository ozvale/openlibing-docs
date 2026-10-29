# 技术方案

## 方案概述

在工具管理新建/编辑工具组件 `toolItem.vue` 中新增软件包限制响应式对象 `softwarePackLimit`，组件初始化时调用新增接口 `getSoftwarePackSizeLimit` 拉取限制配置并合并到默认值；文件校验与分片大小计算统一读取该对象，替换原有硬编码的 5G 与 5MB。

## 接口设计

| 项目     | 内容                                                                                              |
| -------- | ------------------------------------------------------------------------------------------------- |
| 路径     | `GET /tool-apply/get-software-pack-size-limit`                                                    |
| 请求参数 | 无（沿用框架前缀 `FRAME_WORK`）                                                                   |
| 返回字段 | `maxSizeMb`（文件大小上限，MB）、`maxSizeDesc`（大小限制展示文案）、`chunkSizeMb`（分片大小，MB） |
| 失败处理 | 沿用前端默认值 `500MB` / `5MB`                                                                    |

## 改动文件

| 文件                                                                          | 改动说明                                                             |
| ----------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `apps/web-openlibing/src/api/url.ts`                                          | 新增 `GET_SOFTWARE_PACK_SIZE_LIMIT` 常量                             |
| `apps/web-openlibing/src/api/api.ts`                                          | 新增 `getSoftwarePackSizeLimit` 请求方法                             |
| `apps/web-openlibing/src/views/ToolManagement/MyTool/components/toolItem.vue` | 新增 `softwarePackLimit`，校验文案、大小校验、分片大小改为读取接口值 |

## 核心代码

```javascript
// 软件包上传限制，接口获取失败时使用默认值
const softwarePackLimit = ref({
  maxSizeMb: 500,
  maxSizeDesc: "500MB",
  chunkSizeMb: 5,
});
getSoftwarePackSizeLimit().then((res) => {
  if (res.code === 200 && res.data) {
    softwarePackLimit.value = { ...softwarePackLimit.value, ...res.data };
  }
});

// 文件大小校验
const isLtSize =
  file.raw.size / 1024 / 1024 < softwarePackLimit.value.maxSizeMb;

// 分片大小
const chunkSize = softwarePackLimit.value.chunkSizeMb * 1024 * 1024;
```

## 影响范围

- **影响范围**：仅工具管理新建/编辑工具弹窗的软件包上传校验与分片逻辑
- **数据来源**：限制配置由后端接口返回，前端仅做展示与校验
- **不影响**：上传接口地址与参数、断点续传/分片合并流程、其他页面

## 风险分析

1. **接口不可用**：已内置默认值兜底，上传流程不会中断，但默认值与后端实际限制可能不一致，需后端保证接口可用性
2. **字段缺失**：合并逻辑采用 `...softwarePackLimit.value, ...res.data`，缺失字段保留默认值；若后端返回 0 或空字符串会导致校验异常，需后端保证字段有效
3. **超大文件耗时**：分片大小变小会增加分片数量与请求次数，接口值由后端下发，属于预期内的配置权衡
