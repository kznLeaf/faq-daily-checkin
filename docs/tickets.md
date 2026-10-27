自动获取 code → 自动获取 ticket

---

## 方案一

纯 Python 重新实现登录流程。

### 1. OAuth2 凭据获取与维持 (扫码与刷新)

**目标**：获取并长期维护 `access_token` 和 `refresh_token`。

- **Python 实现**：使用 `httpx` 或 `requests` 调用微信开放平台的 OAuth2 接口，生成扫码链接供用户授权，并实现 Token 的自动刷新逻辑。
- **参考 Go 源码**：
  - [`internal/oauth/authorize.go`](https://github.com/525815266/YYB-Go-Enhanced/blob/main/internal/oauth/authorize.go)：查看扫码 URL 的构造规则、授权回调处理以及 Token 刷新机制。

### 2. 获取 `login_buffer` 与签名生成

**目标**：使用 `access_token` 向应用宝接口请求 `login_buffer`，该请求必须携带特定的 MD5 防篡改签名头（`Ual-Access-*`）。

- **Python 实现**：使用内置的 `hashlib.md5` 按照特定规则拼接字符串并生成签名，然后通过 `httpx` 发送 HTTPS 请求。
- **参考 Go 源码**：
  - [`internal/protocol/loginbuffer.go`](https://github.com/525815266/YYB-Go-Enhanced/blob/main/internal/protocol/loginbuffer.go)：重点查看请求参数的构造顺序、签名算法的具体实现，以及 HTTP Header 的精确拼写。

### 3. MMTLS 握手与 `js-login` 取码 (核心难点)

**目标**：建立裸 TCP 连接，完成 MMTLS 握手（ECDHE、ManualAuth、PSK），发送 `js-login` 请求并解析出真实的 `wx.login` code。

- **避免造轮子策略 (Python 侧)**：
  1. **密码学原语**：**绝对不要手写**。使用 Python 的 `cryptography` 库：
     - **ECDH (P-256)**：`cryptography.hazmat.primitives.asymmetric.ec`
     - **AES-192-GCM**：`cryptography.hazmat.primitives.ciphers.aead.AESGCM` (原生完美支持 24 字节/192 位密钥，解决 ESP32 遇到的硬件加速拒绝问题)。
     - **HKDF / SHA-256**：`cryptography.hazmat.primitives.kdf.hkdf` / `hashlib.sha256`
  2. **协议封装**：建议直接复用或参考开源的 Python MMTLS 实现，如 [`ljc545w/pymmtls`](https://github.com/ljc545w/pymmtls)，处理 MMTLS 记录层（WPKG 头、AAD 计算、分片）。
- **参考 Go 源码**：
  - [`internal/protocol/mmtls_crypto.go`](https://github.com/525815266/YYB-Go-Enhanced/blob/main/internal/protocol/mmtls_crypto.go)：查看密钥派生 (HKDF) 流程、AES-GCM 加解密的具体参数和 Nonce 构造规则。
  - [`internal/protocol/mmtls_protocol.go`](https://github.com/525815266/YYB-Go-Enhanced/blob/main/internal/protocol/mmtls_protocol.go)：查看 ClientHello、ServerHello 的解析和状态机流转。
  - [`internal/protocol/shortlink.go`](https://github.com/525815266/YYB-Go-Enhanced/blob/main/internal/protocol/shortlink.go)：查看 0-RTT PSK 短连接建立，以及 `js-login` payload 的 Protobuf/LZ4 封装与解析。

### 4. 业务层换取 SESSION 与 Ticket

**目标**：用 code 换取小程序 SESSION，再换取 43 字符的 `X-Checkin-Ticket`，最后提交打卡。

- **Python 实现**：标准的 HTTP POST 请求。
- **注意**：
  1. **Cookie 污染**：使用 `httpx.Client` 时，如果你在 headers 中手动指定了 `Cookie`，请确保禁用了自动 CookieJar，或每次请求前清空它，防止产生双 `Cookie` 头导致服务端会话解析失败。
  2. **自愈机制**：当接口返回 `46001`/`46002`/`46003` 或 HTTP 403 时，Python 脚本必须清空本地缓存的 Ticket 和 SESSION，重新从阶段二开始执行。

---

## 方案二

混合架构：直接基于已有的实现

1. **协议层 (不造轮子)**：使用 Docker 在本地或服务器部署 [`YYB-Go-Enhanced`](https://github.com/525815266/YYB-Go-Enhanced)。它已经完美、稳定地实现了所有复杂的 MMTLS 握手、加密和取码逻辑。
2. **业务层 (纯 Python)**：Python 脚本仅作为 Client，负责：
   1. 调用 `YYB-Go-Enhanced` 提供的 HTTP API (例如 `POST /wxapp/getCode`)，直接获取现成的 `wx.login` code。
   2. 拿到 code 后，使用 `httpx` 执行上述的 **阶段四**（学校接口的 check-bind、checkin-ticket 和打卡提交）。

如果你因环境限制必须在单一 Python 进程中完成所有网络请求，请严格按照上述“阶段三”的指引，对照 Go 源码并使用 `cryptography` 库进行逐行翻译，并务必先跑通 `pymmtls` 的测试用例以确保加密原语的正确性。
