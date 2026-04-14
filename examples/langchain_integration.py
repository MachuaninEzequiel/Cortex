"""
examples/langchain_integration.py
----------------------------------
Shows how to wire cortex into a LangChain agent using the
CortexLangChainCallback hook so every agent action is automatically
stored as an episodic memory.

Requirements:
    pip install langchain langchain-openai
"""

# from langchain.agents import AgentExecutor, create_openai_tools_agent
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate

from cortex import AgentMemory
from cortex.hooks import CortexLangChainCallback

memory = AgentMemory()
callback = CortexLangChainCallback(memory)

# Attach callback to your agent executor:
#
#   agent_executor = AgentExecutor(
#       agent=agent,
#       tools=tools,
#       callbacks=[callback],   # <-- cortex hook
#       verbose=True,
#   )
#
# Every tool call and agent finish will be automatically stored
# in episodic memory and searchable via:
#
#   results = memory.retrieve("what did the agent do with auth?")
#   print(results.to_prompt())

print("CortexLangChainCallback ready.")
print("Attach it to your AgentExecutor via the `callbacks` parameter.")
