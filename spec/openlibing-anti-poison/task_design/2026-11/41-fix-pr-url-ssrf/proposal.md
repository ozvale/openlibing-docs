# 41-fix-pr-url-ssrf — 需求背景与验收标准

## 背景

argus 漏洞挖掘确认（CWE-918，高危）：PR URL 经裸 split 解析无任何校验，platformProjectName/repoName/pullNumber 等用户可控字段直接拼入请求 URL；OkHttp 客户端未禁用重定向，且无域名白名单、内网 IP 段与云元数据地址防护，构成完整 SSRF 攻击链，可探测内网、访问云元数据、绕过网络边界。

关联业务 Issue：openlibing/openlibing-anti-poison#41

## 需求范围

- PR URL 解析改安全解析并做域名白名单（gitee/gitcode）校验
- OkHttp 禁用重定向（followRedirects(false)）
- 请求前校验目标 host，拦截内网 IP 段与云元数据地址

## 验收标准

- [x] SSRF 风险已整改，已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

出网请求校验收紧后需确认正常平台 API 调用不受影响。
