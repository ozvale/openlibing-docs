# security-hardening — 实现任务

## 进度: 15/15 complete

- [x] T1（测试先行 #9）：新增临时文件安全测试——预置 symlink 返回 EEXIST/写入隔离目录、读取校验、三退出路径清理无残留
- [x] T2（测试先行 #10）：新增 Markdown 转义测试矩阵——`|`、换行、`[x](url)`、`<img>`、连续反引号、CRLF；依赖树围栏不闭合
- [x] T3（测试先行 #11）：新增 sanitizeLog 测试——恶意目录名/组件名不产生 `::` 起始物理行；CRLF/连续 `::`/中缀 `::` 边界
- [x] T4（测试先行 #7/#8/#13）：新增提示类测试——预解析失败、无结果文件、无修复版本高危漏洞在 Summary 出现提示
- [x] T5（实现 #9）：`runTrivyScan` 改 mkdtemp 0700 专属目录 + `wx` 排他/ lstat 校验 + 读取校验 + finally 同步清理 + 重试重建目录
- [x] T6（实现 #10）：新增 `escapeMarkdownCell`/围栏转义并在所有 Summary 动态字段接入
- [x] T7（实现 #11）：新增 `sanitizeLog` 并接入全部外部可控日志输出
- [x] T8（实现 #7/#8/#13）：预解析失败/无结果文件/无修复高危漏洞的日志与 Summary 提示 + 口径说明（不阻断）
- [x] T9（构建与验证）：运行两 action 单测 + `npx ncc build` 重打包 dist + 汇总验证结果
- [x] T10（用户补充）：按 uv SOP 更新 Python 提示；按前端 SOP 新增“package.json 缺少 trivy 支持锁文件”提示（日志 + 概览，不阻断）
- [x] T11（用户补充）：Python 提示改为按目录判断——存在 uv.lock/poetry.lock/Pipfile.lock 任一则不提示，requirements.lock 不抑制提示
- [x] T12（CI）：新增 `.prettierrc` / `.prettierignore`、eslint 依赖与 `eslint.config.js`，按 prettier 3.9.5 格式化并修复 dist 尾随空白/EOF
- [x] T13（CI）：UT checkout 增加 `fetch-depth: 0`，修复浅克隆导致 diff-cover `no merge base`
- [x] T14（覆盖率）：为 scan/checkTrivy/runTrivyScan 增加可注入 exec，新增 6 组主流程集成测试，增量行覆盖率 59% → 98%
- [x] T15（隔离）：单测与 UT workflow 测试步骤隔离 `ATOMGIT_STEP_SUMMARY`，避免 Maven 降级提示污染 UT job 汇总

## 备注

- 分支：`fix-oss-scan-security`（基于 origin/master）
- Issue：#7 #8 #9 #10 #11 #13
- 提示类变更不得改变 `judge`/`setFailed` 语义
