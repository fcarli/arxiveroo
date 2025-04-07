import datetime

import chainlit as cl
import pandas as pd
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, create_model
from pydantic.types import Literal

from arxiveroo.tools.query import fetch_arxiv_papers, fetch_biorxiv_papers, fetch_medrxiv_papers

nl = "\n"

model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.0)
available_tools = [fetch_arxiv_papers, fetch_biorxiv_papers, fetch_medrxiv_papers]
model = model.bind_tools(available_tools)


INITIALIZATION_PROMPT = """
You are an helpful assistnat that will help the user in selecting interesting papers. 
Consider the preferences of the user and select from the list of available resources the ones that are most relevant to the user.

<user_preferences>
{user_preferences}
</user_preferences>

<available_resources>
{available_resources}
</available_resources>
"""


commands = [
    {"id": "Initialize", "icon": "image", "description": "Initialize your preferences"},
    {"id": "ListCategories", "icon": "image", "description": "List the available categories"},
]


def process_tool_call(tool_call: dict) -> str | None:
    """Process a tool call and return the result.

    Args:
        tool_call (dict): The tool call to process

    Returns:
        str | None: The result of the tool call or None if there is an error

    """
    messages = cl.user_session.get("messages")
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


def create_category_model(categories: list[str]) -> type[BaseModel]:
    """Create a Pydantic model with a field for a list of relevant categories.

    Args:
        categories: A list of category codes

    Returns:
        type[BaseModel]: A Pydantic model with a single field containing a list of
                         selected categories from the provided options

    """
    # Create a Literal type with all possible categories
    LiteralCategories = Literal[tuple(categories)]  # type: ignore

    # Create a model with a single field for the list of selected categories
    DynamicModel = create_model(
        "DynamicModel",
        selected_categories=(list[LiteralCategories], ...),  # Required field with list of categories
    )

    return DynamicModel


async def initialize_preferences(content: str):
    # read the resources csv TODO: remember to relativize the path
    initalization_chat = []
    resources = pd.read_csv("/Users/mrcharles/LocalProj/feedSelector/arxiveroo/resources/categories_index.csv")

    # join all rows into a single string
    string_resources = ""
    categories = []
    for index, row in resources.iterrows():
        string_resources += f"{row['category_code']}: {row['description']}\n"
        categories.append(row["category_code"])

    # model initialization
    model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.0)

    # structured output
    CategoryModel = create_category_model(categories)
    model = model.with_structured_output(CategoryModel)

    # save the first message
    initalization_chat.append(HumanMessage(content=content))

    # first call to the model
    response = model.invoke(
        INITIALIZATION_PROMPT.format(user_preferences=content, available_resources=string_resources)
    )

    # format the response
    response = f"I've selected the following categories for you:{nl}-{(nl + '-').join(response.selected_categories)}"

    # save the response into the messages
    initalization_chat.append(AIMessage(content=response))

    await cl.Message(content=response).send()

    not_satisfied = True

    while not_satisfied:
        res = await cl.AskActionMessage(
            content="Are you satisfied with the selection?",
            actions=[
                cl.Action(name="Yes", payload={"value": "continue"}, label="✅ Continue"),
                cl.Action(name="No", payload={"value": "cancel"}, label="❌ Cancel"),
            ],
        ).send()

        if res["name"] == "Yes":
            not_satisfied = False
            await cl.Message("Great! I'll save your preferences.").send()
        else:
            res = await cl.AskUserMessage(content="Tell me what you want to change").send()

            # simulate the response
            initalization_chat.append(AIMessage(content="Tell me what you want to change"))

            # append the user message to refine the selection
            initalization_chat.append(HumanMessage(content=res["output"]))

            # invoke the model again
            refined_response = model.invoke(initalization_chat)

            # format the response
            response = f"I've selected the following categories for you:{nl}-{(nl + '-').join(refined_response.selected_categories)}"

            # send the response to screen
            await cl.Message(response).send()

            # save the response into the messages
            initalization_chat.append(AIMessage(content=response))

    return string_resources


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("messages", [])
    await cl.context.emitter.set_commands(commands)
    messages = cl.user_session.get("messages")
    messages.append(
        SystemMessage(
            content=f"You are a helpful assistant that can fetch papers from arXiv. You have access to several tools and you use them whenever you can. \nToday is {datetime.datetime.now().strftime('%Y-%m-%d')}"
        )
    )
    print("A new chat session has started!")


@cl.on_message
async def on_message(msg: cl.Message):
    messages = cl.user_session.get("messages")

    if msg.command == "Initialize":
        await cl.Message("Initializing your preferences!").send()
        await initialize_preferences(msg.content)

        return

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
