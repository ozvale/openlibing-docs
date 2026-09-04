# 仿真资源增删改接口 — 实现任务

## 进度: 0/N complete

### Mapper 层

- [ ] M1: 新建 `mapper/ServerResourceMapper.java` + `resources/mapper/ServerResourceMapper.xml`
       t_server_basic_info：insertServer / updateServer / deleteServer（逻辑删 is_deleted='1'）
       t_server_extend_info：insertExtend / updateExtend / deleteExtend（物理删）
       t_server_using：insertUsing / updateUsing / deleteUsing（逻辑删）
- [ ] M2: 扩展 `mapper/EngineBasicInfoMapper.java` + XML：insertEngine / updateEngine / deleteEngine（物理删）
- [ ] M3: 扩展 `mapper/QcowInfoMapper.java` + XML：insertQcow / updateQcow / deleteQcow（物理删）
- [ ] M4: 扩展 `mapper/ResourceAttachmentMapper.java` + XML：insertAttachment / updateAttachment / deleteAttachment（物理删）

### Service 层

- [ ] S1: `service/ServerResourceService.java` + `impl/ServerResourceServiceImpl.java`（basic/extend/using 各 add/update/delete）
- [ ] S2: `service/EngineResourceService.java` + `impl/EngineResourceServiceImpl.java`
- [ ] S3: `service/QcowResourceService.java` + `impl/QcowResourceServiceImpl.java`
- [ ] S4: `service/AttachmentResourceService.java` + `impl/AttachmentResourceServiceImpl.java`
       （含：id=CommmonUtils.getUuid()、creator 从调用方透传、审计时间、参数校验返回 400、不存在返回 400）

### Controller 层

- [ ] C1: `controller/ServerResourceController.java`（/simulation/manage/server/basic|extend|using/{add,update,delete}）
- [ ] C2: `controller/EngineResourceController.java`（/simulation/manage/engine/{add,update,delete}）
- [ ] C3: `controller/QcowResourceController.java`（/simulation/manage/qcow/{add,update,delete}）
- [ ] C4: `controller/AttachmentResourceController.java`（/simulation/manage/attachment/{add,update,delete}）

### 测试与验证

- [ ] T1: 为 4 个 Service 新增单测（Mockito），覆盖成功/参数缺失/删除逻辑删 3 分支
- [ ] T2: `mvn test` 全量通过（jacoco 20% line 门槛保持）
- [ ] T3: pre-commit 通过；`mvn validate` enforcer 通过
- [ ] T4: 业务 PR 关联 #26 + ai-assisted 标签

### 涉及文件（预估新增/修改）

新增 Java：`entity/`（0，直接用现有实体）｜ `mapper/ServerResourceMapper.java`、`service/`×4 接口、`service/impl/`×4 实现、`controller/`×4
新增 XML：`resources/mapper/ServerResourceMapper.xml`
修改 Java：`mapper/EngineBasicInfoMapper.java`、`mapper/QcowInfoMapper.java`、`mapper/ResourceAttachmentMapper.java`
修改 XML：`EngineBasicInfoMapper.xml`、`QcowInfoMapper.xml`、`ResourceAttachmentMapper.xml`
