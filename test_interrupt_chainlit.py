import chainlit as cl
from typing import cast

from langgraph.graph import MessagesState, StateGraph, START
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

from langchain_core.messages import HumanMessage, AIMessage


def edit_this(state: MessagesState):
    approved = interrupt("Next step? Answer in Yes or No")

    if approved.lower() == "yes":
        return {"messages": AIMessage(content="Approved!")}
    else:
        return {"messages": AIMessage(content="Rejected!")}


@cl.on_chat_start
async def on_chat_start():
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node("edit", edit_this)
    graph_builder.add_edge(START, "edit")

    checkpointer = MemorySaver()
    graph = graph_builder.compile(checkpointer=checkpointer)

    cl.user_session.set("graph", graph)
    cl.user_session.set("interrupt_node_name", "edit")


@cl.on_message
async def on_message(message: cl.Message):
    thread_config = {"configurable": {"thread_id": 1}}
    graph = cast(CompiledStateGraph, cl.user_session.get("graph"))

    # where graph starts
    for chunk in graph.stream(
        {"messages": [HumanMessage(content=message.content)]},
        thread_config,
        stream_mode="updates",
    ):
        if interruptobject := chunk.get("__interrupt__"):
            print(interruptobject)
            res = await cl.AskUserMessage(content=str(interruptobject[-1].value)).send()

    # after interrupt, resume node named `edit_this`
    for chunk in graph.stream(
        Command(
            resume=res["output"],
            update={"messages": HumanMessage(content=res["output"])},
        ),
        thread_config,
        stream_mode="updates",
    ):
        content = chunk[cl.user_session.get("interrupt_node_name")]["messages"].content
        await cl.Message(content=content).send()
