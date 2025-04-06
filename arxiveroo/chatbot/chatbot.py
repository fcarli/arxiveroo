import datetime

import chainlit as cl
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from arxiveroo.tools.query import fetch_arxiv_papers, fetch_biorxiv_papers, fetch_medrxiv_papers

messages = []
model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.0)
available_tools = [fetch_arxiv_papers, fetch_biorxiv_papers, fetch_medrxiv_papers]
model = model.bind_tools(available_tools)
print(model)


def process_tool_call(tool_call: dict) -> str | None:
    """Process a tool call and return the result.

    Args:
        tool_call (dict): The tool call to process

    Returns:
        str | None: The result of the tool call or None if there is an error

    """
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    tool_call_id = tool_call["id"]

    tool_func = next((t for t in available_tools if t.name == tool_name), None)

    if tool_func:
        try:
            tool_result = tool_func.invoke(tool_args)
            print(tool_result)
            messages.append(ToolMessage(content=str(tool_result), name=tool_name, tool_call_id=tool_call_id))

            return tool_result

        except Exception as e:
            return f"Error: {e}"
    return None


@cl.on_chat_start
def on_chat_start():
    messages.append(
        SystemMessage(
            content=f"You are a helpful assistant that can fetch papers from arXiv. You have access to several tools and you use them whenever you can. \nToday is {datetime.datetime.now().strftime('%Y-%m-%d')}"
        )
    )
    print("A new chat session has started!")


@cl.on_message
async def on_message(msg: cl.Message):
    messages.append(HumanMessage(content=msg.content))
    response = await model.ainvoke(messages)

    if response.tool_calls:
        tool_result = process_tool_call(response.tool_calls[0])
        messages.append(AIMessage(content=tool_result))
        await cl.Message(tool_result).send()
    else:
        messages.append(AIMessage(content=response.content))
        await cl.Message(response.content).send()
        print(response)
