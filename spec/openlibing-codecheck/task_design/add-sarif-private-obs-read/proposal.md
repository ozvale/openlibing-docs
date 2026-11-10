# add-sarif-private-obs-read

## 基本信息

| 项          | 值                                                                                  |
| ----------- | ----------------------------------------------------------------------------------- |
| FE 需求名称 | upload-sarif-action插件上传OBS对象私有化适配及存量数据治理-后端                     |
| 目标仓      | openlibing-codecheck                                                                |
| 业务分支    | add-sarif-private-obs-read（base: upstream/add-static-alarm-github-adapt a0eaeb29） |
| 关联 Issue  | openlibing/openlibing-codecheck#402（业务 issue；伞形安全 issue 见 #401）           |
| 流程模式    | Standard                                                                            |

## 需求背景

`upload-sarif-action` / `pre-commit-action` 插件当前以 `public-read` 上传 SARIF 到 OBS，后端 `SarifParseServiceImpl` 直接用 `HttpURLConnection` 匿名 GET 下载。扫描结果包含源码路径、代码片段与缺陷信息，任何拿到 URL 的人都能读取，属于敏感信息暴露。

插件侧将改为私有 ACL 上传（另仓负责）。后端需要同步改造为：用平台 OBS 凭证（`obs.access-key-id` / `obs.secret-access-key` / `obs.endpoint`）读取私有对象。凭证具备仓库内对象读权限，若直接按调用方传入的 URL 读取，会退化成"任意对象读取器"，因此必须叠加访问策略：只允许约定桶、约定目录、SARIF 后缀，并校验对象归属仓库与上报仓库一致。

存量已上传到公开桶的文件不在本次治理范围（由插件侧负责），后端只保证读取链路适配后存量 `obsUrl` 仍可正常解析，不迁移、不清理既有对象。华为云 CodeHub 旧链路的 `obsUrl` 在改造前即被 host 白名单拒绝，不在本条承诺范围。

## 验收标准

1. 删除基于 `obsUrl` 的匿名 HTTP 下载路径，不再对 `obsUrl` 发起任何出站 HTTP 请求。
2. SARIF 通过平台 OBS 客户端读取：AK/SK 经 `SecurityUtil.decrypt(x, security.part1)` 解密，与现有 Excel 导出共用同一套 `obs.*` 配置。
3. 桶白名单支持 Nacos 覆盖 `codecheck.alarm.obs.allowed-buckets`，未配置时默认 `openlibing-gitcode-action,openlibing-github-action`。
4. 目录白名单支持 Nacos 覆盖 `codecheck.alarm.obs.allowed-key-patterns`（逗号分隔正则，匹配对象 key 开头），未配置时默认 `^[a-z0-9][a-z0-9._-]*-results/`，覆盖 `{toolName}-results/`、`pre-commit-results/`、`code-arts-check-results/`。
5. 白名单配置逐条解析：单条正则编译失败时丢弃该条并告警；配置整体为空或全部非法时回落默认值，不阻断服务启动。
6. 只允许读取以 `.sarif` 结尾的对象（忽略大小写），其余后缀（如 `build-result.json`）拒绝。
7. 归属校验：objectKey 第二段仓库名需与 `scanRun.repo` 忽略大小写相等；`unknown-repo`（插件取不到仓库名的兜底目录）无归属信息，接收阶段拒绝入库、读取阶段拒绝读取；路径段数不足约定结构时拒绝。
8. 单文件大小上限默认 500MB，可通过 `codecheck.alarm.obs.max-file-size-mb` 调整；元数据预检 + 流式计数双保险，超限中止并删除临时文件。
9. 单个 URL 被拒或下载失败只记录该 URL 的错误，不影响同批其他 URL；全部失败时 scanRun 置 FAILED（保持现有语义）。
10. 下载产生的临时文件在解析成功、解析失败、下载失败三种路径下均被删除。
11. 首页/告警列表展示的平台与仓库仍来自 `repoUrl` 解析结果；`unknown-repo` 目录不再被接收，展示逻辑不依赖 OBS 路径。
