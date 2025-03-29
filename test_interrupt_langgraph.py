from langgraph.graph import MessagesState, StateGraph, START
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver


def edit_this(state: MessagesState):
    approved = interrupt(
        {"question": "Is this Correct?", "llm_output": state["messages"][-1].content}
    )

    if approved:
        print("Approved!")
    else:
        print("Rejected!")

    # 여기서 {edit: None} 나오기 싫으면 return state
    # 혹은 command에서 update message 치면 됨
    return state


graph_builder = StateGraph(MessagesState)
graph_builder.add_node("edit", edit_this)
graph_builder.add_edge(START, "edit")

checkpointer = MemorySaver()
graph = graph_builder.compile(checkpointer=checkpointer)

thread_config = {"configurable": {"thread_id": 1}}

for chunk in graph.stream(
    {"messages": [("human", "You are UGLY!")]},
    config=thread_config,
    stream_mode="updates",
):
    print(chunk)

for chunk in graph.stream(Command(resume=True), thread_config, stream_mode="updates"):
    print(chunk)
    print("\n")
