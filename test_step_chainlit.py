import chainlit as cl
from typing import Dict, Optional, cast


@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name="GPT-3.5",
            markdown_description="The underlying LLM model is **GPT-3.5**.",
            icon="https://picsum.photos/200",
        ),
        cl.ChatProfile(
            name="GPT-4",
            markdown_description="The underlying LLM model is **GPT-4**.",
            icon="https://picsum.photos/250",
        ),
    ]


@cl.header_auth_callback
async def header_auth_callback(headers: Dict | None) -> Optional[cl.User]:
    return cl.User(identifier="dev")


@cl.on_message
async def on_message(message: cl.Message):
    user = cast(cl.User, cl.user_session.get("user"))

    async with cl.Step(name="Test", type="tool") as step:
        step.input = message.content
        # stream with TavilySearchResult
        step.output = "No I'm not saying this"

        await cl.Message(content="Whole Process is Completed!").send()

        chat_profile = cl.user_session.get("chat_profile")
        await cl.Message(
            content=f"starting chat with {user.identifier} using the {chat_profile} chat profile"
        ).send()
