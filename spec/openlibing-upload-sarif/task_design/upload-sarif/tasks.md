# openlibing-upload-sarif 通用 SARIF 上传插件 — 实现任务

## 进度: 8/8 complete

- [x] Task 1: 插件脚手架 — package.json / action.yml / index.js 入口 / fetchPolyfill 注入（node16 无全局 fetch）
- [x] Task 2: OIDC 免密换证 — 内嵌 `@openlibing/huaweicloud-oidc-client`，自申请 ID Token + STS 换证，移除对 `huaweicloud-oidc-auth` 插件的依赖
- [x] Task 3: SARIF 文件收集 — `sarif_file` 逗号分隔多路径（文件/目录，目录扫描 `.sarif`），路径兜底查找与缺失校验
- [x] Task 4: `region.snippet` 补齐 — 按 `uri`+行号读源码补齐，支持 `source_path` 多值与文件名递归兜底，写回原文件
- [x] Task 5: OBS 上传 — 迁移 `obsutil` CLI 为 `esdk-obs-nodejs` SDK，动态 region 拼装 server，`public-read`，指数退避重试 3 次
- [x] Task 6: OBS 路径结构统一 — `{toolName}-results/{仓库名}/{yyyyMMdd}.{HH}/{runId|manual}/`，工具名动态前缀与兜底，`build-result.json` 与 SARIF 同路径
- [x] Task 7: APIG 回调 — `/action-api/codescan/v1/result/receive`，V11 签名 + `X-Security-Token`，`obsUrl` 恒为数组，失败仅 WARN
- [x] Task 8: 交付物 — `npm run build`（ncc 打包 dist + zip），README / action.yml 文档同步
