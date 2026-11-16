# 67-fix-apig-permission — 需求背景与验收标准

## 背景

anti-poison 多个 APIG（内部 API 网关）接口无权限控制，任意调用方可触发或查询敏感数据，涉及 4 个接口：/poison-pr/sca-pr（PR SCA 扫描）、/poison-pr/query-pr-results-status、/poison-version/scan-version（版本扫描）、/poison-version/query-version-results-status。

关联业务 Issue：openlibing/openlibing-anti-poison#67

## 需求范围

- 为 4 个 APIG 接口补充调用方鉴权/权限控制
- 防止未授权调用扫描触发与结果查询

## 验收标准

- [x] 未授权调用方无法访问上述接口（已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

需与合法内部调用方（CI/平台）协调鉴权方式，避免误伤既有调用链路。
