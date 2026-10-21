# 安全漏洞 Issue 批次修复

## 需求背景

argus 安全漏洞挖掘报告（2026-08-27、2026-10-10 两批）覆盖 openlibing-codecheck 12 个安全缺陷：认证/授权缺陷（#280 #281 #282 #287）、IDOR/越权（#284 #288 #289）、参数注入（#278 #279）、SSRF（#286）、并发状态机（#292）、CI/CD 供应链（#290）、配置传输未加密（#291）。其中 10 个需代码修复，2 个经技术核实豁免。前端调用方需同步适配接口参数变化。

## 功能描述

- 修复 10 个漏洞（分 A/B/C 三批，每批一个分支一个 PR，base=release_20261029_iter2）：
  - A 批（#280 #281 #282 #287）：前端接口补可信身份（网关注入 userId）+ checkPermission 横向鉴权（18+ 接口）+ openlibing-web 前端补 projectId；
  - B 批（#284 #288 #289 #292）：撤销接口归属校验与或签抢占并发隔离；
  - C 批（#278 #279 #286）：URL 参数编码防注入 + obsUrl SSRF 防护。
- 豁免 2 个：#290（SIG 组结论维持 tag 引用，不固定 commit SHA）；#291（`config.secure` 属性不存在，真实修复需平台开 TLS + 部署级变更，单独跟踪）。
- 不做：RuleModel 输入白名单校验（URL 编码已闭合注入，自由文本搜索字段会误伤合法输入）；不固定 action commit SHA（SIG 结论）。

## 验收标准

- [ ] A 批：伪造 userId / 使用无权限 projectId 越权调用返回 403「no permission」；projectId<=0 返回 403「projectId is invalid」；正常用户操作不受影响；前端调用携带 projectId
- [ ] B 批：exportDebugFile 无权限下载返回 403；跨用户批量撤销已审屏蔽被拒（候选为空或 403）；或签抢占/回滚按操作人隔离
- [ ] C 批：参数值含 `&`/`#`/`=` 时无参数注入、按原值搜索；obsUrl 非白名单主机/file:///302 重定向被拒；正常 OBS 下载解析正常
- [ ] 全量单元测试 0 失败（A 1483 / B 1469 / C 1470），编译通过
- [ ] 三批 PR 打 `ai-assisted` 标签并关联对应业务 Issue
- [ ] 豁免项在 Issue 评论记录结论，commit body 留痕

## 影响范围

- openlibing-codecheck 仓：Controller/Delegate/Operation/Util 30+ 文件 + 对应测试
- openlibing-web 仓：前端接口调用补 projectId 参数（A 批）
- openlibing-docs 仓：本文档归档
