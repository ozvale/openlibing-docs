# 需求背景

## 业务场景

openlibing-web beta / gamma 两套测试环境的部署访问。测试环境临时切换为直接通过 IP + 端口访问（gamma: `10.0.1.109:8071`，beta: `10.0.15.101:8076`），前端构建产物环境变量与 nginx 反向代理配置需同步调整。

## 问题痛点

1. `.env.beta` / `.env.gamma` 中 `VITE_APP_OPENLIBING_URL` 仍指向域名 `beta/gamma.openlibing.com`，域名在当前测试窗口不可解析/不可用，导致前端拼接的子应用 URL（argus/ai/build 等 Wujie 页面）无法访问。
2. `nginx_beta.conf` / `nginx_gamma.conf` 中各 upstream 块的 `proxy_cookie_domain` 仍按域名改写，与 IP 访问方式不匹配。

## 需求目标

1. `.env.beta`：`VITE_APP_OPENLIBING_URL` 由 `https://beta.openlibing.com` 改为 `https://10.0.15.101:8076`。
2. `.env.gamma`：`VITE_APP_OPENLIBING_URL` 由 `https://gamma.openlibing.com` 改为 `https://10.0.1.109:8071`。
3. `nginx_beta.conf` / `nginx_gamma.conf`：所有 `proxy_cookie_domain` 由 `beta/gamma.openlibing.com .beta/gamma.openlibing.com` 改为对应 `IP:端口 .IP:端口` 形式。

## 验收标准

### 功能验收

1. 通过 `https://10.0.1.109:8071`（gamma）与 `https://10.0.15.101:8076`（beta）可正常访问 openlibing-web 页面。
2. Wujie 子应用（argus / ai / build / ops 等）页面与静态资源经 IP 环境正常加载。
3. 登录与网关（/gateway）链路可用。

### 非功能验收

1. 生产环境（`.env.production`）与 nginx 生产配置不受影响。
2. 仅替换域名/cookie 改写目标，不调整代理路由结构、limit 配置与缓存策略。

## 关联 Issue

[openlibing/openlibing-web#419](https://gitcode.com/openlibing/openlibing-web/issues/419)（beta、gamma 环境域名切换为内网 ip）

## 关联分支

openlibing-web `text-gamma`（commits d89afeecb gamma、5b57d54c2 beta）

## 期望交付时间

2026-11-10
