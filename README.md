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

- 后端：Python + FastAPI
- 本地大模型：Ollama
- 知识检索：RAG + 向量库
- 图像生成：Stable Diffusion
- 前端：Web 页面
- 三维展示：Three.js

## 当前状态

- [x] 基础 FastAPI 骨架
- [ ] 接入 Ollama 和 RAG
- [ ] 接入 Stable Diffusion
- [ ] 搭建前端页面
- [ ] 增加测试与配置管理

## 开发建议

1. 先跑通一个端到端功能（如知识问答），再扩展其他模块
2. 需要新目录时再创建，避免过早抽象
3. 后端路由、服务、模型等分层在代码量超过 3-5 个文件后再拆分到独立目录
