import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any

from app.core.circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Raised when MCP connection fails."""
    pass


# Connection pool: URL -> MCPClient instance
_connection_pool: dict[str, "MCPClient"] = {}
_pool_lock = asyncio.Lock()
_mcp_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)


@dataclass
class MCPClient:
    """Client for connecting to Dynatrace MCP servers (SaaS or Managed).

    Supports connection pooling, reconnection, and concurrent access protection.
    """
    url: str
    token: str
    env_type: str  # "saas" or "managed"
    timeout: int = 30
    max_retries: int = 3
    _session: Any = field(default=None, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def connect(self) -> bool:
        """Establish connection to MCP server with retry logic."""
        async with self._lock:
            for attempt in range(self.max_retries):
                try:
                    await self._connect_mcp()
                    logger.info(f"MCP connected to {self.url}")
                    return True
                except Exception as e:
                    logger.warning(f"MCP connect attempt {attempt+1}/{self.max_retries} failed: {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
            raise MCPConnectionError(
                f"Failed to connect to MCP at {self.url} after {self.max_retries} attempts"
            )

    async def _connect_mcp(self) -> dict:
        """Internal method to connect to MCP server via stdio."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        try:
            package = "dynatrace-mcp" if self.env_type == "saas" else "dynatrace-managed-mcp"
            use_npx = os.getenv("MCP_USE_NPX", "false").lower() == "true"
            if use_npx:
                command = "npx"
                args = [f"@dynatrace-oss/{package}"]
            else:
                command = os.getenv("MCP_COMMAND", package)
                args = []

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env={"DT_URL": self.url, "DT_TOKEN": self.token},
            )

            # Use context manager to properly manage stdio streams lifecycle
            stdio_cm = stdio_client(server_params)
            read, write = await stdio_cm.__aenter__()
            session = ClientSession(read, write)
            await session.initialize()
            self._session = session
            self._stdio_cm = stdio_cm  # Store for proper cleanup
            return {"status": "connected"}
        except ImportError as e:
            raise MCPConnectionError(f"MCP package not available: {e}")
        except Exception as e:
            raise MCPConnectionError(f"Failed to establish MCP connection: {e}")

    async def call_tool(self, tool_name: str, arguments: dict, timeout: float | None = None) -> Any:
        """Call an MCP tool and return its result.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments to pass to the tool.
            timeout: Optional timeout in seconds for the tool call.
        """
        if not self._session:
            raise MCPConnectionError("Not connected. Call connect() first.")

        async def _call():
            tool_coro = self._session.call_tool(tool_name, arguments)
            if timeout:
                return await asyncio.wait_for(tool_coro, timeout=timeout)
            return await tool_coro

        try:
            result = await _mcp_circuit_breaker.execute(_call())
        except CircuitOpenError as e:
            raise MCPConnectionError(str(e)) from e
        return result.content

    async def list_tools(self) -> list[dict]:
        """List all available tools from the MCP server."""
        if not self._session:
            raise MCPConnectionError("Not connected")
        result = await self._session.list_tools()
        return [{"name": t.name, "description": t.description} for t in result.tools]

    async def disconnect(self) -> None:
        """Close the MCP connection and cleanup resources."""
        async with self._lock:
            self._session = None
            # Properly close the stdio context manager
            if hasattr(self, '_stdio_cm') and self._stdio_cm is not None:
                await self._stdio_cm.__aexit__(None, None, None)
                self._stdio_cm = None
            # Remove from pool if present
            async with _pool_lock:
                if self.url in _connection_pool:
                    del _connection_pool[self.url]

    def is_connected(self) -> bool:
        """Check if the client is currently connected.

        Returns:
            True if _session is not None, False otherwise.
        """
        return self._session is not None

    async def reconnect(self) -> bool:
        """Reconnect to the MCP server.

        Disconnects first if already connected, then establishes a new connection.

        Returns:
            True if reconnection successful.
        """
        await self.disconnect()
        return await self.connect()

    @classmethod
    async def get_from_pool(cls, url: str, token: str, env_type: str) -> "MCPClient":
        """Get or create an MCPClient from the connection pool.

        Args:
            url: The MCP server URL.
            token: Authentication token.
            env_type: "saas" or "managed".

        Returns:
            MCPClient instance for the given URL (reused if already in pool).
        """
        async with _pool_lock:
            if url in _connection_pool:
                client = _connection_pool[url]
                logger.debug(f"Reusing pooled MCP connection for {url}")
                return client

            client = cls(url=url, token=token, env_type=env_type)
            _connection_pool[url] = client
            logger.debug(f"Created new MCP connection for {url}")
            return client
