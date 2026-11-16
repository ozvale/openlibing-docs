# 技术方案

## 方案说明

纯环境配置适配，改动模式统一：`域名 → IP:端口`。

| 配置项                                                     | 原值                              | 新值                       |
| ---------------------------------------------------------- | --------------------------------- | -------------------------- |
| `.env.gamma` VITE_APP_OPENLIBING_URL                       | `https://gamma.openlibing.com`    | `https://10.0.1.109:8071`  |
| `.env.beta` VITE_APP_OPENLIBING_URL                        | `https://beta.openlibing.com`     | `https://10.0.15.101:8076` |
| nginx_*_conf proxy_cookie_domain（gamma 4 处 / beta 5 处） | `gamma/beta.openlibing.com .域名` | `IP:端口 .IP:端口`         |

`proxy_cookie_domain` 替换覆盖的代理块：gateway（网关）与各子应用静态资源/页面代理（argus、ai、build、ops 等）。

## 关键点与已知风险

1. **cookie Domain 携带端口在 RFC 6265 下非法**（2026-11-10 gamma 环境实测结论）：
   - nginx `proxy_cookie_domain 10.0.1.109:8071 .10.0.1.109:8071` 实际不会生效（改写结果含端口会被浏览器整条拒绝）；
   - IP 访问场景下 cookie Domain 属性也不允许是 IP，只能 host-only（即不设置 Domain）。
   - 本分支保留按 IP:端口成对改写的写法，实测以「改写不生效、Set-Cookie 保持上游原样（host-only）」的方式工作。若后续出现 cookie 域问题，正确做法是删除 `proxy_cookie_domain` 行（host-only），而非继续调整其值。
2. 该调整为**测试环境临时方案**：域名恢复后需要回切（或由发布流程统一覆盖），`.env.production` 与生产 nginx 配置不受影响。
3. `.env.*` 属于构建期注入，改后需重新构建部署才生效。

## 影响范围

| 文件                                         | 变更                     |
| -------------------------------------------- | ------------------------ |
| `apps/web-openlibing/.env.gamma`             | 1 行                     |
| `apps/web-openlibing/nginx/nginx_gamma.conf` | 4 处 proxy_cookie_domain |
| `apps/web-openlibing/.env.beta`              | 1 行                     |
| `apps/web-openlibing/nginx/nginx_beta.conf`  | 5 处 proxy_cookie_domain |

## 验证设计

- IP:端口 访问 gamma / beta 环境：页面、静态资源、子应用加载正常。
- 登录态与网关接口 cookie 正常携带（若异常，按「已知风险 1」处理）。
- 回归确认生产配置零改动。
