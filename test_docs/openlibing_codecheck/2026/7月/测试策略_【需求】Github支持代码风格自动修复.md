# Github支持代码风格自动修复 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2104586651
* **对应task(issueID)链接**: https://gitcode.com/openlibing/openlibing-coderepo/issues/67
* **需求名称**: Github支持代码风格自动修复
* **核心目标**:
  验证github开源仓能够成功接入pre-commit.ci并在PR中触发代码风格自动修复，pre-commit.ci检测到代码风格问题后能自动修复并提交到PR分支，PR中正确呈现pre-commit.ci执行状态，与现有PR门禁流水线解耦独立运行。
* **开发责任人**: 吴志文
* **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

> **操作指南**:请依据需求分析阶段的标签勾选。勾选后,必须在"第 3 节"提供对应的测试用例或方案。

* [x] **功能自检测试**

> * **测试重点:** github开源仓接入pre-commit.ci、PR中触发自动修复、修复后自动提交到PR分支、PR检查状态呈现。
>* **目的:** 确保pre-commit.ci在github开源仓PR流程中能正确触发、检测、修复并提交代码风格问题，PR中状态展示符合预期。
>* **触发条件:** 强制执行,**可委托开发测试完成,测试完成验收**。

* [ ] **体验测试**

> * **测试重点:** 站在用户角度进行体验使用,验证产品是否符合用户习惯。
>* **目的:** 满足用户需求,超出用户期望;判定产品是否能让用户快速的接受和使用。
>* **触发条件:** 需求标签含 `need_experience`

* [x] **集成测试**

> * **测试重点:** pre-commit.ci与github PR流程集成、修复结果与本地pre-commit修复结果一致性、与PR门禁流水线解耦独立运行。
>* **目的:** 验证pre-commit.ci与github PR流程衔接正常，修复结果可靠，与现有PR门禁体系无耦合影响。
>* **触发条件:** 需求标签含 `need_itest`

* [ ] **安全与隐私测试**:

> * **测试重点:** 全量依赖漏洞扫描、高危/中危漏洞验证、敏感数据(PII)日志脱敏校验、鉴权绕过测试。
>* **目的:** 验证依赖漏洞已修复,确保无高危/中危漏洞,符合安全基线要求。
>* **触发条件:** 需求标签含 `need_security`

* [ ] **可靠性与韧性测试**

> * **测试重点:** 故障注入(Chaos)。模拟网络丢包/延迟、进程意外溢出、磁盘 IO 满载后等异常情况下的系统自愈行为。
>* **目的:** 验证架构设计中的"面向失败设计"等能力。
>* **触发条件:** 涉及核心Core服务变更,且架构设计含可靠性与韧性设计。

* [ ] **可服务性与可观测性测试**

> * **测试重点:** 告警有效性验证、指标准确性抽检、排障手册实操演练、优雅停机验证。
>* **目的:** 确保系统"可感知、可定位、可维护"。
>* **触发条件**:  涉及核心Core服务变更,且架构设计含可服务性与可观测性设计。

* [ ] **性能与伸缩性测试**

> * **测试重点:** 基准测试、负载测试。验证延迟、吞吐量上限及资源配额(CPU/Mem)稳定性。
>* **目的:** 确保不产生性能退化,满足 SLO 要求。
>* **触发条件**: 涉及核心Core服务变更,且架构设计含性能与伸缩性设计。

---

## 3. 专项验证设计和执行详情

> 测试自检
* [ ] **Task 闭环**: 架构设计说明书中定义的 **TASK** 是否均有对应的测试结果?
* [ ] **证据留存**: 关键测试(如性能、安全扫描)是否附带了截图或报告链接?

### 3.1 功能测试专项

**1. github开源仓接入pre-commit.ci并在PR中触发**:
* 前置条件:github开源仓已创建，仓库已安装pre-commit.ci GitHub App
* 测试步骤:
* 1.在github开源仓的.pre-commit-config.yaml中配置pre-commit钩子
* 2.创建包含代码风格问题的特性分支
* 3.向main分支提交PR，触发pre-commit.ci执行
* 4.查看PR中pre-commit.ci检查的状态(Pending/Success/Failure)
* 5.查看pre-commit.ci执行日志，确认钩子被正确加载
* 预期结果:
* pre-commit.ci在PR中被成功触发，PR检查列表中正确呈现pre-commit.ci执行状态

**2. pre-commit.ci检测到代码风格问题后自动修复并提交到PR分支**:
* 前置条件:github开源仓已接入pre-commit.ci，PR已触发
* 测试步骤:
* 1.提交包含lint或format问题的代码到PR
* 2.等待pre-commit.ci执行完成
* 3.查看pre-commit.ci执行日志，确认检测到的代码风格问题列表
* 4.验证pre-commit.ci是否对检测到的问题执行了自动修复
* 5.查看PR分支的提交记录，确认修复提交由pre-commit.ci bot自动推送
* 6.验证PR中pre-commit.ci最终状态为Success
* 预期结果:
* pre-commit.ci成功检测代码风格问题，自动修复并将修复结果提交到PR分支，PR最终检查状态通过

**3. 代码无风格问题时pre-commit.ci正常通过**:
* 前置条件:github开源仓已接入pre-commit.ci
* 测试步骤:
* 1.提交符合代码风格规范的代码到PR
* 2.等待pre-commit.ci执行完成
* 3.查看pre-commit.ci执行日志，确认无代码风格问题
* 4.验证PR中pre-commit.ci状态为Success
* 预期结果:
* pre-commit.ci正常执行，无代码风格问题时检查通过，PR可正常合并

**4. 多种代码语言混合场景下pre-commit.ci正常处理**:
* 前置条件:github开源仓已接入pre-commit.ci，仓库包含多种语言
* 测试步骤:
* 1.提交同时包含Python和JavaScript代码风格问题的PR
* 2.等待pre-commit.ci执行完成
* 3.查看pre-commit.ci执行日志，确认两种语言钩子都被加载执行
* 4.验证两种语言的问题均被自动修复
* 5.确认PR分支获得自动修复提交
* 预期结果:
* pre-commit.ci能正确处理多语言混合场景，各语言钩子独立执行并完成修复

**5. pre-commit.ci自动修复失败时PR中给出明确提示**:
* 前置条件:github开源仓已接入pre-commit.ci
* 测试步骤:
* 1.提交包含无法自动修复的代码风格问题(如语法错误导致无法格式化)的PR
* 2.等待pre-commit.ci执行完成
* 3.查看pre-commit.ci执行日志，确认失败原因
* 4.验证PR中pre-commit.ci状态为Failure
* 5.检查PR评论或日志中是否有明确的失败原因说明
* 预期结果:
* pre-commit.ci正确报告失败状态，PR中清晰展示失败原因，便于开发者定位

### 3.2 集成测试专项

**6. pre-commit.ci修复结果与本地pre-commit修复结果一致性**:
* 前置条件:github开源仓已接入pre-commit.ci，本地环境已配置pre-commit
* 测试步骤:
* 1.本地检出同一PR分支代码
* 2.本地执行pre-commit run --all-files获取修复结果
* 3.对比pre-commit.ci修复后的代码差异
* 4.验证两者的修复行为和修复结果一致
* 预期结果:
* pre-commit.ci与本地pre-commit执行相同的钩子，修复结果完全一致

**7. 移除pre-commit.ci集成后本地pre-commit仍可独立运行**:
* 前置条件:github开源仓已接入pre-commit.ci
* 测试步骤:
* 1.在仓库中卸载pre-commit.ci GitHub App
* 2.本地克隆仓库代码
* 3.本地执行pre-commit install并触发git commit
* 4.验证本地pre-commit钩子能正常拦截代码风格问题
* 5.确认pre-commit.ci移除后不影响本地pre-commit工作流
* 预期结果:
* pre-commit.ci与本地pre-commit解耦，移除pre-commit.ci不影响本地代码风格校验能力
