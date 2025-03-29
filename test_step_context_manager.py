import chainlit as cl


@cl.step(type="tool")
async def tool(message: str):
    print(message)
    return "Response from tool!"


@cl.step
async def parent_step():
    await child_step()
    return "Parent step output"


@cl.step
async def child_step():
    return "Child step output"


@cl.on_message
async def main(message: cl.Message):
    # tool Call result
    tool_res = await tool(message.content)
    await cl.Message(content=tool_res).send()

    await parent_step()
    # send Message
    await cl.Message(content=message.content).send()
