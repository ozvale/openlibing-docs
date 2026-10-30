# 安全问题整改修复（漏洞挖掘 + ICSL 安全送检）

## 需求背景

openlibing-codecheck 于 2026 年 10 月完成两轮安全问题整改，累计修复 30+ 安全 Issue：

1. **漏洞挖掘（argus）**：2026-08-27、2026-10-10 两批报告覆盖认证/授权缺陷（#280 #281 #282 #287）、IDOR/越权（#284 #288 #289）、参数注入（#278 #279）、SSRF（#286 #245）、并发状态机（#292）、CI/CD 供应链（#290）、配置传输未加密（#291）。
2. **同批 PR 并入的专项整改**：接口越权专项 #295（门户接口身份不可验证）、#352（40 个接口资源归属）随 A 批 PR !366 修复；白盒验证 #382（suppression 扫描 URL 路径注入）、#384（webhook 可控 repoType 主机注入）与威胁分析 #254（OBS 对象 key 白名单）随 C 批 PR !368 修复。
3. **ICSL 安全送检排查及整改（#372）**：按《华为 Web 应用安全开发规范》《产品网络安全红线》《威胁分析》《白盒安全验证》《SecBinaryCheck》等专项报告分批次整改，覆盖凭证与加密（B2）、传输与配置（B3）、依赖漏洞（B4）、日志与审计（B5）、输入校验与资源限制、免认证接口越权。
4. 前端调用方需同步适配接口参数变化（A 批 projectId、Excel 导出 userId Query 参数）。

## 功能描述

### 第一部分：漏洞挖掘批次（A/B/C）

- 修复 16 个漏洞（分 A/B/C 三批，每批一个分支一个 PR，base=release_20261029_iter2）：
  - A 批（#280 #281 #282 #287 #295 #352）：前端接口补可信身份（网关注入 userId）+ checkPermission 横向鉴权（18+ 接口，覆盖 #352 的 40 个接口清单）+ openlibing-web 前端补 projectId；
  - B 批（#284 #288 #289 #292）：撤销接口归属校验与或签抢占并发隔离；
  - C 批（#278 #279 #286 #254 #382 #384）：URL 参数编码防注入 + obsUrl/主机名 SSRF 防护 + OBS 对象 key 白名单 + suppression URL 路径校验。
- 豁免 2 个：#290（SIG 组结论维持 tag 引用，不固定 commit SHA）；#291（`config.secure` 属性不存在，真实修复需平台开 TLS + 部署级变更，单独跟踪）。

### 第二部分：ICSL 安全送检整改批次

- B2 凭证与加密（#220 #221 #222 #305）：auto-fix token 改环境变量传入；git 凭证改 GIT_ASKPASS 临时脚本；代码平台 token 改 PRIVATE-TOKEN header；外部脚本执行收敛敏感信息暴露面。
- B3 传输与配置（#301 #303）：内部服务调用 http→https；SMTP STARTTLS 先行加固后回退（#392，由平台统一整改）。
- B4 依赖漏洞升级（#161 #226 #228）：jsoup 1.23.2、kotlin-stdlib 2.4.20、log4j2 2.26.1、amqp-client 5.37.0。
- B5 日志与审计（#214 #241 #256 #297）：LogSanitizer CRLF 净化 + 敏感字段掩码，控制器/委托/响应体日志统一脱敏。
- 输入校验与资源限制（#357 #242 #374 #366 #247）：正则元字符 `Pattern.quote` 转义、邮件 HTML 实体转义、异常详情不回显客户端、ReDoS/扫描量限长限量、SARIF 仅记录规模不设硬截断。
- 免认证接口越权（#389）：新增 CheckboardRepoAccessService/Helper，看板/文件下载/Excel 导出统一仓可见性校验；Excel 导出 userId 改为 Query 参数。

## 验收标准

### 第一部分（漏洞挖掘）

- [x] A 批：伪造 userId / 使用无权限 projectId 越权调用返回 403「no permission」；projectId<=0 返回 403「projectId is invalid」；正常用户操作不受影响；前端调用携带 projectId
- [x] B 批：exportDebugFile 无权限下载返回 403；跨用户批量撤销已审屏蔽被拒（候选为空或 403）；或签抢占/回滚按操作人隔离
- [x] C 批：参数值含 `&`/`#`/`=` 时无参数注入、按原值搜索；obsUrl 非白名单主机/file:///302 重定向被拒；正常 OBS 下载解析正常；OBS 对象 key 越界被拒
- [x] 全量单元测试 0 失败（A 1483 / B 1469 / C 1470），编译通过
- [x] 三批 PR 打 `ai-assisted` 标签并关联对应业务 Issue
- [x] 豁免项在 Issue 评论记录结论，commit body 留痕

### 第二部分（ICSL 整改）

- [x] B2：token 不再出现在子进程 argv、URL 查询串、`.git/config`；GIT_ASKPASS 临时脚本用后清理；GiteeHelperTest 通过
- [x] B3：内部服务调用为 https；SMTP STARTTLS 已回退并记录 #392 平台跟踪
- [x] B4：依赖树为 jsoup 1.23.2 / kotlin-stdlib 2.4.20 / log4j 2.26.1 / amqp-client 5.37.0，`mvn test-compile` 通过
- [x] B5：CRLF 控制字符被净化；token/password/secret/AK/SK 等字段日志掩码为 `***`；LogSanitizerTest 23 项通过
- [x] 输入校验：#357 正则特殊字符按字面量匹配；#242 邮件 HTML 转义；#374 异常详情不回显；#366 限长 100 / 500 文件 / 20000 行生效
- [ ] #247 移除 50 URL/50MB 硬截断并记录 obsUrlCount/fileSize/runs；可配置软上限待定，Issue #247 保持 open（豁免/遗留项）
- [x] 免认证接口：私有仓无 userId 拒绝（403/4001），公开仓匿名只读放行，登录态按仓权限放行；Excel 导出 userId 从 body 移至 Query
- [x] 相关 PR CI 通过并打 `ai-assisted` 标签；合并后全量单测 1571 通过，pre-commit（gitleaks/spotless/checkstyle/spotbugs/pmd）通过

## 影响范围

- openlibing-codecheck 仓：Controller/Delegate/Operation/Service/Util/脚本 40+ 文件 + 对应测试
- openlibing-web 仓：前端接口调用补 projectId 参数（A 批）
- openlibing-docs 仓：本文档归档
