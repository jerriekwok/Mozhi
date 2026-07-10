# 墨智后端接口对接说明

本文档用于指导后端同学对接「墨智」前端项目。

## 一、当前前端入口

前端项目位置：

```text
C:\Users\31752\Desktop\temp\大模型\Mozhi\frontend
```

当前实际页面入口：

```text
frontend/index.html
frontend/js/main.js
frontend/js/api.js
```

注意：`frontend/js/chat.js` 是旧预留文件，目前没有被 `index.html` 引用，不作为当前页面入口。

默认后端服务地址：

```text
http://127.0.0.1:8000
```

## 二、AI 书法问答接口

```http
POST /chat
Content-Type: application/json
```

请求 JSON：

```json
{
  "message": "请分析颜真卿楷书的临帖重点。"
}
```

返回 JSON：

```json
{
  "answer": "简要判断：颜真卿楷书适合用来训练中锋、骨力和结构开张..."
}
```

前端调用位置：

```text
frontend/js/api.js -> chatWithAI(message)
frontend/js/main.js -> 提交问答表单后读取 data.answer
```

兼容要求：

- 请求字段保持 `message`。
- 返回字段必须包含 `answer`。
- 前端目前只读取 `data.answer`，不要改成其他字段名。

回答质量建议：

- 全程中文，语气亲切但专业。
- 默认结构建议为：简要判断、具体分析、练习建议。
- 作品点评类问题优先覆盖：章法、结构、用笔、改进练习。
- 临帖或技法类问题优先覆盖：观察方法、常见错误、当天可执行练习。
- 书家、碑帖或书体知识类问题优先覆盖：风格特征、学习价值、临摹要点。

## 三、书法图片上传接口

```http
POST /uploads/calligraphy
Content-Type: multipart/form-data
```

表单字段：

```text
file: 必填，图片文件
purpose: 可选，默认 analysis
```

支持图片类型：

```text
image/jpeg
image/png
image/webp
```

建议大小限制：

```text
最大 8MB
```

返回 JSON：

```json
{
  "uploadId": "calligraphy_20260710_xxxxx",
  "filename": "practice.jpg",
  "contentType": "image/jpeg",
  "size": 245678,
  "imageUrl": "/uploads/calligraphy/calligraphy_20260710_xxxxx.jpg"
}
```

前端调用位置：

```text
frontend/js/api.js -> uploadCalligraphyImage(file, options)
```

前端调用示例：

```javascript
const result = await uploadCalligraphyImage(file, { purpose: "analysis" });
console.log(result.uploadId, result.imageUrl);
```

重要说明：

- 前端上传时使用 `FormData`。
- 前端不会手动设置 `Content-Type`，浏览器会自动补 multipart boundary。
- `uploadId` 后续传给 `/calligraphy/analyze` 使用。
- 当前仅支持书法图片上传，不支持 PDF / Word / TXT / Markdown 等普通文件上传。
- 当前没有通用文件上传接口，也没有删除文件接口。

## 四、书法作品分析接口

```http
POST /calligraphy/analyze
Content-Type: application/json
```

请求 JSON：

```json
{
  "uploadId": "calligraphy_20260710_xxxxx",
  "imageUrl": "/uploads/calligraphy/calligraphy_20260710_xxxxx.jpg",
  "mode": "full",
  "userLevel": "beginner",
  "style": "kaishu",
  "question": "请重点分析结构和用笔"
}
```

字段说明：

```text
uploadId: 上传接口返回的图片 ID，uploadId 和 imageUrl 至少提供一个
imageUrl: 图片地址，uploadId 和 imageUrl 至少提供一个
mode: 分析模式，可选 full / quick，默认 full
userLevel: 用户水平，可选 beginner / intermediate / advanced，默认 beginner
style: 书体或风格，可选 kaishu / xingshu / caoshu / lishu / zhuanshu
question: 用户希望重点分析的问题
```

返回 JSON：

```json
{
  "score": 86,
  "style": "楷书",
  "summary": "整体结构较稳，部分横画起收笔还可以更明确。",
  "analysis": {
    "composition": "章法基本整齐，字距略紧。",
    "structure": "重心较稳定，个别字中宫偏紧。",
    "strokes": "起笔较轻，转折处顿挫不够清楚。"
  },
  "suggestions": [
    "先做横画起笔和收笔的慢速练习",
    "临摹颜体时重点观察横细竖粗和转折力度",
    "每次练习后圈出三个结构最不稳的字单独复写"
  ]
}
```

前端调用位置：

```text
frontend/js/api.js -> analyzeCalligraphy(payload)
```

当前实现策略：

- 可以先返回稳定模拟分析结果。
- 后续再接 OCR / OpenCV / 视觉模型 / Agent。
- 如果后端接入真实视觉模型，保持返回字段不变，前端即可兼容。

## 五、错误码建议

```text
400: 请求参数缺失或 purpose 不合法
413: 上传图片超过大小限制
415: 上传内容不是支持的图片类型
500: 后端服务异常
```

错误返回建议：

```json
{
  "detail": "uploadId or imageUrl is required"
}
```

## 六、CORS 配置要求

前端可能运行在以下地址：

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

## 七、启动方式

后端启动命令：

```bash
cd backend
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

## 八、对接优先级

1. 保证 `POST /chat` 可用，返回 `answer`。
2. 保证 `POST /uploads/calligraphy` 可上传图片并返回 `uploadId`。
3. 保证 `POST /calligraphy/analyze` 可接收 `uploadId` 或 `imageUrl`。
4. 所有接口返回 JSON。
5. 后端报错时返回清晰 `detail`。
