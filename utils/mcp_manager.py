"""
MCP Manager for Strands SDK.

This module provides a manager for MCP servers that can be used by strands SDK agents.
It reads MCP server configurations from:
1. system_mcp_server - Default MCP servers provided by the system
2. public_mcp_server - Public MCP servers that can be used by any agent
3. Database - Custom MCP servers stored in a database (placeholder)
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

from mcp.client.streamable_http import streamablehttp_client
from mcp.client.sse import sse_client
import mcp

logger = logging.getLogger(__name__)

class MCPServer:
    """Class representing an MCP Server configuration."""
    
    def __init__(
        self, 
        name: str, 
        command: str,
        args: List[str],
        env: Dict[str, str] = None,
        auto_approve: List[str] = None,
        disabled: bool = False,
        url: Optional[str] = None,
    ):
        """
        Initialize an MCP Server.
        
        Args:
            name: Name of the MCP server
            command: Command to start the MCP server
            args: Arguments to pass to the command
            env: Environment variables to set when starting the server
            auto_approve: List of commands to auto-approve
            disabled: Whether the server is disabled
            url: Optional URL for the server (for remote servers)
        """
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.auto_approve = auto_approve or []
        self.disabled = disabled
        self.url = url

    def to_dict(self) -> Dict[str, Any]:
        """Convert the MCP server to a dictionary."""
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "env": self.env,
            "autoApprove": self.auto_approve,
            "disabled": self.disabled,
            "url": self.url,
        }
    
    @classmethod
    def from_dict(cls, name: str, config: Dict[str, Any]) -> "MCPServer":
        """
        Create an MCP server from a dictionary.
        
        Args:
            name: Name of the MCP server
            config: Dictionary containing the configuration
            
        Returns:
            MCPServer instance
        """
        return cls(
            name=name,
            command=config.get("command", ""),
            args=config.get("args", []),
            env=config.get("env", {}),
            auto_approve=config.get("autoApprove", []),
            disabled=config.get("disabled", False),
            url=config.get("url"),
        )

    def create_mcp_client(self, transport_type: str = "streamable_http"):
        """
        Create direct MCP client connection for this server.
        
        Unlike the previous implementation, this returns the raw client connection
        that can be used in an async context manager, not wrapped in an MCPClient.
        
        Args:
            transport_type: Type of transport to use (streamable_http, sse, stdio)
            
        Returns:
            The direct client connection that can be used with async with
        """
        if transport_type == "streamable_http":
            if self.url:
                return streamablehttp_client(self.url)
            else:
                # Default to localhost if no URL is provided
                return streamablehttp_client("http://localhost:8000/mcp")
        elif transport_type == "sse":
            if self.url:
                return sse_client(self.url)
            else:
                return sse_client("http://localhost:8000/sse")
        elif transport_type == "stdio":
            return mcp.stdio_client(
                mcp.StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    env=self.env
                )
            )
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")


class MCPManager:
    """
    Manager for MCP servers.
    
    This class reads MCP server configurations from different sources and creates
    MCPServer objects that can be used by strands SDK agents.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the MCP Manager.
        
        Args:
            base_path: Base path to look for MCP server configurations.
                      If None, use the current working directory.
        """
        self.base_path = Path(base_path) if base_path else Path(os.getcwd())
        self.system_servers: Dict[str, MCPServer] = {}
        self.public_servers: Dict[str, MCPServer] = {}
        self.db_servers: Dict[str, MCPServer] = {}
        
        # Load MCP servers from different sources
        self._load_system_servers()
        self._load_public_servers()
        # Database loading is a placeholder
        
    def _load_system_servers(self) -> None:
        """Load MCP servers from system_mcp_server directory."""
        system_path = self.base_path / "mcp" / "system_mcp_server"
        if not system_path.exists():
            logger.warning(f"System MCP server path does not exist: {system_path}")
            return
            
        for file_path in system_path.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    config = json.load(f)
                
                if "mcpServers" in config:
                    for name, server_config in config["mcpServers"].items():
                        server = MCPServer.from_dict(name, server_config)
                        self.system_servers[name] = server
                        logger.debug(f"Loaded system MCP server: {name}")
            except Exception as e:
                logger.error(f"Error loading system MCP server from {file_path}: {e}")
    
    def _load_public_servers(self) -> None:
        """Load MCP servers from public_mcp_server directory."""
        public_path = self.base_path / "mcp" / "public_mcp_server"
        if not public_path.exists():
            logger.warning(f"Public MCP server path does not exist: {public_path}")
            return
            
        for file_path in public_path.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    config = json.load(f)
                
                if "mcpServers" in config:
                    for name, server_config in config["mcpServers"].items():
                        server = MCPServer.from_dict(name, server_config)
                        self.public_servers[name] = server
                        logger.debug(f"Loaded public MCP server: {name}")
            except Exception as e:
                logger.error(f"Error loading public MCP server from {file_path}: {e}")
    
    def load_db_servers(self, db_connector: Any = None) -> None:
        """
        Load MCP servers from database.
        
        Args:
            db_connector: Database connector to use for loading servers
        """
        # This is a placeholder for database loading
        # In a real implementation, this would query the database for MCP servers
        # and create MCPServer objects from the results
        logger.info("Database MCP server loading is not implemented")
    
    def get_server(self, name: str) -> Optional[MCPServer]:
        """
        Get an MCP server by name.
        
        Args:
            name: Name of the server to get
            
        Returns:
            MCPServer instance or None if not found
        """
        # Check system servers first, then public, then database
        if name in self.system_servers:
            return self.system_servers[name]
        elif name in self.public_servers:
            return self.public_servers[name]
        elif name in self.db_servers:
            return self.db_servers[name]
        else:
            return None
    
    def list_servers(self) -> Dict[str, MCPServer]:
        """
        List all available MCP servers.
        
        Returns:
            Dictionary of server names to MCPServer objects
        """
        # Combine all servers into one dictionary
        # Public servers override system servers, and DB servers override both
        servers = {}
        servers.update(self.system_servers)
        servers.update(self.public_servers)
        servers.update(self.db_servers)
        return servers