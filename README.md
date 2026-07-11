# 墨智（Mozhi）

墨智是一套本地运行的书法学习与创作智能助手。项目围绕书法知识问答、学习推荐、集字创作和文房文化展示构建，前端与后端独立运行。

## 当前功能

- RAG 书法问答：本地知识库检索、流式回答、多轮追问、可折叠参考资料。
- 学习路径推荐：按基础、目标书体、每日练习时间和目标生成建议。
- 文房四宝展馆：基于 Three.js 的湖笔、徽墨、宣纸、端砚交互展示。
- 集字创作界面：已完成字帖、书体与创作画布交互；真实单字素材库与作品导出仍在开发。
- 书法图片分析：上传作品后由本地视觉模型分析章法、结构和用笔，并给出练习建议。

## 技术栈

- 后端：Python、FastAPI、LangChain、Chroma
- 本地模型：Ollama（默认 `qwen2.5vl:7b`、`bge-m3`）
- 前端：原生 HTML / CSS / JavaScript
- 三维展示：Three.js（本地静态资源，不依赖 CDN）

## 首次安装

1. 安装 Python 3.10 或更高版本，并安装 [Ollama](https://ollama.com/download)。
2. 在项目根目录创建虚拟环境并安装后端依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

3. 下载所需的本地模型：

```powershell
ollama pull qwen2.5vl:7b
ollama pull bge-m3
```

4. 构建知识库索引：

```powershell
.\.venv\Scripts\python.exe backend\app\scripts\init_knowledge_base.py --reset
```

## 启动项目

直接双击根目录的 `start_mozhi.bat`。它会打开前端和后端两个窗口：

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
- 不提交：`data/chroma_db/` 向量索引、`data/mozhi.sqlite3` 本机聊天记录、`uploads/` 用户上传内容、`models/` 中的大模型权重、`.venv/` 和临时日志。
- 克隆项目后，按“首次安装”的第 4 步重新构建向量索引即可。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```
