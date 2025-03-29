from typing import Literal, cast
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
from langchain.schema.runnable.config import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import MessagesState

import chainlit as cl


@tool
def get_weather(city: Literal["nyc", "sf"]):
    """Use this to get weather information."""
    if city == "nyc":
        return "It might be cloudy in nyc"
    elif city == "sf":
        return {"weather": "It's always sunny in sf"}
    else:
        raise AssertionError("Unknown city")


tools = [get_weather]
model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
final_model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

model = model.bind_tools(tools)
final_model = final_model.with_config(tags=["final_node"])
tool_node = ToolNode(tools=tools)


def should_continue(state: MessagesState) -> Literal["tools", "final"]:
    messages = state["messages"]
    last_message = messages[-1]
    # If the LLM makes a tool call, then we route to the "tools" node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, we stop (reply to the user)
    return "final"


def call_model(state: MessagesState):
    messages = state["messages"]
    response = model.invoke(messages)
    # We return a list, because this will get added to the existing list
    return {"messages": [response]}


def call_final_model(state: MessagesState):
    messages = state["messages"]
    last_ai_message = messages[-1]
    response = final_model.invoke(
        [
            SystemMessage("Rewrite this in the voice of Al Roker"),
            HumanMessage(last_ai_message.content),
        ]
    )
    # overwrite the last AI message from the agent
    response.id = last_ai_message.id
    return {"messages": [response]}


builder = StateGraph(MessagesState)

builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)
# add a separate final node
builder.add_node("final", call_final_model)

builder.add_edge(START, "agent")
builder.add_conditional_edges(
    "agent",
    should_continue,
)

builder.add_edge("tools", "agent")
builder.add_edge("final", END)

graph = builder.compile()


@cl.on_message
async def on_message(msg: cl.Message):
    config = {"configurable": {"thread_id": cl.context.session.id}}
    active_tool_steps = {}  # tool id로 저장해서 cl.Step에서 추적 가능하도록 하는 dict
    final_answer = cl.Message(content="")

    for typ, chunk in graph.stream(
        {"messages": [HumanMessage(content=msg.content)]},
        stream_mode=["messages", "values"],
        config=RunnableConfig(**config),
    ):
        if typ == "values":
            last_message = chunk["messages"][-1]

            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                for call in last_message.tool_calls:
                    tool_id = call.get("id")
                    async with cl.Step(name=call.get("name"), type="tool") as step:
                        step.input = call.get("args", {})
                        await step.send()
                    active_tool_steps[tool_id] = step

            elif isinstance(last_message, ToolMessage):
                # Type casting
                step = cast(cl.Step, active_tool_steps.get(last_message.tool_call_id))
                async with step:
                    print(last_message)
                    step.output = str(last_message.content)
                    await step.update()

        if typ == "messages":
            msg_chunk, metadata = chunk
            if metadata.get("langgraph_node") == "final":
                await final_answer.stream_token(msg_chunk.content)

    await final_answer.send()
    await cl.Message(content="Done!").send()
