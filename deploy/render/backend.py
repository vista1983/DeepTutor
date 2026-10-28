"""Upstream application plus an owner-only MCP adapter."""
from deeptutor.api.main import app
from deploy.render.mcp_bridge import install

install(app)
