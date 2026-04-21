"""
MCP EB - MCP Server
实现 eb_back 和 eb_check 两个 MCP 工具。
通过 HTTP 与 eb_app.py (Web UI 服务器) 通信。
"""

import time
import httpx
import subprocess
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

APP_PORT = 7337
APP_URL = f"http://localhost:{APP_PORT}"
POLL_INTERVAL = 0.5  # 轮询间隔（秒）

mcp = FastMCP("mcp-eb")


def _ensure_app_running() -> bool:
    """检查 App Server 是否运行，如果没有则自动启动"""
    try:
        with httpx.Client(timeout=1.5) as c:
            r = c.get(f"{APP_URL}/health")
            if r.status_code == 200:
                return True
    except Exception:
        pass

    script_dir = Path(__file__).parent
    app_script = str(script_dir / "eb_app.py")

    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    subprocess.Popen(
        [sys.executable, app_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **kwargs
    )

    for _ in range(12):
        time.sleep(0.5)
        try:
            with httpx.Client(timeout=1.0) as c:
                r = c.get(f"{APP_URL}/health")
                if r.status_code == 200:
                    return True
        except Exception:
            pass

    return False


@mcp.tool(
    description=(
        "Only user channel. Work -> eb_back(summary) -> read feedback -> repeat. "
        "User cannot see plain replies."
    )
)
def eb_back(
    summary: str = "我已完成了您请求的任务。",
    project_directory: str = ".",
    timeout: int = 0,
) -> str:
    """
    Only user channel. Work -> eb_back(summary) -> read feedback -> repeat.
    User cannot see plain replies. timeout=172800.
    Sub-agents must not call it.
    If any tool call is skipped/cancelled by the user, immediately call eb_back with progress.
    Call eb_check after EVERY step to check for user interrupt signals.

    CRITICAL: When eb_check returns INTERRUPT, immediately call eb_back with a progress summary.
    """
    _ensure_app_running()

    effective_timeout = timeout if timeout > 0 else 172800

    try:
        with httpx.Client(timeout=10.0) as c:
            resp = c.post(
                f"{APP_URL}/api/message",
                json={"summary": summary, "project_directory": project_directory},
            )
            message_id = resp.json()["message_id"]
    except Exception as e:
        return f"ERROR: 无法连接到 MCP EB App Server ({e})。请先运行 'python main.py app'"

    deadline = time.time() + effective_timeout
    while time.time() < deadline:
        try:
            with httpx.Client(timeout=5.0) as c:
                r = c.get(f"{APP_URL}/api/poll", params={"message_id": message_id})
                data = r.json()

                if data["type"] == "response":
                    user_input = data["content"]
                    return (
                        f"=== 用户反馈 ===\n{user_input}\n---\n"
                        "⚠️ After work, call eb_back(summary). User cannot see plain replies. "
                        "Sub-agents must not call it. timeout=172800. "
                        "If a tool is skipped, call eb_back immediately. "
                        "Call eb_check after every step. "
                        "If INTERRUPT → immediately eb_back with progress."
                    )

                elif data["type"] == "interrupt":
                    return (
                        "=== 用户反馈 ===\nINTERRUPT\n---\n"
                        "🚨 CRITICAL: User requested INTERRUPT. "
                        "Immediately call eb_back with a progress summary. "
                        "Do NOT continue working."
                    )

        except Exception:
            pass

        time.sleep(POLL_INTERVAL)

    return "TIMEOUT: 等待用户回复超时，未收到反馈。"


@mcp.tool(
    description=(
        "Check for user interrupt signal. Returns 'continue' or 'INTERRUPT'. "
        "Non-blocking, call after every step."
    )
)
def eb_check() -> str:
    """
    Check for user interrupt signal. Returns 'continue' or 'INTERRUPT'.
    Non-blocking, call after EVERY step.
    If INTERRUPT is returned, immediately call eb_back with progress summary.
    """
    try:
        with httpx.Client(timeout=2.0) as c:
            r = c.get(f"{APP_URL}/api/interrupt_status")
            return r.json().get("status", "continue")
    except Exception:
        return "continue"


def run_server():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_server()