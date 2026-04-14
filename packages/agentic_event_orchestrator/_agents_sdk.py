"""Re-exports from the installed openai-agents package.

The local `agents/` directory (deprecated) previously conflicted with the
installed `agents` package. Now that the pipeline lives in `pipeline/`,
this module is a simple re-export shim kept for backward compatibility.
"""
from agents import Agent, Runner, function_tool, handoff, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.run import RunConfig

try:
    from agents.extensions.models.litellm_model import LitellmModel
except ImportError:
    LitellmModel = None  # type: ignore

__all__ = [
    "Agent", "Runner", "function_tool", "handoff",
    "AsyncOpenAI", "OpenAIChatCompletionsModel", "RunConfig", "LitellmModel",
]
