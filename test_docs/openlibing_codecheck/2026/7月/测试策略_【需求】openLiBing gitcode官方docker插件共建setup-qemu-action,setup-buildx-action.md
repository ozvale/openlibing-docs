# openLiBing gitcode官方docker插件共建setup-qemu-action,setup-buildx-action 测试策略设计说明书

## 1. 基本信息

* **需求链接**: https://portal.edevops.huawei.com/ipdproject/third/2103073332; https://portal.edevops.huawei.com/ipdproject/third/2103073324
* **对应task(issueID)链接**: 与GitCode平台共建，无openlibing相关issue
* **需求名称**: openLiBing gitcode官方docker插件共建setup-qemu-action,setup-buildx-action
* **核心目标**:
  验证gitcode平台官方docker插件 setup-qemu-action 和 setup-buildx-action 能够实现与GitHub平台官方插件相同的核心功能，确保用户可以在gitcode CI流水线中正常使用这两个插件完成多架构容器镜像构建等任务。
* **开发责任人**: 宁欣龙
* **测试责任人**: 徐愚冰

---

## 2. 测试维度确认

> **操作指南**:请依据需求分析阶段的标签勾选。勾选后,必须在"第 3 节"提供对应的测试用例或方案。

* [x] **功能自检测试**

> * **测试重点:** setup-qemu-action 各输入参数生效、QEMU多架构仿真能力、容器跨平台运行；setup-buildx-action 各输入参数生效、Buildx构建器创建与配置、多平台镜像构建、输出信息正确性。
> * **目的:** 确保两个插件在gitcode平台上的核心功能与GitHub官方行为一致，各输入参数和输出结果符合预期。
> * **触发条件:** 强制执行,**可委托开发测试完成,测试完成验收**。

* [ ] **体验测试**

> * **测试重点:** 插件使用配置便捷性、错误提示友好性、日志输出可读性。
> * **目的:** 满足用户需求,确保用户能快速上手使用。
> * **触发条件:** 需求标签含 `need_experience`

* [x] **集成测试**

> * **测试重点:** setup-qemu-action与setup-buildx-action组合使用、与docker/build-push-action集成、与docker/login-action集成、gitcode CI流水线端到端多架构镜像构建与推送。
> * **目的:** 验证两个插件在gitcode CI流水线中的协同工作能力，确保多架构镜像构建与推送的完整链路正常。
> * **触发条件:** 需求标签含 `need_itest`

* [ ] **安全与隐私测试**

> * **测试重点:** 全量依赖漏洞扫描、高危/中危漏洞验证、敏感数据(PII)日志脱敏校验、鉴权绕过测试。
> * **目的:** 验证依赖漏洞已修复,确保无高危/中危漏洞,符合安全基线要求。
> * **触发条件:** 需求标签含 `need_security`

* [ ] **可靠性与韧性测试**

> * **测试重点:** 故障注入(Chaos)。模拟网络丢包/延迟、进程意外溢出、磁盘 IO 满载后等异常情况下的系统自愈行为。
> * **目的:** 验证架构设计中的"面向失败设计"等能力。
> * **触发条件:** 涉及核心Core服务变更,且架构设计含可靠性与韧性设计。

* [ ] **可服务性与可观测性测试**

> * **测试重点:** 告警有效性验证、指标准确性抽检、排障手册实操演练、优雅停机验证。
> * **目的:** 确保系统"可感知、可定位、可维护"。
> * **触发条件**: 涉及核心Core服务变更,且架构设计含可服务性与可观测性设计。

* [ ] **性能与伸缩性测试**

> * **测试重点:** 多架构镜像构建耗时、大规模并发构建场景下的资源消耗。
> * **目的:** 确保不产生性能退化,满足 SLO 要求。
> * **触发条件**: 涉及核心Core服务变更,且架构设计含性能与伸缩性设计。

---

## 3. 专项验证设计和执行详情

> 测试自检
* [ ] **Task 闭环**: 架构设计说明书中定义的 **TASK** 是否均有对应的测试结果?
* [ ] **证据留存**: 关键测试(如性能、安全扫描)是否附带了截图或报告链接?

### 3.1 功能测试专项

#### setup-qemu-action 功能测试

**1. setup-qemu-action 默认配置安装QEMU静态二进制文件成功**:
* 前置条件:gitcode CI流水线可正常运行，runner为ubuntu-latest
* 测试步骤:
* 1.在gitcode CI流水线配置中使用 `uses: gitcode/.../setup-qemu-action@v1`（默认配置，不传任何输入参数）
* 2.执行流水线
* 3.检查流水线执行日志，确认QEMU安装成功，无报错
* 4.验证QEMU静态二进制文件是否已正确安装到系统中
* 预期结果:
* setup-qemu-action默认配置执行成功，QEMU静态二进制文件正确安装，与GitHub平台行为一致

**2. setup-qemu-action 指定platforms参数安装特定平台QEMU仿真器**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `platforms: arm64,riscv64`
* 2.执行流水线
* 3.检查流水线日志，确认只安装了arm64和riscv64的QEMU仿真器
* 4.验证其他平台（如s390x、ppc64le等）未被安装
* 预期结果:
* 指定platforms参数后仅安装指定的平台仿真器，未指定平台不被安装，与GitHub平台行为一致

**3. setup-qemu-action 使用自定义image参数**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `image: tonistiigi/binfmt:latest`（或指定其他版本）
* 2.执行流水线
* 3.检查流水线日志，确认使用指定镜像安装QEMU
* 4.验证QEMU仿真器正常工作
* 预期结果:
* 自定义image参数生效，使用指定镜像安装QEMU，与GitHub平台行为一致

**4. setup-qemu-action 设置reset参数清除已有仿真器后重新安装**:
* 前置条件:gitcode CI流水线可正常运行，系统中已有QEMU仿真器
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `reset: true`
* 2.执行流水线
* 3.检查流水线日志，确认先清除已有仿真器后再安装
* 4.验证清除后重新安装的仿真器正常工作
* 预期结果:
* reset参数生效，清除已有仿真器后重新安装，与GitHub平台行为一致

**5. setup-qemu-action 设置cache-image参数控制缓存行为**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `cache-image: false`
* 2.执行流水线
* 3.检查日志确认未缓存binfmt镜像
* 4.再次设置 `cache-image: true` 执行，确认缓存行为
* 预期结果:
* cache-image参数生效，控制binfmt镜像的缓存行为，与GitHub平台行为一致

**6. setup-qemu-action 安装后运行跨架构容器验证QEMU仿真**:
* 前置条件:setup-qemu-action已成功安装QEMU
* 测试步骤:
* 1.在gitcode CI流水线中，setup-qemu-action步骤后添加一个步骤运行arm64平台容器
* 2.配置 `docker run --rm --platform linux/arm64 alpine uname -m`
* 3.执行流水线
* 4.检查输出结果是否为 `aarch64`
* 5.重复测试其他架构（如linux/riscv64、linux/s390x等）
* 预期结果:
* 跨架构容器正常运行，输出结果与目标架构一致（如arm64输出aarch64），与GitHub平台行为一致

**7. setup-qemu-action 输出platforms信息验证**:
* 前置条件:setup-qemu-action已成功安装QEMU
* 测试步骤:
* 1.在gitcode CI流水线中配置setup-qemu-action，并设置 `platforms: arm64,riscv64`
* 2.在后续步骤中读取 `steps.qemu.outputs.platforms`
* 3.验证输出值是否包含安装的平台列表
* 预期结果:
* platforms输出正确展示已安装的平台列表，与GitHub平台行为一致

#### setup-buildx-action 功能测试

**8. setup-buildx-action 默认配置创建Buildx构建器成功**:
* 前置条件:gitcode CI流水线可正常运行，runner为ubuntu-latest
* 测试步骤:
* 1.在gitcode CI流水线配置中使用 `uses: gitcode/.../setup-buildx-action@v1`（默认配置）
* 2.执行流水线
* 3.检查流水线日志，确认Buildx已安装并创建了docker-container驱动的构建器
* 4.验证构建器状态为running
* 预期结果:
* setup-buildx-action默认配置执行成功，创建docker-container驱动的构建器，与GitHub平台行为一致

**9. setup-buildx-action 指定version参数安装特定版本Buildx**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `version: v0.20.0`（指定一个具体版本）
* 2.执行流水线
* 3.检查日志确认安装的是指定版本的Buildx
* 4.验证该版本Buildx功能正常
* 预期结果:
* version参数生效，安装指定版本的Buildx，与GitHub平台行为一致

**10. setup-buildx-action 指定driver参数使用不同驱动**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `driver: docker`（使用docker驱动而非默认的docker-container）
* 2.执行流水线
* 3.检查日志确认创建了docker驱动的构建器
* 4.验证构建器输出driver字段为docker
* 预期结果:
* driver参数生效，创建指定驱动的构建器，与GitHub平台行为一致

**11. setup-buildx-action 指定driver-opts参数配置驱动选项**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `driver-opts: image=moby/buildkit:master,network=host`
* 2.执行流水线
* 3.检查日志确认驱动选项已生效
* 4.验证构建器使用指定镜像和网络配置
* 预期结果:
* driver-opts参数生效，驱动选项正确配置，与GitHub平台行为一致

**12. setup-buildx-action 指定buildkitd-flags参数配置BuildKit daemon标志**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `buildkitd-flags: --debug --allow-insecure-entitlement security.insecure`
* 2.执行流水线
* 3.检查日志确认BuildKit daemon以指定标志启动
* 4.验证构建器运行正常
* 预期结果:
* buildkitd-flags参数生效，BuildKit daemon使用指定标志启动，与GitHub平台行为一致

**13. setup-buildx-action 指定buildkitd-config-inline参数配置BuildKit daemon**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `buildkitd-config-inline` 包含registry mirror配置
* 2.执行流水线
* 3.检查日志确认BuildKit daemon使用了配置文件
* 4.验证registry mirror配置生效
* 预期结果:
* buildkitd-config-inline参数生效，BuildKit daemon配置正确应用，与GitHub平台行为一致

**14. setup-buildx-action 指定name参数使用自定义构建器名称**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `name: my-custom-builder`
* 2.执行流水线
* 3.检查日志确认构建器名称为my-custom-builder
* 4.验证输出name字段为my-custom-builder
* 预期结果:
* name参数生效，构建器使用指定名称，与GitHub平台行为一致

**15. setup-buildx-action 设置use参数控制是否切换到该构建器**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `use: false`
* 2.执行流水线
* 3.检查日志确认构建器已创建但未切换为当前使用
* 4.再次设置 `use: true` 验证切换行为
* 预期结果:
* use参数生效，控制是否切换到创建的构建器，与GitHub平台行为一致

**16. setup-buildx-action 指定endpoint参数连接远程Docker**:
* 前置条件:gitcode CI流水线可正常运行，有远程Docker socket或context
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `endpoint: tcp://remote-docker:2375`（或使用context名称）
* 2.执行流水线
* 3.检查日志确认构建器连接到指定endpoint
* 4.验证构建器在远程Docker上创建
* 预期结果:
* endpoint参数生效，构建器连接到指定的Docker endpoint，与GitHub平台行为一致

**17. setup-buildx-action 指定platforms参数固定构建器平台**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `platforms: linux/amd64,linux/arm64`
* 2.执行流水线
* 3.检查日志确认构建器平台被固定为linux/amd64和linux/arm64
* 4.验证输出platforms字段包含指定平台
* 预期结果:
* platforms参数生效，构建器平台被固定，与GitHub平台行为一致

**18. setup-buildx-action 设置cache-binary参数控制Buildx二进制缓存**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `cache-binary: false`
* 2.执行流水线
* 3.检查日志确认未缓存Buildx二进制文件
* 4.再次设置 `cache-binary: true` 验证缓存行为
* 预期结果:
* cache-binary参数生效，控制Buildx二进制的缓存行为，与GitHub平台行为一致

**19. setup-buildx-action 设置cleanup参数控制是否清理构建器**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `cleanup: false`
* 2.执行流水线
* 3.检查流水线结束后构建器是否未被清理
* 4.再次设置 `cleanup: true` 验证清理行为
* 预期结果:
* cleanup参数生效，控制流水线结束后是否清理构建器，与GitHub平台行为一致

**20. setup-buildx-action 输出信息验证**:
* 前置条件:setup-buildx-action已成功执行
* 测试步骤:
* 1.在gitcode CI流水线中配置setup-buildx-action
* 2.在后续步骤中读取以下输出：
*   a. `steps.buildx.outputs.name` - 构建器名称
*   b. `steps.buildx.outputs.driver` - 构建器驱动类型
*   c. `steps.buildx.outputs.platforms` - 可用平台列表
*   d. `steps.buildx.outputs.nodes` - 构建器节点元数据（JSON格式）
* 3.验证各输出值格式正确、内容准确
* 预期结果:
* 所有输出字段正确返回，格式与GitHub平台一致，节点元数据JSON包含name、endpoint、status、buildkitd-flags、buildkit、platforms等字段

**21. setup-buildx-action 使用append参数附加额外节点到构建器**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线配置中设置append参数，附加一个远程节点
* 2.执行流水线
* 3.检查日志确认附加节点已添加到构建器
* 4.验证nodes输出包含多个节点信息
* 预期结果:
* append参数生效，附加节点成功添加到构建器，与GitHub平台行为一致

**22. setup-buildx-action 设置keep-state参数保持BuildKit状态**:
* 前置条件:gitcode CI流水线可正常运行（使用持久化self-hosted runner）
* 测试步骤:
* 1.在gitcode CI流水线配置中设置 `keep-state: true`
* 2.执行流水线
* 3.检查流水线结束后BuildKit状态是否保持
* 4.验证状态文件未被清理
* 预期结果:
* keep-state参数生效，BuildKit状态在流水线结束后保持，与GitHub平台行为一致

**23. setup-buildx-action standalone模式（不使用Docker CLI）**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.在gitcode CI流水线中配置setup-buildx-action，driver设置为 `docker-container`
* 2.在后续步骤中直接使用buildx二进制（不通过docker buildx命令）
* 3.执行流水线
* 4.验证buildx standalone模式可正常工作
* 预期结果:
* standalone模式下buildx可直接使用，无需依赖Docker CLI，与GitHub平台行为一致

### 3.2 集成测试专项

**24. setup-qemu-action + setup-buildx-action + build-push 构建并推送多架构镜像**:
* 前置条件:gitcode CI流水线可正常运行，Docker镜像仓库可访问
* 测试步骤:
* 1.配置gitcode CI流水线，依次执行：
*   a. setup-qemu-action（默认配置）
*   b. setup-buildx-action（默认配置）
*   c. docker/login-action（登录到镜像仓库）
*   d. docker/build-push-action（构建并推送多架构镜像，指定platforms: linux/amd64,linux/arm64,linux/arm/v7）
* 2.执行流水线
* 3.验证setup-qemu-action执行成功，QEMU安装正常
* 4.验证setup-buildx-action执行成功，构建器创建正常
* 5.验证login-action登录成功
* 6.验证build-push-action成功构建多架构镜像并推送到仓库
* 7.从镜像仓库拉取各架构镜像，确认镜像层正确
* 预期结果:
* 完整CI流水线正常执行，多架构镜像成功构建并推送，各架构镜像可正常拉取使用，与GitHub平台行为一致

**25. setup-qemu-action + setup-buildx-action 组合使用构建多架构镜像（不推送）**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.配置gitcode CI流水线，依次执行：
*   a. setup-qemu-action（设置platforms: arm64,riscv64）
*   b. setup-buildx-action（设置driver-opts包含registry mirror）
*   c. docker buildx build --platform linux/arm64,linux/riscv64 -t test:latest .
* 2.执行流水线
* 3.验证跨架构构建成功
* 4.验证构建产物包含两个架构的镜像
* 预期结果:
* setup-qemu-action与setup-buildx-action组合使用正常，成功构建多架构镜像，各参数生效

**26. setup-buildx-action 与docker/login-action集成验证**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.配置gitcode CI流水线，先执行setup-buildx-action，再执行docker/login-action
* 2.验证登录状态是否在buildx构建器中生效
* 3.执行docker buildx build并推送镜像到私有仓库
* 4.验证推送成功
* 预期结果:
* setup-buildx-action与docker/login-action集成正常，登录凭证在构建器中生效，与GitHub平台行为一致

**27. setup-buildx-action 使用buildkitd-config配置registry mirror后构建加速验证**:
* 前置条件:gitcode CI流水线可正常运行，有可用的registry mirror
* 测试步骤:
* 1.配置setup-buildx-action，设置buildkitd-config-inline包含registry mirror配置
* 2.执行docker buildx build构建镜像
* 3.检查构建日志，确认使用了registry mirror拉取基础镜像
* 4.验证构建成功
* 预期结果:
* registry mirror配置生效，构建过程中通过mirror拉取镜像，与GitHub平台行为一致

### 3.3 体验测试专项

**28. 插件使用配置便捷性验证**:
* 前置条件:gitcode CI流水线可正常运行
* 测试步骤:
* 1.参考gitcode平台文档配置setup-qemu-action和setup-buildx-action
* 2.验证配置语法与GitHub平台一致，用户无需额外学习成本
* 3.验证插件支持常用的GitHub平台配置方式（如uses、with等）
* 4.验证配置错误时给出明确提示
* 预期结果:
* 插件配置方式与GitHub平台一致，用户可无缝迁移，配置错误时有明确提示

**29. 插件日志输出可读性验证**:
* 前置条件:gitcode CI流水线中已配置并使用两个插件
* 测试步骤:
* 1.执行包含两个插件的流水线
* 2.检查流水线日志中各步骤的日志输出
* 3.验证日志是否清晰展示安装/配置过程、版本信息、结果状态
* 4.验证错误日志是否包含足够的排查信息
* 预期结果:
* 日志输出清晰可读，包含关键信息，错误时有明确排查线索