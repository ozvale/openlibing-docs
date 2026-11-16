# csv-injection-neutralize — 导出 CSV/Excel 注入防御改用单引号前缀

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/131
（【安全】【CSV注入】transData 方法存在缺陷无法有效进行 CSV 注入防御）

`CSVInjection#transData` 是 license/扫描结果导出链路统一使用的单元格中和函数。旧实现用正则 `^[=+\-&\\@"].{0,}` 匹配危险开头后，递归 `substring(1)` 逐字符剥离。

实测缺陷（`85542090` 提交说明与单测）：

1. 正则中的 `.` 不匹配行终止符，`{0,}` 长度任意，导致以 `=` 开头、随后紧跟换行值（如 `"=\ncmd"`）整条不匹配，原始危险值直接写入单元格；
2. 递归剥离会破坏合法数据：分支名 `-feature` 被剥成 `feature`，`@user` 被剥成 `user`，导出结果与源数据不一致；
3. 旧正则对全角字符依赖 `convertToHalfWidth` 先行转换，转换区间上界 `'｠'`（U+FF60）会把部分全角字符映射到 ASCII 之外的码位。

归类：CWE-1236（CSV Formula Injection）。

## 功能描述

**做什么**：

1. `transData` 改为单引号前缀（OWASP CSV Injection 缓解方式）：`validate` 判定危险时返回 `"'" + data`，一次前缀中和任意长度的连续危险字符，且幂等（再次调用不会重复追加）。
2. 危险开头判定不再依赖正则，改为：全角转半角 + 去除 `\u0000` 后取首字符，判断是否在 `=+-&\@"` 集合内（`DANGEROUS_LEADING_CHARS`）。
3. 全角转半角区间上界由 `'｠'`（U+FF60）收窄为 `'ｓ'`（U+FF53），避免该区间字符被偏移映射成 DEL 等非预期码位。
4. `OpenScanServiceImpl#insertScanIssue` 中的双重调用 `transData(transData(value))` 简化为单次调用（前缀方案幂等，重复调用无收益）。
5. 重写 `CSVInjectionTest`：覆盖连续危险字符、原始数据保留、幂等、换行/回车绕过、全角字符、NUL 前缀、空值/null、`validate` 首字符判定。

**不做什么**：

- 不采用 issue 建议的"把单元格设置为文本格式"方案（本轮未覆盖）。选择前缀方案的原因：`transData` 是导出链路统一入口，前缀方案一次改动即可覆盖 xls 导出与 CSV 场景，不依赖每个单元格样式设置；文本格式方案需遍历全部导出点设置 DataFormat，且对已存在的 `HSSFWorkbook` 样式共享逻辑侵入更大。若后续要求导出文件"零可见改动"，可再评估文本格式方案。
- 不改变导出文件类型、列结构与样式体系。
- 不处理非导出链路的用户输入（不属于 CSV 注入面）。

## 验收标准

- [x] 危险开头值被中和：`=test` / `+test` / `-test` / `&test` / `\test` / `@test` / `"test` 输出均带单引号前缀
- [x] 连续危险字符一次中和：`==test` → `'==test`，`=+test` → `'=+test`，`+-&test` → `'+-&test`
- [x] 换行绕过修复：`=\ncmd` → `'=\ncmd`，`@\rcmd` → `'@\rcmd`（对应旧正则 `.` 不匹配行终止符的缺陷）
- [x] 合法数据不被破坏：`-feature` → `'-feature`，`@user` → `'@user`
- [x] 幂等：`transData(transData("=test"))` 结果仍为 `'=test`，不会追加第二个单引号
- [x] 全角与 NUL 场景：`＝cmd`、`＠cmd`、`\u0000=cmd` 均被前缀中和
- [x] 非危险开头与空值：`test+123`、`test=test` 原样返回；`""`、`null` 返回空串
- [x] 单测：`CSVInjectionTest` 共 11 个用例全部按新语义断言；本次回溯未重新执行 `mvn test`

## 影响范围

- 仓库：`openlibing-sca`（analysis 模块导出链路）。
- 接口：无契约变化；导出文件单元格内容语义变化（危险值带 `'` 前缀；不再吞掉开头特殊字符）。
- 配置 / schema / 部署：无。
- 用户可见变化：导出文件中原先被剥掉开头 `-`、`@` 等字符的数据恢复原样，但危险开头值会显示单引号前缀。
