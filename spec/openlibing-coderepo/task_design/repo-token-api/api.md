> 归档说明：本文件为「【黄蓝协同】openlibing代码仓Token鉴权信息自动获取」的调用方接口说明（机机接口，非前端接口）。
> 接口：`POST /repo-token/internal/fetch`（APIG 对外建议 `/repo-token/v1/fetch`）；业务 PR：!231。

# 代码仓 Token 获取接口 · 调用方接入文档

> 版本：1.0（2026-10-13）｜ 对应实现分支 `feat/repo-token-api`
> 适用对象：经 APIG 调用本接口的指定服务（机机调用，**前端不调用**）

---

## 1. 接口基本信息

| 项            | 值                                                      |
| ------------- | ------------------------------------------------------- |
| 方法          | `POST`                                                  |
| 内部路径      | `/repo-token/internal/fetch`                            |
| APIG 对外路径 | `/repo-token/v1/fetch`（以网关发布为准）                |
| Content-Type  | `application/json`                                      |
| 字符编码      | UTF-8                                                   |
| 批量上限      | 单次最多 **100** 个仓库地址                             |
| 限流          | 网关按 App 限流（当前约定 10 QPS，以 APIG 配置为准）    |
| 幂等性        | 幂等查询；但每个请求的 nonce 只能使用一次（重复即 401） |

---

## 2. 请求头（鉴权三要素，缺一即 401）

| 头                 | 必填 | 格式                                          | 说明                                                    |
| ------------------ | ---- | --------------------------------------------- | ------------------------------------------------------- |
| `X-Auth-Timestamp` | 是   | 毫秒时间戳                                    | 与服务器时间偏差须在 **±5 分钟**内（调用方需 NTP 校时） |
| `X-Auth-Nonce`     | 是   | **32~128 位 hex**（服务端强校验，不符即 401） | **一次性**：10 分钟内不可重复（服务端 Redis 登记）      |
| `X-Auth-Signature` | 是   | Base64                                        | ECDSA 签名，见下方签名算法                              |

另有 `Authorization` 头（如有）会被 APIG 消费/透传，与应用层鉴权无关。

### 2.1 签名算法（逐字节约定）

```
canonical = timestamp + "\n" + nonce + "\n" + sha256hex(body)
signature = SHA256withECDSA(私钥, canonical)  →  Base64
```

- `body` 取**原始请求字节**（序列化后不要改动任何字符，否则摘要不符）；
- `sha256hex` 为小写 hex（64 字符）；
- 三段以 `\n`（单个换行符）拼接，共 3 行；
- 签名算法固定 **SHA256withECDSA**，密钥为 **EC P-256** 私钥（PKCS#8）。

Java 示例：

```java
String canonical = timestamp + "\n" + nonce + "\n" + sha256Hex(bodyBytes);
Signature signer = Signature.getInstance("SHA256withECDSA");
signer.initSign(privateKey);            // EC P-256 私钥
signer.update(canonical.getBytes(StandardCharsets.UTF_8));
String signature = Base64.getEncoder().encodeToString(signer.sign());
```

---

## 3. 请求体

```json
{
  "repoUrls": [
    "https://gitcode.com/org/repo-a.git",
    "https://github.com/org/repo-b.git"
  ]
}
```

| 字段       | 类型           | 必填 | 约束                                                                                                    |
| ---------- | -------------- | ---- | ------------------------------------------------------------------------------------------------------- |
| `repoUrls` | `List<String>` | 是   | 非空；≤100 条（超限整体拒绝）；自动去重与去空白；与库中 `repo_url` **精确匹配**（不归一化 `.git` 后缀） |

> 同一仓库地址被多个项目引用时（库中 `(repo_url, project_id)` 唯一索引，允许多行），服务端按
> **`token_status=valid` 优先 → `repo_id` 最小** 的确定性规则选择一行返回，不会因多行而误报 `not_found`。

> **请求体大小上限 64 KB**（100 条仓库地址远小于该值）。超限在验签前直接拒绝，返回 **413**
> `{"code":413,"message":"request body exceeds 64KB limit"}`。

---

## 4. 响应体

### 4.1 结构

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "ephemeralPublicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE...", // Base64(X.509)
    "items": [
      {
        "repoUrl": "https://gitcode.com/org/repo-a.git",
        "tokenMeta": {
          "status": "valid",
          "expiration": "2027-10-13T16:00:00Z",
          "scopes": "read_user,read_repository,..."
        },
        "iv": "qxMl6h2h9NqwJft+", // Base64(12 字节 GCM IV)
        "cipherToken": "D96S4pb+O1/O4g..." // Base64(AES-256-GCM 密文，含 128bit tag)
      },
      {
        "repoUrl": "https://gitee.com/org/repo-c.git",
        "tokenMeta": {
          "status": "unsupported",
          "expiration": null,
          "scopes": null
        },
        "iv": null,
        "cipherToken": null
      }
    ]
  }
}
```

### 4.2 顶层字段

| 字段                      | 类型          | 说明                                                                          |
| ------------------------- | ------------- | ----------------------------------------------------------------------------- |
| `code`                    | int           | 200 成功；非 200 见错误处理                                                   |
| `msg`                     | string        | success / 错误描述                                                            |
| `data.ephemeralPublicKey` | string · 可空 | 本次响应的临时 EC 公钥（Base64 X.509）；**存在密文时必有**，全降级响应为 null |
| `data.items[]`            | array         | 与请求 `repoUrls` 顺序一一对应                                                |

### 4.3 `items[]` 字段

| 字段                   | 类型          | 说明                                                                                                                |
| ---------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------- |
| `repoUrl`              | string        | 对应请求中的仓库地址                                                                                                |
| `tokenMeta.status`     | string        | 见 4.4 状态表                                                                                                       |
| `tokenMeta.expiration` | string · 可空 | 令牌过期时间，**统一 ISO-8601 UTC**（如 `2027-10-13T16:00:00Z`）；平台未提供或不可解析时为 `null`（勿当作永不过期） |
| `tokenMeta.scopes`     | string · 可空 | 令牌权限范围（平台原样），可能为 null                                                                               |
| `iv`                   | string · 可空 | GCM IV（Base64，12 字节）；仅存在密文时有值                                                                         |
| `cipherToken`          | string · 可空 | AES-256-GCM 加密的 token（Base64）；**仅 `status=valid/unsupported` 时有值**                                        |

### 4.4 `status` 枚举与下发条件

| status        | 含义                                                           | 密文下发                                  |
| ------------- | -------------------------------------------------------------- | ----------------------------------------- |
| `valid`       | 平台确认令牌有效                                               | ✅ 下发                                   |
| `unsupported` | 平台不提供令牌元信息（如 Gitee），令牌已配置但**未经平台校验** | ✅ 下发（调用方必须自行处理平台 401/404） |
| `invalid`     | 平台确认令牌失效                                               | ❌                                        |
| `unknown`     | 元数据尚未刷新（新录入仓库）                                   | ❌                                        |
| `unavailable` | 状态有效但未能解析出可用令牌                                   | ❌                                        |
| `not_found`   | repoUrl 未录入本平台                                           | ❌                                        |

---

## 5. 调用方解密步骤

```
1. aesKey = ECDH(自身EC私钥, data.ephemeralPublicKey) 后取 SHA-256   → AES-256 密钥
2. 对每个 item:
   plain = AES-256-GCM-Decrypt(
             key = aesKey,
             iv  = Base64Decode(item.iv),          // 12 字节
             ciphertext = Base64Decode(item.cipherToken),  // 末尾 16 字节为 tag
             aad  = item.repoUrl 的 UTF-8 字节      // ★ AAD 必须传 repoUrl，防调包
           )
3. token = UTF-8(plain)
```

Java 示例：

```java
KeyAgreement ka = KeyAgreement.getInstance("ECDH");
ka.init(privateKey);                    // 调用方 EC 私钥
ka.doPhase(ephemeralPublicKey, true);   // 响应中的临时公钥
byte[] shared = ka.generateSecret();
SecretKey aesKey = new SecretKeySpec(MessageDigest.getInstance("SHA-256").digest(shared), "AES");

Cipher aes = Cipher.getInstance("AES/GCM/NoPadding");
aes.init(Cipher.DECRYPT_MODE, aesKey, new GCMParameterSpec(128, iv));
aes.updateAAD(repoUrl.getBytes(StandardCharsets.UTF_8));
byte[] token = aes.doFinal(cipherToken);
```

> ★ AAD 缺失或不符会抛 `AEADBadTagException`——这是防止响应内密文被调包到其他仓库条目的保护，请勿忽略该异常。

---

## 6. 错误处理

### 6.1 HTTP 层

| HTTP | 触发条件                                                                           | 调用方处理                                                                                              |
| ---- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| 401  | 缺头 / 时间戳超窗 / **nonce 格式不符（非 32~128 位 hex）** / nonce 重复 / 签名不符 | 检查本机时钟与 nonce 生成逻辑（32 位 hex 随机）；换新 nonce 重签；持续 401 联系管理员（可能密钥被吊销） |
| 503  | `repo-token.enabled=false`（接口整体下线）                                         | 停止调用，等待恢复通知                                                                                  |
| 429  | 网关流控                                                                           | 退避重试                                                                                                |

### 6.2 业务层（HTTP 200，看 code）

| code                 | 含义                                                |
| -------------------- | --------------------------------------------------- |
| 200                  | 成功（逐条看 items 内的 status）                    |
| 非 200（如 5010000） | 服务异常，`msg`/`data` 含描述，可退避重试或联系运维 |

**重要**：HTTP 200 且 `code=200` 不代表每个仓库都拿到了 token——**逐条检查 `items[].tokenMeta.status` 与 `cipherToken` 是否存在**。

---

## 7. 约束与注意事项

1. **token 明文不落盘、不进日志**；使用完毕即弃，勿缓存于内存以外的地方；
2. `expiration` 仅是元数据快照，使用 token 时仍需处理平台返回的 401；
3. `unsupported` 状态（Gitee）表示"平台不提供元信息"，令牌有效性未经校验，**必须处理平台 401/404**；
4. 每次请求应使用**新 nonce**与**新时间戳**；同 nonce 重发会被 401（防重放）；
5. 签名私钥仅存于调用方内网配置（如 Nacos），不得出内网、不得入库；支持 Base64 本体或完整 PEM 两种形态（公钥同）；
6. 密钥轮换：与服务方约定低峰窗口，服务方先换公钥、调用方随后切私钥，失败回退。

---

## 8. 完整示例（真实报文）

**请求：**

```http
POST /repo-token/internal/fetch HTTP/1.1
Content-Type: application/json
X-Auth-Timestamp: 1792053647298
X-Auth-Nonce: 019938cc249859524d95521737fbcd9f
X-Auth-Signature: MEUCIArkHq/RQzTw51gM4LSQAjFbP6p7RajDsgTKVtTQmw1NAiEA0IiR6Cfc9rNazCrCyCzDJ4F5OdXXpkBToz2k9X+1kXE=

{"repoUrls":["https://gitcode.com/openUBMC/account.git","https://github.com/cuishiying-1/test.git","https://gitee.com/stridexq/test-pr-management.git"]}
```

**响应（节选）：**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "ephemeralPublicKey": "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEm+8TYNmQD6TZm9rb3Fy7UsfhGk9tOsnflw8XNjUSF89S0w6ISzPjlk8L8v1oabXm9UCkdzEfj8roj8E4iVhOQQ==",
    "items": [
      {
        "repoUrl": "https://gitcode.com/openUBMC/account.git",
        "tokenMeta": {
          "status": "valid",
          "expiration": "2027-10-13T16:00:00Z",
          "scopes": "read_user,read_key,..."
        },
        "iv": "y3nTIOe5lfVqYNHz",
        "cipherToken": "OeCJUDskTAYp8OY0fyziV6NuCk8Nn8LuvneKZKEpTl4sJbItOZh0pw=="
      },
      {
        "repoUrl": "https://github.com/cuishiying-1/test.git",
        "tokenMeta": {
          "status": "valid",
          "expiration": "2026-11-23T06:55:13Z",
          "scopes": "admin:enterprise,..."
        },
        "iv": "lRmxc/uDMlH5T8lJ",
        "cipherToken": "m7rmgGNlm2/6lqgfT8MZb5cuxqalA0eIMT3uE1azG1SP6KujvCZAJeocPLkJ292B6OpZRdoUdVg="
      },
      {
        "repoUrl": "https://gitee.com/stridexq/test-pr-management.git",
        "tokenMeta": {
          "status": "unsupported",
          "expiration": null,
          "scopes": "--"
        },
        "iv": "trbHL+RCVYM/7mcp",
        "cipherToken": "YLIC3UtkdXvmbUgf734SqTG9OboUbENcwxQE3SEzw65PqidDgRdj5icZbFvmCuIY"
      }
    ]
  }
}
```

---

## 9. 配置要求（双方）

| 侧       | 配置项                   | 说明                                                                        |
| -------- | ------------------------ | --------------------------------------------------------------------------- |
| 调用方   | 私钥                     | EC P-256 PKCS#8，存内网 Nacos（支持 Base64 本体或完整 PEM），**永不出内网** |
| coderepo | `repo-token.public-key`  | 调用方公钥（Base64 本体，推荐；兼容完整 PEM），Nacos 明文存放               |
| coderepo | `repo-token.fingerprint` | `sha256:` + 公钥 DER SHA-256 前 16 字节 hex；启动自检，不一致拒绝启动       |
| coderepo | `repo-token.enabled`     | 总开关；false 时接口整体 503                                                |
