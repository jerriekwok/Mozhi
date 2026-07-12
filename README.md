# Mozhi

Mozhi 是一个面向书法学习与创作的智能助手平台，结合本地大模型、RAG 知识检索和 AI 图像生成能力，提供知识问答、作品生成、学习推荐和文化展示功能。

## 快速开始

```cmd
.\.venv\Scripts\activate
python -m uvicorn backend.app.main:app --reload
```

访问 http://127.0.0.1:8000/health 验证服务是否运行。

## 项目结构

```
├── backend/          # FastAPI 后端
│   ├── app/main.py   # 应用入口
│   └── requirements.txt
├── frontend/         # 前端页面（待补充）
├── data/             # 知识库与数据资料
├── models/           # 本地模型配置
├── assets/           # 静态资源
├── docs/             # 项目文档
└── .env.example      # 环境变量模板
```

> 当前处于项目初期，目录保持扁平，随着功能增加再逐步拆分模块。

## 技术栈

<<<<<<< Updated upstream
- 后端：Python + FastAPI
- 本地大模型：Ollama
- 知识检索：RAG + 向量库
- 图像生成：Stable Diffusion
- 前端：Web 页面
- 三维展示：Three.js
=======
- 后端：Python、FastAPI、LangChain、Chroma
- 本地模型：Ollama（默认 `qwen2.5:3b`、`bge-m3`）
- 前端：原生 HTML / CSS / JavaScript
- 三维展示：Three.js（本地静态资源，不依赖 CDN）
>>>>>>> Stashed changes

## 当前状态

- [x] 基础 FastAPI 骨架
- [ ] 接入 Ollama 和 RAG
- [ ] 接入 Stable Diffusion
- [ ] 搭建前端页面
- [ ] 增加测试与配置管理

## 开发建议

<<<<<<< Updated upstream
1. 先跑通一个端到端功能（如知识问答），再扩展其他模块
2. 需要新目录时再创建，避免过早抽象
3. 后端路由、服务、模型等分层在代码量超过 3-5 个文件后再拆分到独立目录
=======
3. 下载所需的本地模型：

```powershell
ollama pull qwen2.5:3b
ollama pull bge-m3
```

4. 构建知识库索引：

```powershell
.\.venv\Scripts\python.exe backend\app\scripts\init_knowledge_base.py --reset
```

## 启动项目

直接双击根目录的 `start_mozhi.bat`。它会分别打开两个窗口：

- 前端：`http://127.0.0.1:8080`
- 后端 API 文档：`http://127.0.0.1:8000/docs`

也可以手动启动：

```powershell
# 终端 1：后端
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# 终端 2：前端（项目根目录）
.\.venv\Scripts\python.exe frontend\server.py
```

## 配置

复制 `.env.example` 为 `.env` 后可按需调整 Ollama 地址、模型名和知识库目录。`.env` 不应提交到 GitHub。

## 数据与提交说明

- 应提交：`data/knowledge/`、`data/knowledge_base/` 中的 Markdown 知识资料。
- 不提交：`data/chroma_db/` 向量索引、`uploads/` 用户上传内容、`models/` 中的大模型权重、`.venv/` 和临时日志。
- 克隆项目后，按“首次安装”的第 4 步重新构建向量索引即可。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```
>>>>>>> Stashed changes
