import copy
import datetime
import importlib.resources
import json
import os
import pathlib
from collections.abc import Callable

import chainlit as cl
import pandas as pd

# Import dotenv
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import BaseModel, create_model
from pydantic.types import Literal

from arxiveroo.tools.query import fetch_arxiv_papers, fetch_biorxiv_papers, fetch_medrxiv_papers, fetch_all_papers

# Load environment variables from .env file
load_dotenv()

nl = "\n"


# Define the preference directory path
preference_path_env = os.getenv("PREFERENCE_PATH")
if preference_path_env:
    PREFERENCE_DIR = pathlib.Path(preference_path_env)
else:
    PREFERENCE_DIR = pathlib.Path.home() / ".cache" / "arxiveroo"

# Ensure the directory exists
PREFERENCE_DIR.mkdir(parents=True, exist_ok=True)


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
    {"id": "Initialize", "icon": "land-plot", "description": "Initialize your preferences"},
    {"id": "ListCategories", "icon": "layout-list", "description": "List the available categories"},
]


def process_tool_call(tool_call: dict, available_tools: list[Callable]) -> str | None:
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
    messages = cl.user_session.get("messages")
    initalization_chat = []
    initalization_chat.extend(messages)

    # Use importlib.resources to get the path to the CSV file
    # The resource is located within the 'arxiveroo.resources' subpackage/directory
    with importlib.resources.files("arxiveroo.resources").joinpath("categories_index.csv") as resource_path:
        resources = pd.read_csv(resource_path)

    # join all rows into a single string
    string_resources = ""
    categories_dict = {}
    for index, row in resources.iterrows():
        string_resources += f"{row['category_code']}: {row['description']}\n"
        categories_dict[row["category_code"]] = (row["description"], row["database"])

    # model initialization
    # TODO: extend also to other models
    model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.0)

    # structured output
    CategoryModel = create_category_model(list(categories_dict.keys()))
    # save the first message
    initalization_chat.append(HumanMessage(content=content))

    chat_so_far = "\n".join([str(m.content) for m in initalization_chat])

    # take the conversation so far, summarize it and save it to cache for later use
    interests_summary = copy.deepcopy(initalization_chat)
    interests_summary.append(
        HumanMessage(
            content="Given the above conversation, save the user's interests in a detailed description (also keywords). Only output the description, no other text."
        )
    )
    interests_summary = model.invoke(interests_summary).content

    with open(PREFERENCE_DIR / "interests_summary.json", "w") as f:
        json.dump(interests_summary, f)

    # first call to the model
    response = model.with_structured_output(CategoryModel).invoke(
        INITIALIZATION_PROMPT.format(user_preferences=chat_so_far, available_resources=string_resources)
    )

    # save the categories to cache
    with open(PREFERENCE_DIR / "categories.json", "w") as f:
        json.dump(response.selected_categories, f)

    selected_categories = [
        f"**{category}** ({categories_dict[category][1]}): {categories_dict[category][0]}"
        for category in response.selected_categories
    ]

    # format the response
    response = f"I've selected the following categories for you:{nl}-{(nl + '-').join(selected_categories)}"

    # save the response into the messages
    initalization_chat.append(AIMessage(content=response))

    await cl.Message(content=response).send()

    not_satisfied = True

    while not_satisfied:
        res = await cl.AskActionMessage(
            content="Are you satisfied with the selection?",
            actions=[
                cl.Action(name="Yes", payload={"value": "Yes"}, label="✅ Continue"),
                cl.Action(name="No", payload={"value": "No"}, label="❌ Cancel"),
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
            refined_response = model.with_structured_output(CategoryModel).invoke(initalization_chat)

            # save the categories to cache
            with open(PREFERENCE_DIR / "categories.json", "w") as f:
                json.dump(refined_response.selected_categories, f)

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

    # save the user message
    messages.append(HumanMessage(content=msg.content))

    if msg.command == "Initialize":
        await cl.Message("Initializing your preferences!").send()
        await initialize_preferences(msg.content)

    elif msg.command == "ListCategories":
        pass  # TODO: implement this

    elif msg.command == "ApplyPreferences":
        # bind with preferred tool
        model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.0)
        available_tools = [tool(fetch_all_papers)]
        model = model.bind_tools(available_tools)

        response = await model.ainvoke(messages)

    else:
        # bind with all tools #TODO: implement capibility to handle multiple tool calls
        model = init_chat_model("google_genai:gemini-2.0-flash", temperature=0.0)
        available_tools = [tool(fetch_arxiv_papers), tool(fetch_biorxiv_papers), tool(fetch_medrxiv_papers)]
        model = model.bind_tools(available_tools)

        response = await model.ainvoke(messages)

    if response.tool_calls:
        tool_result_txt, tool_result_data = await process_tool_call(response.tool_calls[0], available_tools)
        messages.append(AIMessage(content=tool_result_txt))
        await cl.Message(tool_result_txt).send()
    else:
        messages.append(AIMessage(content=response.content))
        await cl.Message(response.content).send()
        print(response)
