from fastapi import FastAPI#导入FastAPI工具


app = FastAPI(title="Mozhi API", version="0.1.0")#创建应用


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Mozhi backend is running"}


#用于检测服务器是否正常
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

