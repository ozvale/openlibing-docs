-- 指标判定规则面板：conf_json 追加 rule 节点（与 openlibing-ops classpath security/detail-conf/*.json 同源，自动生成）
-- 用法：Doris 直接执行；幂等（JSON_SET 覆盖同名节点，重复执行无副作用）；生效延迟 ≤ 5 分钟（引擎 TTL 缓存）

UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查仓库中是否直接提交了二进制文件或非源码产物，包括可执行文件（.exe/.dll/.so/.jar）、压缩包（.zip/.tar/.gz 等）、办公文档（.pdf/.doc/.xlsx 等）共 22 类。","formula":"得分 = 10 − 二进制文件数（最低 0 分，每个文件扣 1 分）","conditions":[{"label":"命中即扣分","value":"仓库文件树中出现后缀清单内的文件，不区分目录"}],"naCondition":"无，本指标恒有得分。","notes":[]}' AS JSON))
WHERE metric_code = 'BINARY_ARTIFACTS';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"GitCode 平台已默认提供基础分支保护（分支锁定、强制走 PR、评审门槛），本指标主要考察进阶要求：是否通过 .infra_self_service/rebot.yaml 配置了双人 LGTM（lgtm_need_num=2）并真正落实。","formula":"二元计分：默认 8 分；配置 lgtm_need_num=2 且近 30 个已合入 PR 每个都有两条不同人的 /lgtm = 10 分；配置了但未通过仍 8 分（无中间分）","conditions":[{"label":"基础 8 分","value":"平台默认分支保护，恒定满足"},{"label":"满分 10 分","value":"rebot.yaml 配置 lgtm_need_num=2，且近 30 PR 每个都有两条来自不同人（剔除机器人和 PR 作者）的 /lgtm"}],"naCondition":"无，本指标恒有得分。","notes":["lgtm_need_num 取其他值（1/3/…）不触发双人检查，按默认 8 分"]}' AS JSON))
WHERE metric_code = 'BRANCH_PROTECTION';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查最近 30 次已合入 PR（与代码评审同口径）中，每个 PR 是否有 CI 流水线执行记录——只要触发过流水线即视为有 CI。","formula":"得分 = 10 × 有 CI 的 PR 数 / PR 总数","conditions":[{"label":"有 CI","value":"PR 关联到流水线执行记录（CodeArts 关联表）"},{"label":"PR 口径","value":"最近 30 次已合入 PR，剔除机器人创建的 PR"}],"naCondition":"仓库无已合入 PR 时，本指标不参评（不计入总分，不是 0 分）。","notes":[]}' AS JSON))
WHERE metric_code = 'CI_TESTS';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查最近 30 次已合入 PR 中，每个 PR 是否存在有效评审：有「非机器人、非 PR 创建人」通过 /lgtm 或 /approve 命令给出认可。","formula":"得分 = 已评审 PR 数 / PR 总数 × 10","conditions":[{"label":"已评审","value":"存在非机器人、非创建人的 /lgtm 或 /approve 评论"},{"label":"PR 口径","value":"最近 30 次已合入 PR，剔除机器人创建的 PR"}],"naCondition":"剔除机器人创建的 PR 后数量为 0 时，本指标不参评（不计入总分，不是 0 分）。","notes":[]}' AS JSON))
WHERE metric_code = 'CODE_REVIEW';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查最近 30 次已合入 PR 的作者（剔除机器人）来自多少个不同组织，且这些组织中是否有活跃作者（近 30 次 PR 中个人贡献 ≥ 5 个）。","formula":"得分 = 10 × N / 3，上限 10 分（N = 存在至少 1 名活跃作者的组织个数，3 个即满分）","conditions":[{"label":"活跃作者","value":"近 30 次已合入 PR 中该作者贡献 ≥ 5 个"},{"label":"N 值","value":"存在至少 1 名活跃作者的组织个数"},{"label":"PR 口径","value":"最近 30 次已合入 PR，剔除机器人创建的 PR"}],"naCondition":"近 30 次已合入 PR 为 0 时，本指标不参评（不计入总分，不是 0 分）。","notes":[]}' AS JSON))
WHERE metric_code = 'CONTRIBUTORS';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"逐个检查源码文件（.go/.java/.py/.js/.c/.cpp/.rs/.ts/.sh/.bat，test/tests 目录除外）的文件头版权声明，是否与仓库 LICENSE 协议对应的官方版权模板一致。木兰协议的两行短头视为不合格。","formula":"得分 = 10 − 0.2 × 不合格文件数（最低 0 分，50 个扣完）","conditions":[{"label":"合格","value":"文件头含规范版权行（年份 + Huawei），且正文与模板匹配"},{"label":"不合格","value":"无文件头 / 无版权行 / 版权行不规范 / 正文与模板不匹配"},{"label":"比对模板","value":"按 LICENSE 类型自动确定：木兰协议 → 官方模板；带应用附录 → 印刷归一模板；其他 → 内置模板集"}],"naCondition":"仓库无 LICENSE 文件（或不可读）、或没有任何目标类型源码文件时，本指标不参评（不计入总分，不是 0 分）。","notes":["upstream banner（上游代码标识）仅标注展示、不影响判定","每个不合格文件的具体原因可在「版权合规问题文件清单」中查看"]}' AS JSON))
WHERE metric_code = 'COPYRIGHT';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查 .gitcode/workflows 下 CI 配置文件中的两类危险写法：① 显式配置 allow-unsafe-pr-checkout: true（允许检出不可信的 PR 代码）；② 脚本步骤中直接引用不可信上下文变量（如 PR 标题、描述、评论内容，可被注入恶意命令）。","formula":"发现任意一处危险模式 = 0 分；全部干净 = 10 分","conditions":[{"label":"危险模式 1","value":"workflow 中存在 allow-unsafe-pr-checkout: true"},{"label":"危险模式 2","value":"步骤中直接使用 PR 标题 / 描述 / 评论内容等不可信上下文变量"}],"naCondition":"仓库没有 workflow 文件、或文件解析失败（结论不完整，不当 0 分处理）时，本指标不参评。","notes":[]}' AS JSON))
WHERE metric_code = 'DANGEROUS_WF';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查仓库是否开展模糊测试（Fuzzing）活动：是否集成 OSS-Fuzz、配置 ClusterFuzzLite、或使用语言原生模糊测试能力。","formula":"阶梯计分：集成 OSS-Fuzz 或配置 ClusterFuzzLite = 10 分；语言原生 fuzz = 5 分；Haskell 测试框架 = 3 分；无任何活动 = 0 分","conditions":[{"label":"OSS-Fuzz","value":"项目收录于 OSS-Fuzz 官方清单"},{"label":"ClusterFuzzLite","value":"workflow 中引用/配置"},{"label":"原生 fuzz","value":"go test fuzz、libFuzzer、AFL、pytest fuzz 等"}],"naCondition":"无，本指标恒有得分。","notes":["本指标暂缓实施，暂不计入总分"]}' AS JSON))
WHERE metric_code = 'FUZZING';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查仓库根目录（或 license 目录）下的 LICENSE 文件：是否有许可证、格式是否符合官方模板、版权年份和责任人是否填写正确、是否通过 OSI/FSF 开源认证。","formula":"阶梯计分，取满足的最高档：无许可证 0 → 有许可证 5 → 模板一致 8 → 版权正确 9 → OSI/FSF 认证 10","conditions":[{"label":"无 LICENSE 文件","value":"0 分（有效低分，不是不参评）"},{"label":"有许可证","value":"5 分"},{"label":"格式符合官方模板","value":"8 分"},{"label":"版权年份和责任人正确","value":"9 分"},{"label":"通过 OSI/FSF 认证","value":"10 分"}],"naCondition":"无，本指标恒有得分。","notes":[]}' AS JSON))
WHERE metric_code = 'LICENSE';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查仓库近 90 天的维护活跃度 = 默认分支 commit 数 + 新建 issue 数。","formula":"得分 = 10 × (commit 数 + issue 数) / 13，上限 10 分（近 90 天合计 13 个即满分）","conditions":[{"label":"commit","value":"默认分支近 90 天提交数"},{"label":"issue","value":"近 90 天新建 issue 数"}],"naCondition":"仓库已归档、或创建时间不足 90 天（尚在孵化期）时，本指标不参评（不计入总分，不是 0 分）。","notes":[]}' AS JSON))
WHERE metric_code = 'MAINTAINED';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查仓库是否具备自动化发包能力，满足任一即算：workflow 中配置了制品上传插件（obs-upload 或 upload-artifact）；或仓库被收录在 openEuler（Eluermaker）打包工程清单中。","formula":"具备自动化发包能力 = 10 分；未检出 = 0 分（视为未建立自动发包流程）","conditions":[{"label":"条件 1","value":"workflow 中使用制品上传插件（obs-upload / upload-artifact）"},{"label":"条件 2","value":"仓库命中 openEuler 打包工程清单（包名口径比对）"}],"naCondition":"无，本指标恒有得分。","notes":[]}' AS JSON))
WHERE metric_code = 'PACKAGING';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查 CI 引用的 action、Dockerfile 基础镜像、脚本中的安装命令是否都锁定了具体版本（action 带 tag/SHA、镜像带 tag、安装命令带版本号）。Go modules 视为已锁定。","formula":"得分 = 已锁定依赖数 / 依赖总数 × 10","conditions":[{"label":"已锁定","value":"action 带 tag/SHA、镜像带 tag、安装命令带版本号"},{"label":"未锁定","value":"引用浮动版本（如 latest、无 tag）"}],"naCondition":"仓库没有任何可识别的依赖时，本指标不参评（不计入总分，不是 0 分）。","notes":["本指标暂缓实施，暂不计入总分"]}' AS JSON))
WHERE metric_code = 'PINNED_DEP';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查 pre-commit 配置（根目录或 pre-commit/ 目录，两处同时存在则合并）或 workflow 文件中，是否使用了任一静态分析（SAST）工具，不区分语言。","formula":"命中任一工具 = 10 分（多个不加分）；有配置文件但 0 命中 = 0 分","conditions":[{"label":"工具清单","value":"clang-tidy / bandit / eslint / gosec / clippy / spotbugs / gitleaks / luacheck"}],"naCondition":"既没有 pre-commit 配置文件、又没有 workflow 文件时，本指标不参评（不计入总分，不是 0 分）。","notes":[]}' AS JSON))
WHERE metric_code = 'SAST';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查仓库是否提供安全政策文档 SECURITY.md（检查 .gitcode/、根目录、docs/ 等位置），内容包括漏洞披露说明、报告联系方式等。","formula":"仓库内存在 SECURITY.md = 10 分；仅所在社区层面存在 = 5 分；都不存在 = 0 分","conditions":[{"label":"仓库内","value":"检出 SECURITY.md 文件"},{"label":"社区层面","value":"仓库所在社区提供安全政策"}],"naCondition":"无，本指标恒有得分。","notes":[]}' AS JSON))
WHERE metric_code = 'SECURITY_POLICY';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查最近 30 个 Release 版本（含预发布，忽略纯源码包版本）的附件中，是否同时包含 sha256 校验文件和数字签名文件。","formula":"全部版本均同时含 sha256 校验文件与签名文件 = 10 分；任一版本缺少任一项 = 0 分（一票否决）","conditions":[{"label":"sha256 校验文件","value":".sha256 / .sha256sum"},{"label":"数字签名资产","value":".asc / .sig / .pgp / .gpg / .minisig / .pem / .crt / .cer / .p7s"}],"naCondition":"仓库没有任何 Release 时，本指标不参评（不计入总分，不是 0 分）。","notes":["2026-10-20 口径调整：sha256 与签名须同时存在（AND），移除 SLSA Provenance 等效判定"]}' AS JSON))
WHERE metric_code = 'SIGNED_RELEASES';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查 CI 中引用的插件（action）实际获得的权限，是否超出该插件正常工作所需的基准权限。未收录在基准表中的插件按只读基准检查。","formula":"得分 = 10 − 违规插件数（最低 0 分；同一插件多处引用只记一次）","conditions":[{"label":"权限生效顺序","value":"job 级配置 > 文件顶层配置 > 平台默认（读）"},{"label":"违规判定","value":"插件所在 job 的生效权限中任一项为写（write）且超出该插件基准"},{"label":"正确做法","value":"需要写权限的插件单独拆 job 配置，避免一个 job 全量开写"}],"naCondition":"无 workflow 文件、文件解析失败、或有 workflow 但没有引用任何插件（纯脚本/纯复用引用）时，本指标不参评。","notes":["读写分离：job 下多个插件共享同一权限，全 job 开写会让所有只读基准插件同时违规"]}' AS JSON))
WHERE metric_code = 'TOKEN_PERM';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查漏洞管理平台中本仓库已超期且未关闭的漏洞，按严重度扣分。已关闭、已拒绝的漏洞不计入。","formula":"得分 = 10 − (致命×10 + 高危×5 + 中危×2 + 低危×1)，最低 0 分","conditions":[{"label":"致命","value":"每个扣 10 分"},{"label":"高危","value":"每个扣 5 分"},{"label":"中危","value":"每个扣 2 分"},{"label":"低危","value":"每个扣 1 分（严重度未标注的按低危计）"}],"naCondition":"漏洞平台未跟踪本仓库时，本指标不参评（不计入总分，不是 0 分）。","notes":["有跟踪且无超期漏洞 = 满分 10 分","超期判定 = 计划修复时间已过且仍未关闭"]}' AS JSON))
WHERE metric_code = 'VULNS';
UPDATE dm_rd_efc_security_metric_detail_conf
SET conf_json = JSON_SET(CAST(conf_json AS JSON), '$.rule', CAST('{"brief":"检查仓库活跃的 Webhook 中，有多少配置了密钥（secret）。未配密钥的 Webhook 请求可被伪造。","formula":"得分 = 10 × 配置密钥的 Webhook 数 / 活跃 Webhook 总数（向下取整）","conditions":[{"label":"已配密钥","value":"活跃（active）且密钥非空"},{"label":"无活跃钩子","value":"10 分（没有入口即没有风险，不是不参评）"},{"label":"全部未配","value":"0 分"}],"naCondition":"无，本指标恒有得分。","notes":[]}' AS JSON))
WHERE metric_code = 'WEBHOOKS';
