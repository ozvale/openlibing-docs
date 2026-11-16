# software-pack-zip-deep-check — 软件包上传 zip 深度校验与压缩炸弹防护

## 需求背景

`ToolApplyController.saveToolSoftwarePack` 支持整片与分片两种上传模式，当前均缺乏压缩炸弹防护，且格式校验停留在表层：

| 路径 | 现有格式校验 | 压缩炸弹防护 |
|------|------------|------------|
| 整片上传 | ImageCheckUtil 表层校验（魔数/扩展名/大小 ≤5MB） | 无 |
| 分片上传 | 仅首片 4 字节 zip 魔数（后续分片内容不受控，合并后可非合法 zip） | 无 |

恶意用户可上传高压缩比 zip 炸弹（如 3KB→5.6GB），或借分片路径绕过格式校验上传任意内容。

## 功能描述

**新增 `ZipSecurityCheckUtil`**（common/utils）：基于 zip 中央目录的深度校验，仅读条目元数据、不解压条目内容（JDK `ZipFile` 原生支持 zip64）：

1. 深度格式校验：zip 结构必须合法（`ZipException` 拒绝），且至少含 1 个条目
2. 压缩炸弹检测（三项独立阈值，Nacos 可配置，缺省回退默认值）：
   - 解压后总大小 ≤ `tool.software.pack.max.uncompressed.size`（MB，默认 10240）
   - 整体压缩比 ≤ `tool.software.pack.max.compression.ratio`（默认 100）
   - 条目数 ≤ `tool.software.pack.max.zip.entries`（默认 100000）

**接入两条上传路径**：

- 整片上传：`validateSoftwarePackFile` 保留 ImageCheckUtil 表层校验后，落临时文件执行深度校验（≤5MB，成本可忽略）
- 分片上传：`completeChunkUpload` 在 OBS 合并成功后，`downloadObject` 流式拷贝到临时文件（带 maxPackSize 硬上限防御性截断，防 Redis 累计计数被并发绕过）→ 深度校验；**失败关闭**：校验失败（含下载失败）即删除已合并 OBS 对象 + 清理会话 + 返回失败。同时补齐原始设计注释"从OBS下载流式扫描"的意图

**不做**：嵌套 zip 炸弹（42.zip 类）递归扫描——顶层中央目录无法观测内层条目，需解压侧控制兜底，如需可作为后续增强。

## 验收标准

- [ ] 整片上传：合法 zip 通过；非法 zip（魔数+垃圾）被拒；高压缩比炸弹（zeros，ratio>1000）被拒
- [ ] 分片上传：合并后为炸弹 → OBS 对象被删除 + 会话清理 + 返回失败；合并后非法 zip → 同样拒绝
- [ ] 三个阈值 Nacos 可配置，配置缺失/非法时回退默认值
- [ ] 深度校验不解压条目内容（仅中央目录元数据），单次扫描代价为顺序 IO
- [ ] 现有测试改造：at-limit 用例由伪 zip（魔数+全零）改为真实 zip
- [ ] spotless + 相关测试全绿

## 影响范围

- `saveToolSoftwarePack` 接口行为变化：整片与分片（最后一片）新增深度校验，非法/炸弹文件被拒
- 分片上传最后一片响应时间增加一次 OBS 合并对象下载（同 VPC）
- 无 schema / 接口契约变化；新增 3 个 Nacos 可选配置键
