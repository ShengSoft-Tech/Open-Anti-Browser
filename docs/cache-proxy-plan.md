# HTTP/HTTPS 请求缓存代理 — 最终实现计划

## 已确认决策汇总

| # | 问题 | 决策 |
|---|---|---|
| 1 | 实例模式 | 单进程共享，session API 区分 profile |
| 2 | 缓存范围 | 所有 profile 共享同一缓存 |
| 3 | 代码位置 | 独立 Go repo，与 Python 项目分开 |
| 4 | CA 管理 | Go 全权管理（生成 + Windows 安装） |
| 5 | 统计 API | Python 转发 Go stats，前端只对 Python |
| 6 | WebSocket | 检测 `Upgrade: websocket` 后动态切透传 |
| 7 | 启动时机 | App 启动时拉起 Go 代理进程 |
| 8 | 分发方式 | 方案 Z（开发时运行时下载，发布时 CI 预置） |

## 缓存内部逻辑确认（参照现有 JS 实现）

| 问题 | 决策 | 来源 |
|---|---|---|
| 响应体存储位置 | **S3（body）+ PostgreSQL（元数据）**，沿用 JS 架构 | shengsho-bolide-api |
| Authorization 请求 | 跳过缓存 | 新增 |
| 不缓存的条件 | 非 GET、响应含 Set-Cookie、Content-Type 为 HTML 或 JSON | 新增 + JS 参照 |
| Cache-Control: no-cache | 忽略，照常缓存 | JS 实现相同 |
| TTL 策略 | **永久缓存**，无过期时间，沿用 JS 策略 | shengsho-bolide-api |
| 压缩存储 | 存原始压缩字节，保留 Content-Encoding 头原样转发 | JS 实现相同 |
| 缓存键 | `sha256(METHOD + URL + Accept-Language + Accept-Encoding)` | 调整（不含 UserAgent，支持跨 profile 共享）|

---

## 整体架构

```
┌──────────────────────────────────────────────────────┐
│  Python FastAPI 后端                                   │
│                                                        │
│  App 启动 → 检查 binary → 启动 Go 代理进程             │
│                                                        │
│  start_profile() → POST /sessions → 拿到 proxy port   │
│  stop_profile()  → DELETE /sessions/{port}            │
│                                                        │
│  GET /api/cache/stats   → 转发 Go GET /stats          │
│  DELETE /api/cache      → 转发 Go DELETE /cache       │
└────────────────────┬─────────────────────────────────┘
                     │ subprocess + HTTP
                     ▼
┌──────────────────────────────────────────────────────┐
│  Go MITM 缓存代理进程（单个，App 级别）                │
│                                                        │
│  管理端口（固定，如 19100）                             │
│    POST   /sessions         注册 profile 会话          │
│    DELETE /sessions/{port}  注销会话                   │
│    GET    /stats            缓存统计                   │
│    DELETE /cache            清空缓存（DB + S3）        │
│    GET    /health           健康检查                   │
│                                                        │
│  代理端口（每个 profile 动态分配，如 13001, 13002...） │
│    CONNECT → bypass list? → 透传 or MITM              │
│    MITM → 查 DB → 命中从 S3 取 body 返回              │
│         → 未命中 → 走上游 → 写 shell → 上传 S3        │
│                          → 更新 DB → 返回             │
└──────────┬───────────────────────────────────────────┘
           │                          │
           ▼                          ▼
     PostgreSQL                      S3
    （元数据、URL、               （响应体 body，
      headers、s3_url）             按 hash 路径存储）
```

---

## 缓存判断逻辑（完整流程）

### 请求进来时——是否查缓存

```
方法不是 GET → 直接放行，不查不存
请求头含 Authorization → 直接放行，不查不存
其他 → 查缓存
```

### 响应回来时——是否存缓存

```
响应头含 Set-Cookie            → 不存
Content-Type 是 text/html      → 不存
Content-Type 是 application/json → 不存
Cache-Control 含 no-store      → 不存
Cache-Control 含 private       → 不存
响应体大小 > max_body_mb       → 不存（但正常转发）
其他 → 存缓存（永久，无过期时间）
```

> `no-cache` 不在排除条件内，照常缓存。

### 并发安全——Shell 机制（参照 JS 实现）

同一 URL 同时有多个请求时：

```
请求 A 进来 → 查 DB → 无记录
  → 插入 shell 记录（s3_url = NULL）
  → 走上游获取响应
  → 上传 S3 → 更新 DB（填入 s3_url）
  → 返回给 Chrome A

请求 B 进来（与 A 同时）→ 查 DB → 发现 shell（s3_url = NULL）
  → 等待（轮询，最多 30 秒）
  → shell 完成后读取 S3 → 返回给 Chrome B
```

定时清理：每小时清理创建超过 5 分钟且 s3_url 仍为 NULL 的 shell 记录。

---

## S3 存储设计

### 路径规则

```
{prefix}/{hash[0:2]}/{hash[2:4]}/{hash}.{ext}

示例：
prefix = "proxy-cache"
hash   = "a3f8c2..."
ext    = "js"（由 Content-Type 推导）

S3 key = proxy-cache/a3/f8/a3f8c2....js
```

ext 映射（Content-Type → 扩展名）：

```
text/javascript / application/javascript → js
text/css                                 → css
image/jpeg                               → jpg
image/png                                → png
image/webp                               → webp
image/gif                                → gif
image/svg+xml                            → svg
font/woff2                               → woff2
font/woff                                → woff
application/octet-stream                 → bin
其他                                     → bin
```

### CLI 参数新增

```
--s3-bucket         S3 bucket 名称
--s3-prefix         S3 key 前缀（默认 proxy-cache）
--s3-region         AWS region
--s3-access-key     AWS access key id
--s3-secret-key     AWS secret access key
```

---

## PostgreSQL Schema

```sql
CREATE TABLE IF NOT EXISTS proxy_cache (
    id           BIGSERIAL   PRIMARY KEY,
    cache_hash   CHAR(64)    NOT NULL UNIQUE,   -- sha256 hex
    url          TEXT        NOT NULL,
    method       TEXT        NOT NULL DEFAULT 'GET',
    status_code  INTEGER     NOT NULL,
    headers      JSONB       NOT NULL,          -- 响应头 [[k,v],...]
    content_type VARCHAR(255),
    content_size BIGINT      NOT NULL DEFAULT 0,
    s3_url       TEXT,                          -- NULL = shell 未完成
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_proxy_cache_hash ON proxy_cache (cache_hash);
CREATE INDEX IF NOT EXISTS idx_proxy_cache_url  ON proxy_cache (url);
CREATE INDEX IF NOT EXISTS idx_proxy_cache_shell
    ON proxy_cache (created_at) WHERE s3_url IS NULL;
```

> 无 `expires_at` 字段，永久缓存。

---

## 缓存键

```go
raw := strings.Join([]string{
    strings.ToUpper(method),
    url,
    r.Header.Get("Accept-Language"),
    r.Header.Get("Accept-Encoding"),
}, "\n")
hash := sha256.Sum256([]byte(raw))
cacheKey := hex.EncodeToString(hash[:])
```

---

## Go 项目结构

独立 repo：`open-anti-browser-proxy`

```
open-anti-browser-proxy/
├── main.go
├── proxy/
│   ├── server.go       管理 API（session 注册、stats、flush）
│   ├── session.go      Session（port、upstream config、bypass list）
│   ├── mitm.go         MITM 核心（CONNECT、H1/H2、WSS 检测、缓存逻辑）
│   ├── tunnel.go       透传模式（bypass、WSS bidirectional copy）
│   ├── upstream.go     上游连接（HTTP / HTTPS / SOCKS5）
│   └── bypass.go       内置 + 用户自定义 bypass list
├── cert/
│   ├── ca.go           根 CA 生成、Windows certutil 安装
│   └── host.go         动态签发子证书，内存缓存 SSLContext
├── cache/
│   ├── cache.go        缓存逻辑入口（判断、key 生成、shell 管理）
│   ├── postgres.go     PostgreSQL（元数据 CRUD）
│   ├── s3.go           S3（upload / download / key 生成）
│   └── stats.go        统计查询
├── go.mod
└── go.sum
```

### 关键依赖

```
github.com/jackc/pgx/v5              PostgreSQL 驱动
github.com/aws/aws-sdk-go-v2/...     AWS S3 SDK
golang.org/x/net/http2               HTTP/2 支持
```

---

## 管理 API

### POST /sessions

Request:
```json
{
  "profile_id": "abc123",
  "upstream": {
    "scheme": "socks5",
    "host": "1.2.3.4",
    "port": 1080,
    "username": "user",
    "password": "pass"
  },
  "bypass_domains": ["internal.example.com"]
}
```
Response: `{ "port": 13001 }`

### DELETE /sessions/{port}

### GET /stats

```json
{
  "total_entries": 1024,
  "total_size_bytes": 52428800,
  "hit_count_total": 8839,
  "miss_count_total": 412,
  "hit_rate": 0.955,
  "shell_count": 2,
  "top_entries": [
    {
      "url": "https://cdn.example.com/main.js",
      "hit_count": 304,
      "size_bytes": 102400,
      "cached_at": "2026-06-12T10:00:00Z"
    }
  ]
}
```

### DELETE /cache — 清空全部（DB 记录 + S3 对象）
### GET /health — `{"status":"ok"}`

---

## MITM 核心流程

### HTTPS（CONNECT）

```
Chrome → Go: CONNECT api.example.com:443 HTTP/1.1

1. 域名在 bypass list？ → 是 → 透传模式
2. 否 → MITM：
   Go → Chrome: 200 Connection established
3. TLS 握手（Go 用 api.example.com 伪造证书）
4. Chrome 发 HTTP 请求
5. 检测 Upgrade: websocket → 切透传模式
6. 方法非 GET 或含 Authorization → 直接走上游，不查不存
7. 查 DB（by cache_hash）
   └─ 命中且 s3_url 非 NULL → 从 S3 下载 body → 返回 Chrome
   └─ 命中但 s3_url = NULL（shell）→ 等待完成
   └─ 无记录 → 插 shell → 走上游 → 判断是否存缓存 → 上传 S3 → 更新 DB
```

### HTTP（非 CONNECT）

同上逻辑，无 SSL 层。

---

## Certificate Pinning Bypass List

### 内置（不可删除）

```go
var defaultBypass = []string{
    "google.com", "googleapis.com", "gstatic.com", "googleusercontent.com",
    "googlevideo.com", "youtube.com", "ytimg.com", "gmail.com",
    "doubleclick.net", "google-analytics.com", "ggpht.com", "appspot.com",
    "googlesyndication.com", "googletagmanager.com",
    "apple.com", "icloud.com", "mzstatic.com",
    "twitter.com", "x.com", "t.co",
    "facebook.com", "fbcdn.net", "instagram.com",
}
```

匹配规则：子域名匹配。用户可通过 session 的 `bypass_domains` 追加。

---

## Python 侧改动

### `backend/models.py`

```python
class CacheSettings(ModelBase):
    enabled: bool = False
    postgres_url: str = ""
    s3_bucket: str = ""
    s3_prefix: str = "proxy-cache"
    s3_region: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    max_body_mb: int = 5
    bypass_domains: list[str] = Field(default_factory=list)
```

`AppSettings` 新增：`cache: CacheSettings = Field(default_factory=CacheSettings)`

### `backend/config.py`

```python
CACHE_PROXY_RELEASE_URL = (
    "https://github.com/your-org/open-anti-browser-proxy/releases/download/"
    "v1.0.0/cache-proxy-windows-amd64.exe"
)
CACHE_PROXY_EXECUTABLE  = ASSETS_DIR / "cache-proxy" / "cache-proxy.exe"
CACHE_PROXY_DOWNLOADED  = DOWNLOADS_DIR / "cache-proxy.exe"
CACHE_PROXY_MGMT_PORT   = 19100
```

### `backend/browser_manager.py`

- App 启动时：检测 binary → 拉起 Go 进程
- `start_profile`：`POST /sessions` → 拿 port → 传给 `launch_chrome_profile`
- `stop_profile`：`DELETE /sessions/{port}`
- 监控 Go 进程存活，崩溃时自动重启，最多重试 3 次

### `backend/main.py`

```
GET    /api/cache/stats   → 转发 Go /stats
DELETE /api/cache         → 转发 Go DELETE /cache
GET    /api/cache/health  → 转发 Go /health
```

---

## 分发方案 Z

### 开发时（运行时下载）

```
App 启动 → 查找 binary（CACHE_PROXY_EXECUTABLE → CACHE_PROXY_DOWNLOADED）
  → 找不到 → 前端设置页显示"下载缓存代理"按钮（复用 DownloadRegistry）
```

### 发布时（CI 预置）

```yaml
- name: Download Go proxy binary
  run: |
    curl -L ${{ env.CACHE_PROXY_RELEASE_URL }} \
         -o assets/cache-proxy/cache-proxy.exe

- name: Build
  run: pyinstaller open-anti-browser.spec
```

版本锁定在 `config.py` 的 `CACHE_PROXY_RELEASE_URL`。

---

## 实现顺序

### Go repo

- [ ] **G1** 项目骨架：CLI flags（`--mgmt-port`、`--postgres-url`、`--data-dir`、`--s3-*`）
- [ ] **G2** `cert/`：CA 生成、Windows certutil 安装、子证书签发 + 内存缓存
- [ ] **G3** `cache/postgres.go`：建表、shell insert/update、按 hash 查询
- [ ] **G4** `cache/s3.go`：upload、download、key 路径生成、ext 映射
- [ ] **G5** `cache/cache.go`：判断逻辑、key 生成、shell 等待、定时清理
- [ ] **G6** `proxy/bypass.go`：内置列表 + 子域名匹配
- [ ] **G7** `proxy/tunnel.go`：透传模式
- [ ] **G8** `proxy/upstream.go`：HTTP CONNECT / HTTPS CONNECT / SOCKS5 上游连接
- [ ] **G9** `proxy/mitm.go`：MITM 核心（SSL 终止、H1/H2、WSS 检测、缓存调用）
- [ ] **G10** `proxy/server.go`：管理 API + session 注册/注销
- [ ] **G11** `cache/stats.go`：统计查询
- [ ] **G12** 集成测试 + GitHub Actions release

### Python repo

- [ ] **P1** `models.py`：`CacheSettings`
- [ ] **P2** `config.py`：binary 路径 + release URL
- [ ] **P3** `browser_manager.py`：Go 进程管理 + session 注册/注销
- [ ] **P4** `services/chrome.py`：接收 proxy_port 参数
- [ ] **P5** `main.py`：缓存 API 端点
- [ ] **P6** 前端：缓存配置页（S3 配置 + bypass_domains + 下载按钮）
- [ ] **P7** 前端：缓存统计面板

---

## 风险与限制

| 风险 | 处置 |
|---|---|
| Certificate Pinning | 内置 bypass list |
| WebSocket (WSS) | 检测 Upgrade 头，动态切透传 |
| Go 进程崩溃 | Python 监控，自动重启，最多 3 次；降级为直连代理 |
| CA 安装失败 | 检测返回码，失败时前端提示 |
| S3 不可用 | 降级为无缓存模式，不影响正常浏览 |
| Shell 死锁（上游超时导致 shell 永不完成）| 5 分钟超时 + 定时清理 |
| 跨 profile 缓存污染（同 URL 不同地区内容）| Accept-Language 在 key 里部分规避，v1 接受此限制 |
