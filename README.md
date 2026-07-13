# 墨智（Mozhi）

墨智是一套本地运行的书法学习与创作智能助手。项目围绕书法知识问答、学习推荐、集字创作和文房文化展示构建，前端与后端独立运行。

> **使用说明：** 本项目仅用于课程设计、课题报告与教学展示，**不得用于商业用途**。集字创作所使用的第三方书法字库另有授权要求，详见 [第三方数据来源与授权](docs/第三方数据来源与授权.md)。

> **字库鸣谢：** 集字创作模块直接使用 [neil-zt/calligraphy-community（莒光书法字库）](https://github.com/neil-zt/calligraphy-community) 提供的书法单字数据；该字库 README 注明其更早上游来源为 @zhuojg 发布的 [Chinese Calligraphy Dataset](https://github.com/zhuojg/chinese-calligraphy-dataset)。字库内容及 `index.json` 按 Apache License 2.0 使用，原始 `LICENSE` 与 `README.md` 随仓库保留。

## 当前功能

- RAG 书法问答：本地知识库检索、流式回答、多轮追问、可折叠参考资料；回答生成期间仍可切换查看其他本地历史会话。
- 学习路径推荐：按基础、目标书体、每日练习时间和目标生成建议。
- 文房四宝展馆：基于 Three.js 的湖笔、徽墨、宣纸、端砚交互展示。
- 集字创作：已接入本地字库全部 19 个来源，可按书体筛选、查询真实单字图，自动裁去多余留白、统一视觉字形大小并竖排预览；支持拖动、缩放、旋转单字、恢复自动排版，以及导出 1800 × 2400 PNG。
- 书法图片分析：上传作品后由本地视觉模型分析章法、结构和用笔，并给出练习建议；图片、提问和分析结果会保存到本机对话历史。

## 技术栈

- 后端：Python、FastAPI、LangChain、Chroma
- 本地模型：Ollama（默认 `qwen2.5vl:3b`、`bge-m3`）
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
ollama pull qwen2.5vl:3b
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

两个窗口分别对应两个服务；关闭其中任意窗口，即可停止对应服务。

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

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe -m ruff check backend\app backend\tests
```
