# 代码检查模块-屏蔽申请支持多选审批人（或签） 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/182
* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-codecheck/issues/182
* **需求名称**: 门禁屏蔽申请支持多选审批人（或签 OR 模式）
* **核心目标**:
  门禁（type=inc）与每日检查（type=full）场景下，屏蔽申请提交、转审支持多选审批人（新增 `reviewerIds`，或签：任一人审核即终结）；审核权限改为审批人名单成员（先成功者生效，后续 409，非名单 403）；「待我审批」查询与待办计数改为 `reviewerId = me OR reviewers.userId = me`；一条申请 × N 审批人 = N 条 message_apply；`reviewerId` 待审时=名单第一人、审完后覆盖为实际操作人；历史无 `reviewers` 字段数据运行时兼容。
* **设计文档**: `openlibing-docs/spec/openlibing-codecheck/task_design/shield-multi-reviewer/design.md`
* **开发责任人**: xiezhiqiang
* **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

* [x] **功能自检测试**
> * **测试重点:** inc/full 多选 3 人提交（3 人待办 + 3 封通知、`reviewers` 落库、`reviewerId`=名单第一人）、单人兼容（只传 `userId` 行为与现网一致）、或签通过/驳回对称（先成功者生效、后续 409）、转审多人（旧待办清理、新名单通知、`referrals` 记录转审前审批人）、出参一致性（`reviewerName` 审完=实际操作人、`reviewers` 仍为全员）、选人接口入参出参不变。
> * **目的:** 确保多选审批人全链路（选人→提交→转审→待办/列表→审核→通知）功能正确。
> * **触发条件:** 强制执行。

* [ ] **体验测试**
* [x] **集成测试**
> * **测试重点:** framework 文件路径级 Committer 校验 fallback（MySQL 角色表未命中时走 `openlibing-framework/get-committer`）；通知链路（每人一封，禁止只通知第一个人）；待办/列表/待办计数（applyAuditNumber）OR 查询改造后各 Tab 数据正确。
> * **目的:** 验证跨服务依赖与通知/待办链路在多人场景下正确。
> * **触发条件:** 需求标签含 `need_itest`。

* [x] **安全与隐私测试**
> * **测试重点:** 审核权限（非 reviewers 成员审核返回 403、申请人不能出现在审批人名单、名单逐个 Committer 校验）；人数上限配置 `shield.max.reviewers` 生效。
> * **目的:** 确保审批权限边界不被突破，非法名单被拒。
> * **触发条件:** 改动涉及权限校验逻辑。

* [x] **可靠性与韧性测试**
> * **测试重点:** 并发安全（两人同时审核仅一人成功，另一人 409，MongoDB 条件更新）；审核失败回滚后 `reviewerId` 从 `reviewers[0]` 还原（旧单人数据无 `reviewers` 时操作人即原审批人）；历史数据兼容（上线前已存在申请无 `reviewers` 字段，查询展示不报错）。
> * **目的:** 确保或签并发正确、回滚还原正确、老数据无缝兼容。
> * **触发条件:** 涉及核心 Core 服务变更，且架构设计含可靠性与韧性设计。

* [ ] **可服务性与可观测性测试**
* [ ] **性能与伸缩性测试**

---

## 3. 专项验证设计和执行详情

### 3.1 功能测试专项

**1. 多选提交与通知验证（inc/full 各测）**:
* 前置条件: 门禁与每日检查均有未通过规则告警，仓库存在 ≥3 名 Committer
* 测试步骤:
    1. 开发者发起屏蔽申请，多选 3 名 Committer 提交
    2. 验证 `revision.reviewers` 落库为全员、`reviewerId`/`reviewerName` = 名单第一人
    3. 验证 message_apply 生成 3 条（`apply_associated_ids` 相同）
    4. 验证 3 名审批人各收到 1 封通知、待我审批均可见且 `auditNumber` > 0
    5. 分别在门禁（inc）与每日检查（full）场景重复验证
* 预期结果: 多选 3 人提交 → 3 人待办 + 3 封通知，落库字段符合设计

**2. 单人兼容验证**:
* 前置条件: 系统运行正常
* 测试步骤:
    1. 只传 `userId`、不传 `reviewerIds` 提交屏蔽申请
    2. 对比现网单人提交行为（落库、待办、通知）
* 预期结果: 与现网单人提交行为完全一致

**3. 或签审核验证**:
* 前置条件: 存在多审批人（A/B/C）待审申请
* 测试步骤:
    1. A 审批通过，验证成功、`reviewerId`/`reviewerName` 覆盖为 A、`reviewers` 仍为全员
    2. B、C 再审核，验证返回 409（通过/不通过均如此）
    3. 另一申请由 A 驳回，验证驳回即终结、申请人可重新发起
* 预期结果: 或签先成功者生效，任一人操作即终结，驳回与通过对称

**4. 转审多人验证**:
* 前置条件: 存在 reviewers=[A,B,C] 的待审申请，操作者为 B
* 测试步骤:
    1. B 将申请转给 [D,E]，验证 `referrals` 追加转审前审批人记录
    2. 验证 `reviewers` 替换为 [D,E]、`reviewerId`=D（第一人）
    3. 验证 D/E 收到通知，A/B/C 待办消失
    4. 验证新名单逐个 Committer 校验、不含申请人
* 预期结果: 转审后新名单生效、旧待办清理、通知与记录正确

**5. 查询出参与待办计数验证**:
* 前置条件: 存在本期新写入（有 reviewers）与历史（无 reviewers）两类申请
* 测试步骤:
    1. 问题详情 / 我的申请 / 待我审批列表查询，验证新申请出参带 `reviewers` 全员（成员带 userUrl），旧申请只有 `reviewerId`
    2. 验证 `CheckboardDelegateImpl.enrichDefectRevisionsWithUserUrls` 给 `reviewerId` 与 `reviewers` 成员均补 userUrl
    3. 验证「待我审批」OR 查询：名单内任意成员均可见该申请
    4. 验证 `applyAuditNumber` 计数条件 `(reviewerId = me OR reviewers.userId = me) AND reviewerStatus = 1`
* 预期结果: 出参「库里有什么返回什么」，待办可见性与计数多人正确

### 3.2 集成测试专项

**6. Committer 两级校验与 fallback 验证**:
* 前置条件: openlibing-framework 服务可用
* 测试步骤:
    1. 选择仓库级 Committer 提交，验证 MySQL 角色表校验命中
    2. 选择文件路径级 Committer 提交，验证 MySQL 未命中后走 framework fallback 正常提交
    3. 模拟 framework 不可用，验证文件路径 Committer 校验失败时该审批人判定非法、仓库级 Committer 不受影响
* 预期结果: 两级校验与 fallback 行为符合设计

### 3.3 安全与隐私测试专项

**7. 权限与名单校验验证**:
* 前置条件: 系统运行正常
* 测试步骤:
    1. 非 reviewers 成员调用审核接口，验证返回 403
    2. 提交时将申请人放入 `reviewerIds`，验证被拒
    3. 配置 `shield.max.reviewers` 上限，提交/转审超限名单，验证被拒且提交与转审共用该配置
* 预期结果: 权限拒绝、同人校验、人数上限均生效

### 3.4 可靠性与韧性测试专项

**8. 并发审核与回滚还原验证**:
* 前置条件: 存在多审批人待审申请
* 测试步骤:
    1. 两人（不同名单成员）几乎同时审核，验证仅一人成功、另一人 409
    2. 构造审核通过后写库失败场景，验证回滚后 `reviewerId`/`reviewerName` 从 `reviewers[0]` 还原
    3. 对旧单人数据（无 `reviewers`）执行审核失败回滚，验证操作人即原审批人
* 预期结果: 并发仅一人成功，回滚还原正确，新旧数据均兼容

**9. 历史数据兼容验证**:
* 前置条件: 库中存在上线前创建的申请（无 `reviewers` 字段）
* 测试步骤:
    1. 查询历史申请详情与列表，验证不报错、前端继续用 `reviewerId` 展示
    2. 对历史申请执行审核/转审，验证走 `reviewerId` 单人逻辑（`resolveReviewers` 回退）
* 预期结果: 历史数据查询与操作均正常，无需数据迁移
