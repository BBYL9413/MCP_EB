"""
Jerry EB - Web UI Server
负责管理消息队列，提供 Web UI 供用户查看 AI 摘要并回复。
MCP Server 通过 HTTP 与本服务通信。
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time
from pathlib import Path
import uvicorn

app = FastAPI(title="MCP Jerry EB")

# ==================== 共享状态 ====================
class AppState:
    def __init__(self):
        self.pending_id: int = 0          # 当前消息 ID
        self.pending_summary: str | None = None  # AI 发来的摘要
        self.pending_project: str = "."   # 项目目录
        self.response: str | None = None  # 用户回复
        self.response_id: int = -1        # 已回复的消息 ID
        self.interrupt: bool = False      # 中断信号
        self.history: list = []           # 对话历史

state = AppState()

# ==================== 请求模型 ====================
class MessageRequest(BaseModel):
    summary: str
    project_directory: str = "."

class ResponseRequest(BaseModel):
    response: str
    message_id: int

# ==================== API 端点 ====================
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/api/message")
async def post_message(req: MessageRequest):
    """AI 调用 jerry_back 时，将摘要 POST 到此端点"""
    state.pending_id += 1
    state.pending_summary = req.summary
    state.pending_project = req.project_directory
    state.response = None
    state.response_id = -1
    state.interrupt = False
    state.history.append({
        "id": state.pending_id,
        "type": "ai",
        "content": req.summary,
        "project_directory": req.project_directory,
        "timestamp": time.time()
    })
    return {"message_id": state.pending_id}

@app.get("/api/poll")
async def poll_response(message_id: int):
    """MCP Server 轮询此端点等待用户回复"""
    if state.response_id == message_id and state.response is not None:
        return {"type": "response", "content": state.response}
    if state.interrupt:
        return {"type": "interrupt"}
    return {"type": "waiting"}

@app.post("/api/response")
async def post_response(req: ResponseRequest):
    """用户在 Web UI 提交回复"""
    state.response = req.response
    state.response_id = req.message_id
    state.history.append({
        "type": "user",
        "content": req.response,
        "timestamp": time.time()
    })
    return {"status": "ok"}

@app.post("/api/interrupt")
async def post_interrupt():
    """用户点击 INTERRUPT 按钮"""
    state.interrupt = True
    return {"status": "ok"}

@app.get("/api/interrupt_status")
async def interrupt_status():
    """jerry_check 调用此端点"""
    if state.interrupt:
        return {"status": "INTERRUPT"}
    return {"status": "continue"}

@app.get("/api/current")
async def get_current():
    """Web UI 轮询最新状态"""
    return {
        "pending_id": state.pending_id,
        "pending_summary": state.pending_summary,
        "pending_project": state.pending_project,
        "response_id": state.response_id,
        "interrupt": state.interrupt,
    }

@app.get("/api/history")
async def get_history():
    return {"history": state.history}

# ==================== 静态文件 ====================
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

@app.get("/")
async def index():
    html_file = static_dir / "index.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Jerry EB - Web UI 文件缺失，请检查 static/index.html</h1>")

def run_app_server(port: int = 7337):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

if __name__ == "__main__":
    run_app_server()
