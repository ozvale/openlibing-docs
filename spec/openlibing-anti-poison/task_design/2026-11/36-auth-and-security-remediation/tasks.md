# 36-auth-and-security-remediation — 实现任务

## 进度: 5/5 complete

- [x] Task 1: 引入服务端统一鉴权，userId 从登录态/Token 解析，禁止信任客户端参数
- [x] Task 2: 命令执行改 ProcessBuilder 参数数组，gitUrl/raw_url 白名单校验，token 不入命令行/URL
- [x] Task 3: 版本库移除公网 Nacos 地址与明文凭据，改环境变量/启动参数注入
- [x] Task 4: 关闭 actuator shutdown、RequestMapping 限定方法、出网请求内网 IP 校验
- [x] Task 5: P2 项整改：tableName 白名单、MongoDB TLS、安全响应头、POI 转义、fastjson2 配置、依赖版本锁定
