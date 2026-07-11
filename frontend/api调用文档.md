# 墨智前后端接口说明

前端服务地址：`http://127.0.0.1:8080`  
后端服务地址：`http://127.0.0.1:8000`

后端启动后，可在 `http://127.0.0.1:8000/docs` 查看并测试接口。

## 1. RAG 书法问答

### 流式问答（前端默认使用）

```http
POST /api/chat/stream
Content-Type: application/json
```

```json
{
  "question": "颜真卿的书法有什么特点？",
  "session_id": "可选的会话 ID"
}
```

响应为 Server-Sent Events，依次包含：

- `sources`：检索到的参考资料
- `chunk`：逐段输出的回答文本
- `done`：包含最终 `session_id`

### 完整问答

```http
POST /api/chat
Content-Type: application/json
```

```json
{
  "question": "颜真卿的书法有什么特点？",
  "session_id": "可选的会话 ID"
}
```

```json
{
  "answer": "……",
  "sources": [
    {
      "title": "颜真卿",
      "content": "……",
      "file": "06_书家_颜真卿.md"
    }
  ],
  "session_id": "……"
}
```

> `POST /chat` 仍保留为兼容接口，使用字段 `message`，仅返回 `answer`。新功能请使用 `/api/chat`。

## 2. 学习路径推荐

```http
POST /api/learning/plan
Content-Type: application/json
```

```json
{
  "level": "beginner",
  "style": "kaishu",
  "daily_minutes": 30,
  "goal": "想临好颜体，提升结构和用笔稳定性"
}
```

- `level`：`beginner`、`intermediate`、`advanced`
- `style`：`kaishu`、`xingshu`、`caoshu`、`lishu`、`zhuanshu`
- `daily_minutes`：10 至 180

响应包含 `plan` 和 `sources`，资料来源结构与问答接口一致。

## 3. 书法图片上传与分析

### 上传图片

```http
POST /uploads/calligraphy
Content-Type: multipart/form-data
```

- `file`：JPEG、PNG 或 WebP 图片，最大 8 MB。
- `purpose`：固定为 `analysis`，可省略。

### 分析图片

```http
POST /calligraphy/analyze
Content-Type: application/json
```

```json
{
  "uploadId": "上传接口返回的 ID",
  "imageUrl": "/uploads/calligraphy/……jpg",
  "style": "kaishu",
  "question": "请重点分析结体和用笔"
}
```

`uploadId` 与 `imageUrl` 至少提供一个。该接口目前返回稳定的演示分析结果，等待后续接入视觉评分模型。

## 4. 健康检查

```http
GET /health
```

```json
{
  "status": "ok"
}
