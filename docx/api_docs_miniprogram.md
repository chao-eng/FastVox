# FastVox 小程序端接口文档

本文档定义了 FastVox 后台提供给微信小程序调用的核心接口，包括身份认证、声纹管理及流式语音合成。

## 1. 基础信息
- **Base URL**: `https://your-domain.com/api/v1`
- **认证方式**: Bearer Token (JWT)。除登录接口外，所有请求需在 Header 中携带 `Authorization: Bearer <TOKEN>`。

---

## 2. 身份认证接口

### 2.1 微信小程序登录
通过小程序 `wx.login` 获取的 `code` 换取后台 Token。

- **URL**: `/auth/wechat/login`
- **Method**: `POST`
- **Request Body**:
| 参数名 | 类型 | 必选 | 说明 |
| :--- | :--- | :--- | :--- |
| code | string | 是 | 微信登录凭证 |
| appid | string | 否 | 小程序 AppID (若后台配置了多个应用则必传) |

- **Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer"
}
```

### 2.2 Token 有效性检查
用于小程序启动时判断本地存储的 Token 是否仍然有效。

- **URL**: `/auth/wechat/check`
- **Method**: `GET`
- **Header**: `Authorization: Bearer <TOKEN>`
- **Response (Valid)**:
```json
{
  "status": "valid",
  "user_id": "...",
  "nickname": "..."
}
```
- **Response (Invalid)**: HTTP 401 Unauthorized

---

## 3. 声纹管理接口

### 3.1 获取可用声纹列表
获取当前用户可用的声纹列表（包含系统预置和用户上传）。

- **URL**: `/voice/list`
- **Method**: `GET`
- **Response**:
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "播音小姐姐",
    "prompt_text": "欢迎使用 FastVox 语音合成系统。",
    "duration_sec": 5.2,
    "is_public": true,
    "is_owner": false
  }
]
```

---

## 4. 语音合成接口 (核心)

### 4.1 流式合成 (WebSocket)
建立双向连接，实时接收合成的 MP3 音频流。

- **URL**: `/tts/stream`
- **Protocol**: `WebSocket (WSS)`
- **Query Params**:
| 参数名 | 说明 |
| :--- | :--- |
| token | 登录获取的 access_token (必填) |

- **建立连接后的控制消息 (Client -> Server)**:
发送 JSON 格式消息启动合成：
```json
{
  "text": "这是一段需要合成的文本内容。",
  "voice_id": "声纹ID",
  "speed": 1.0
}
```

- **服务器响应格式 (Server -> Client)**:
1. **元数据消息 (JSON)**: 每段音频开始前发送，包含预期时长。
   ```json
   { "type": "metadata", "segment_duration_ms": 1200 }
   ```
2. **音频数据 (Binary)**: MP3 格式的原始字节流。小程序端需累加 Buffer 进行播放。
3. **结束信号**: 发送长度为 0 的 Binary 数据表示合成结束。

---

## 5. 错误代码说明
| HTTP 状态码 | 说明 |
| :--- | :--- |
| 401 | 未授权或 Token 过期 |
| 400 | 参数错误或微信登录失败 |
| 500 | 服务器内部推理错误 |

---
> [!IMPORTANT]
> **开发提示**: 
> 1. 小程序域名需在后台配置合法的 Request/Socket 域名白名单。
> 2. 音频流采用标准 MP3 编码，建议小程序端使用 `InnerAudioContext` 或 `WebAudioContext` 处理缓冲播放。
