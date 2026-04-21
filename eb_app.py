"""
MCP EB - Web UI Server
负责管理消息队列，提供 Web UI 供用户查看 AI 摘要并回复。
MCP Server 通过 HTTP 与本服务通信。
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import time
from pathlib import Path
import uvicorn

app = FastAPI(title="MCP EB")
HISTORY_LIMIT = 100


class AppState:
    def __init__(self):
        self.pending_id: int = 0
        self.pending_summary: str | None = None
        self.pending_project: str = "."
        self.response: str | None = None
        self.response_id: int = -1
        self.interrupt: bool = False
        self.history: list = []

    def add_history(self, item: dict):
        self.history.append(item)
        if len(self.history) > HISTORY_LIMIT:
            self.history = self.history[-HISTORY_LIMIT:]

    def clear_history(self):
        self.history.clear()


state = AppState()


class MessageRequest(BaseModel):
    summary: str
    project_directory: str = "."


class ResponseRequest(BaseModel):
    response: str
    message_id: int


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/message")
async def post_message(req: MessageRequest):
    """AI 调用 eb_back 时，将摘要 POST 到此端点"""
    state.pending_id += 1
    state.pending_summary = req.summary
    state.pending_project = req.project_directory
    state.response = None
    state.response_id = -1
    state.interrupt = False
    state.add_history({
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
    state.add_history({
        "type": "user",
        "content": req.response,
        "timestamp": time.time()
    })
    return {"status": "ok"}


@app.post("/api/clear-history")
async def clear_history():
    """清空历史消息，保留当前会话状态"""
    state.clear_history()
    return {"status": "ok", "history_size": 0, "history_limit": HISTORY_LIMIT}


@app.post("/api/interrupt")
async def post_interrupt():
    """用户点击 INTERRUPT 按钮"""
    state.interrupt = True
    return {"status": "ok"}


@app.get("/api/interrupt_status")
async def interrupt_status():
    """eb_check 调用此端点"""
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
async def get_history(limit: int | None = None):
    history = state.history
    if limit is not None and limit > 0:
        history = history[-limit:]
    return {"history": history, "history_limit": HISTORY_LIMIT}


static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)


@app.get("/")
async def index():
    html_file = static_dir / "index.html"
    if html_file.exists():
        return HTMLResponse(html_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>MCP EB - Web UI 文件缺失，请检查 static/index.html</h1>")


def run_app_server(port: int = 7337):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    run_app_server()