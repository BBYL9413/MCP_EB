"""
MCP EB - CLI 入口
支持命令：server, app, version, test, bridge, copilot-server
"""

import click
import sys
import time
import threading
import webbrowser
import json
from pathlib import Path

MCP_JSON_PATH = Path.home() / "AppData/Roaming/Code/User/mcp.json"
APP_PORT = 7337
SCRIPT_DIR = Path(__file__).parent


def _auto_configure_vscode():
    """自动将 MCP EB Server 写入 VS Code mcp.json"""
    server_entry = {
        "command": sys.executable,
        "args": [str(SCRIPT_DIR / "main.py"), "server"],
        "type": "stdio"
    }

    try:
        if MCP_JSON_PATH.exists():
            with open(MCP_JSON_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {"servers": {}, "inputs": []}

        if "servers" not in config:
            config["servers"] = {}

        config["servers"]["mcp-eb"] = server_entry

        with open(MCP_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent="\t", ensure_ascii=False)

        click.echo(f"✅ 已自动配置 VS Code MCP: {MCP_JSON_PATH}")
    except Exception as e:
        click.echo(f"⚠️  无法自动配置 VS Code MCP: {e}")
        click.echo(f"   请手动将以下内容添加到 mcp.json 的 servers 中:")
        click.echo(f'   "mcp-eb": {json.dumps(server_entry, indent=2)}')


@click.group()
def cli():
    """MCP EB - 智能交互反馈 MCP 服务器（Python 实现版）"""
    pass


@cli.command()
def server():
    """启动 MCP 服务器（stdio 模式，供 AI 助手调用）"""
    from eb_mcp import run_server
    run_server()


@cli.command()
@click.option("--port", default=APP_PORT, show_default=True, help="Web UI 端口号")
@click.option("--no-browser", is_flag=True, default=False, help="不自动打开浏览器")
@click.option("--no-vscode", is_flag=True, default=False, help="不自动配置 VS Code MCP")
def app(port, no_browser, no_vscode):
    """独立运行模式 - 启动 Web UI 并自动配置 VS Code MCP"""
    if not no_vscode:
        _auto_configure_vscode()

    click.echo(f"🚀 启动 MCP EB Web UI → http://localhost:{port}")
    click.echo("   按 Ctrl+C 停止服务")

    if not no_browser:
        def _open_browser():
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{port}")
        threading.Thread(target=_open_browser, daemon=True).start()

    from eb_app import run_app_server
    run_app_server(port=port)


@cli.command()
def version():
    """显示版本信息"""
    click.echo("MCP EB v1.0.2")
    click.echo("Python 重新实现版")
    click.echo(f"Python: {sys.version}")


@cli.command()
def test():
    """测试 MCP EB 各组件是否正常运行"""
    import httpx

    click.echo("🔍 测试 App Server 连接 (http://localhost:7337)...")
    try:
        with httpx.Client(timeout=3.0) as c:
            r = c.get("http://localhost:7337/health")
            if r.status_code == 200:
                click.echo("✅ App Server 运行正常")
            else:
                click.echo(f"❌ App Server 响应异常: {r.status_code}")
    except Exception as e:
        click.echo(f"❌ 无法连接 App Server: {e}")
        click.echo("   提示：请先运行 'python main.py app' 启动 Web UI")

    click.echo("\n🔍 检查 VS Code MCP 配置...")
    if MCP_JSON_PATH.exists():
        with open(MCP_JSON_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        if "mcp-eb" in config.get("servers", {}):
            click.echo("✅ VS Code MCP 已配置 mcp-eb")
        else:
            click.echo("⚠️  VS Code MCP 未配置 mcp-eb，运行 'python main.py app' 自动配置")
    else:
        click.echo(f"⚠️  mcp.json 不存在: {MCP_JSON_PATH}")


@cli.command("copilot-server")
def copilot_server():
    """启动 Copilot CLI MCP 服务器（同 server 命令）"""
    from eb_mcp import run_server
    run_server()


@cli.command()
@click.option("--port", default=8080, show_default=True, help="Bridge API 端口")
def bridge(port):
    """OpenClaw 桥接模式 - 提供 OpenAI 兼容 API（转发到 Copilot）"""
    click.echo(f"⚠️  Bridge 模式（端口: {port}）- 当前版本暂不支持，敬请期待")


if __name__ == "__main__":
    cli()
