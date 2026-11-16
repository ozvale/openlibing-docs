# software-pack-zip-deep-check — 实现任务

## 进度: 5/5 complete

- [x] Task 1: 新增 ZipSecurityCheckUtil（checkZipSafety：结构合法性 + 条目数 + 解压总大小 + 压缩比，仅读中央目录）
- [x] Task 2: ToolApplyServiceImpl 新增 3 个 Nacos 阈值配置（${key:default} + 解析回退）
- [x] Task 3: 整片路径 validateSoftwarePackFile 追加深度校验（临时文件，finally 清理）
- [x] Task 4: 分片路径 completeChunkUpload 合并后下载扫描（fail-closed：失败删 OBS 对象 + 清会话）
- [x] Task 5: 测试 — ZipSecurityCheckUtilTest（正常/非法/空/高比例/条目数/总大小）+ 服务级（炸弹拒、非法拒、合并后炸弹删对象、at-limit 改真实 zip）

## 验证方式

- `python scripts/run-mvn.py spotless:apply test -Dtest=ZipSecurityCheckUtilTest,ToolApplyServiceImplTest`
- 实测：spotless 0 修正；60 个测试 0 失败 0 错误（util 6 个 + 服务级 54 个）
- 修复记录：validateZipDeep 首版 Files.copy 未带 REPLACE_EXISTING，目标临时文件已存在抛 FileAlreadyExistsException，已修复
