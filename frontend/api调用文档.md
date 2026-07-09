# 墨智后端接口对接说明

本文档用于指导后端开发同事对接「墨智」前端项目。

## 一、前端项目位置

```text
C:\Users\31752\Desktop\temp\大模型\Mozhi\frontend
```

前端技术栈：

- HTML5
- CSS3
- 原生 JavaScript
- ES Module
- 不使用 Vue / React 等前端框架

当前接口预留文件：

```text
frontend/js/api.js
```

默认后端服务地址：

```text
http://127.0.0.1:8000
```

## 二、需要后端实现的接口

### 1. AI 对话接口

```http
POST /chat
```

请求 JSON：

```json
{
  "message": "请分析我的书法作品，并从章法、结构、用笔三方面给出建议。"
}
```

返回 JSON：

```json
{
  "answer": "你的作品整体章法较稳定，字距略紧。建议先练习横画起收笔，再调整行气节奏..."
}
```

前端调用位置：

```text
frontend/js/api.js -> chatWithAI(message)
```

前端发送按钮会调用该接口。接口暂不可用时，前端会显示本地兜底回复。

接口返回字段必须包含：

```json
{
  "answer": "..."
}
```

### 2. 书法作品分析接口

```http
POST /calligraphy/analyze
```

请求 JSON 示例：

```json
{
  "imageUrl": "作品图片地址或上传后路径",
  "mode": "full",
  "userLevel": "beginner",
  "style": "kaishu"
}
```

返回 JSON 示例：

```json
{
  "score": 92,
  "style": "楷书",
  "summary": "整体结构端正，横竖关系清晰，但部分撇捺舒展不足。",
  "analysis": {
    "composition": "章法较稳，字距略密。",
    "structure": "中宫偏紧，左右舒展不足。",
    "strokes": "起笔较轻，收笔不够明确。"
  },
  "suggestions": [
    "加强横画顿笔练习",
    "临摹颜真卿楷书基本结构",
    "每天练习撇捺舒展 20 分钟"
  ]
}
```

前端调用位置：

```text
frontend/js/api.js -> analyzeCalligraphy(payload)
```

该接口目前为预留接口，后续可接入：

- 图片上传
- 书法图片预览
- AI 评分
- OCR
- OpenCV
- 视觉模型
- AI Agent

## 三、后端技术建议

建议使用：

- Python
- FastAPI
- Uvicorn
- Pydantic
- OpenCV
- Pillow
- OCR
- LLM SDK 或本地大模型服务

建议目录结构：

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── chat.py
│   │   └── calligraphy.py
│   ├── schemas/
│   │   ├── chat.py
│   │   └── calligraphy.py
│   ├── services/
│   │   ├── agent_service.py
│   │   ├── calligraphy_service.py
│   │   └── vision_service.py
│   └── core/
│       └── config.py
└── requirements.txt
```

## 四、CORS 配置要求

由于前端可能运行在以下地址：

```text
http://127.0.0.1:8080
http://localhost:8080
http://127.0.0.1:5173
http://localhost:5173
```

FastAPI 需要开启 CORS：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 五、启动方式

后端启动命令建议：

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端启动命令：

```bash
cd frontend
python -m http.server 8080
```

浏览器访问：

```text
http://127.0.0.1:8080/
```

## 六、对接重点

后端优先保证：

1. `POST /chat` 可用
2. `/chat` 返回字段必须包含 `answer`
3. 开启 CORS
4. 所有接口返回 JSON
5. 后端报错时返回清晰错误信息
6. 图片分析接口可以先返回模拟数据，后续再接入 OCR / OpenCV / Agent

## 七、未来扩展链路

推荐整体调用链路：

```text
Browser
↓
HTML / CSS / JavaScript
↓
FastAPI
↓
Agent Service
↓
LLM / OCR / OpenCV / Vision Model
```

## 八、前端当前读取逻辑

当前前端在 `chat.js` 中调用：

```text
chatWithAI(message)
```

并读取：

```javascript
data.answer
```

因此 `/chat` 接口最小可用返回格式为：

```json
{
  "answer": "墨智已收到你的问题，并完成书法分析。"
}
```
