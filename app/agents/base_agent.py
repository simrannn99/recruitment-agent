"""
Base agent class with tool-calling capabilities.

This module provides the foundation for all specialized agents,
including tool registration, execution, and error handling.
"""

from typing import List, Dict, Any, Callable, Optional
from abc import ABC, abstractmethod
import time
import logging
from datetime import datetime

from langchain_core.tools import Tool
from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.state import AgentState, AgentExecutionTrace, ToolCall

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the recruitment system.
    
    Each agent:
    - Has access to specific tools
    - Can call LLM for reasoning
    - Tracks execution and tool usage
    - Handles errors gracefully
    """
    
    def __init__(self, llm: BaseChatModel, name: str):
        """
        Initialize the base agent.
        
        Args:
            llm: Language model for reasoning
            name: Agent name for logging and tracing
        """
        self.llm = llm
        self.name = name
        self.tools: Dict[str, Tool] = {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def register_tool(self, tool: Tool):
        """
        Register a tool that this agent can use.
        
        Args:
            tool: LangChain Tool instance
        """
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    def register_tools(self, tools: List[Tool]):
        """
        Register multiple tools at once.
        
        Args:
            tools: List of LangChain Tool instances
        """
        for tool in tools:
            self.register_tool(tool)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def call_tool(self, tool_name: str, **kwargs) -> ToolCall:
        """
        Execute a tool with retry logic.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool
            
        Returns:
            ToolCall object with result or error
        """
        start_time = time.time()
        tool_call = ToolCall(tool_name=tool_name, arguments=kwargs)
        
        try:
            if tool_name not in self.tools:
                raise ValueError(f"Tool '{tool_name}' not registered for agent '{self.name}'")
            
            tool = self.tools[tool_name]
            self.logger.info(f"Calling tool: {tool_name} with args: {kwargs}")
            
            result = tool.invoke(kwargs)
            tool_call.result = result
            
            execution_time = int((time.time() - start_time) * 1000)
            tool_call.execution_time_ms = execution_time
            
            self.logger.info(f"Tool {tool_name} completed in {execution_time}ms")
            
        except Exception as e:
            self.logger.error(f"Tool {tool_name} failed: {str(e)}")
            tool_call.error = str(e)
            tool_call.execution_time_ms = int((time.time() - start_time) * 1000)
            raise
        
        return tool_call
    
    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        """
        Execute the agent's main logic.
        
        This method must be implemented by each specialized agent.
        It should:
        1. Read from the state
        2. Perform reasoning and tool calls
        3. Update the state with results
        4. Add execution trace
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        pass
    
    def create_trace(
        self,
        reasoning: str,
        tools_called: List[ToolCall],
        output: Optional[Dict[str, Any]],
        execution_time_ms: int
    ) -> AgentExecutionTrace:
        """
        Create an execution trace for this agent.
        
        Args:
            reasoning: Agent's reasoning process
            tools_called: List of tool calls made
            output: Agent's output
            execution_time_ms: Total execution time
            
        Returns:
            AgentExecutionTrace object
        """
        return AgentExecutionTrace(
            agent_name=self.name,
            reasoning=reasoning,
            tools_called=tools_called,
            output=output,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
    
    def __call__(self, state: AgentState) -> AgentState:
        """
        Make the agent callable for LangGraph integration.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Agent {self.name} starting execution")
            
            # Update current agent in state
            state.current_agent = self.name
            
            # Execute agent logic
            updated_state = self.execute(state)
            
            execution_time = int((time.time() - start_time) * 1000)
            self.logger.info(f"Agent {self.name} completed in {execution_time}ms")
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed: {str(e)}")
            state.error = f"{self.name}: {str(e)}"
            return state


class ToolRegistry:
    """
    Central registry for all tools available to agents.
    
    This allows tools to be shared across multiple agents
    and provides a single source of truth for tool definitions.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        """Register a tool in the global registry."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool in global registry: {tool.name}")
    
    def register_many(self, tools: List[Tool]):
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def get_all(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())
    
    def get_by_category(self, category: str) -> List[Tool]:
        """
        Get tools by category (if tools have category metadata).
        
        Args:
            category: Tool category (e.g., 'database', 'communication', 'analysis')
            
        Returns:
            List of tools in that category
        """
        return [
            tool for tool in self.tools.values()
            if hasattr(tool, 'metadata') and tool.metadata.get('category') == category
        ]


# Global tool registry instance
global_tool_registry = ToolRegistry()
