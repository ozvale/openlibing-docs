| issueID                     | issue名称                            | 责任人          | 评审结果 | 发布日期   |
| --------------------------- | ------------------------------------ | --------------- | -------- | ---------- |
| #251（openlibing-coderepo） | [缺陷]: 代码仓管理令牌角色状态不准确 | weixin_45521051 | 通过     | 2026-10-21 |

## 发布内容补充说明

本次发布包含依赖安全修复（PR [!837](https://gitcode.com/openlibing/openlibing-web/merge_requests/837)、[!838](https://gitcode.com/openlibing/openlibing-web/merge_requests/838)、[!839](https://gitcode.com/openlibing/openlibing-web/merge_requests/839)，merge commit `d7c228a8`，均已合并），通过 `pnpm-workspace.yaml` overrides 统一升级：

| 依赖包                                   | 版本变更                 | 修复漏洞                                              |
| ---------------------------------------- | ------------------------ | ----------------------------------------------------- |
| markdown-it                              | 12.3.2 / 14.1.1 → 14.3.3 | CVE-2026-111759                                       |
| follow-redirects                         | 1.16.0 → 1.16.1          | CVE-2026-111755 / CVE-2026-111756                     |
| d3-color                                 | 1.4.1 → 3.1.0            | GHSA-36jr-mh4h-2g58（ReDoS）                          |
| dompurify                                | 2.3.5 → 3.4.17           | CVE-2024-48910 / CVE-2024-45801 / CVE-2024-47875      |
| mermaid                                  | 8.14.0 → 11.17.2         | GHSA-m4gq-x24j-jpmf（bundled DOMPurify 原型污染）     |
| glob                                     | 10.4.5 → 12.0.0          | CVE-2025-64756（命令注入）                            |
| serialize-javascript                     | 6.0.2 → 7.1.2            | GHSA-5c6j-r48x-rmvq（RCE）                            |
| launch-editor / launch-editor-middleware | < 2.14.2 → 2.14.2        | CVE-2026-112942（HIGH）/ CVE-2026-112943（MODERATE）  |
| vite                                     | ^7.3.5 → ^7.3.7          | CVE-2026-112942 扫描上报根治（patch 级，无 API 变化） |

同时将 overrides 收敛至 `pnpm-workspace.yaml` 单一来源（42 条全部生效），既有安全 pin（axios / tar / minimatch / undici 等）恢复生效。launch-editor 仅为 vite 的 devDependencies 元数据声明，项目运行时未实际安装，无实际暴露面；!838 的 overrides 保留作为纵深防御，!839 通过升级 vite 7.3.7（官方已将 launch-editor-middleware 声明升至 ^2.14.2）从源头消除扫描命中。
