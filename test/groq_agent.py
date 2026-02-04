# app_create_agent.py
import os, json, uuid, requests
from typing import Optional

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.agents import create_agent  # LangChain's production agent API
from dotenv import load_dotenv
load_dotenv()




API_URL = os.getenv("FOOD_API", "http://127.0.0.1:8765/invoke")
CART_ID = os.getenv("CART_ID") or str(uuid.uuid4())


# ---------------------------
# Thin client for your /invoke
# ---------------------------
class FoodAPI:
    def __init__(self, api_url: str):
        self.api_url = api_url
    def invoke(self, tool: str, params: dict):
        r = requests.post(self.api_url, json={"tool": tool, "params": params})
        r.raise_for_status()
        return r.json()

client = FoodAPI(API_URL)
def _json(o) -> str: return json.dumps(o, ensure_ascii=False)

# ---------------------------
# Pydantic arg schemas
# ---------------------------
class RestaurantsSearchArgs(BaseModel):
    city: Optional[str] = None
    area: Optional[str] = None
    cuisine: Optional[str] = None
    min_rating: Optional[float] = None
    price_level: Optional[int] = None

class MenusListArgs(BaseModel):
    restaurant_id: int

class CartEnsureArgs(BaseModel):
    cart_id: Optional[str] = None

class CartViewArgs(BaseModel):
    cart_id: Optional[str] = None

class CartAddItemArgs(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, ge=1, le=20)

class CartUpdateItemArgs(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., ge=0, le=20)

class CartRemoveItemArgs(BaseModel):
    menu_item_id: int

class CartClearArgs(BaseModel):
    pass

class OrdersCreateMockArgs(BaseModel):
    delivery_fee_cents: Optional[int] = None

class OrdersStatusGetArgs(BaseModel):
    order_id: str

class OrdersAdvanceMockArgs(BaseModel):
    order_id: str

class ConversationCreateArgs(BaseModel):
    cart_id: str


class ConversationSaveMessageArgs(BaseModel):
    conversation_id: int
    role: str
    content: str

class ConversationLoadArgs(BaseModel):
    conversation_id: int



# ---------------------------
# Tool wrappers (each calls your API)
# ---------------------------
def restaurants_search_tool(city=None, area=None, cuisine=None, min_rating=None, price_level=None) -> str:
    params = {k: v for k, v in {
        "city": city, "area": area, "cuisine": cuisine,
        "min_rating": min_rating, "price_level": price_level
    }.items() if v is not None}
    return _json(client.invoke("restaurants.search", params))

def menus_list_tool(restaurant_id: int) -> str:
    return _json(client.invoke("menus.list", {"restaurant_id": restaurant_id}))

def cart_ensure_tool(cart_id: Optional[str] = None) -> str:
    return _json(client.invoke("cart.ensure", {"cart_id": cart_id or CART_ID}))

def cart_view_tool(cart_id: Optional[str] = None) -> str:
    return _json(client.invoke("cart.view", {"cart_id": cart_id or CART_ID}))

def cart_add_item_tool(menu_item_id: int, quantity: int = 1) -> str:
    return _json(client.invoke("cart.add_item", {"cart_id": CART_ID, "menu_item_id": menu_item_id, "quantity": quantity}))

def cart_update_item_tool(menu_item_id: int, quantity: int) -> str:
    return _json(client.invoke("cart.update_item", {"cart_id": CART_ID, "menu_item_id": menu_item_id, "quantity": quantity}))

def cart_remove_item_tool(menu_item_id: int) -> str:
    return _json(client.invoke("cart.remove_item", {"cart_id": CART_ID, "menu_item_id": menu_item_id}))

def cart_clear_tool() -> str:
    return _json(client.invoke("cart.clear", {"cart_id": CART_ID}))

def orders_create_mock_tool(delivery_fee_cents: Optional[int] = None) -> str:
    p = {"cart_id": CART_ID}
    if delivery_fee_cents is not None:
        p["delivery_fee_cents"] = int(delivery_fee_cents)
    return _json(client.invoke("orders.create_mock", p))

def orders_status_get_tool(order_id: str) -> str:
    return _json(client.invoke("orders.status.get", {"order_id": order_id}))

def orders_status_advance_mock_tool(order_id: str) -> str:
    return _json(client.invoke("orders.status.advance_mock", {"order_id": order_id}))




def conversation_create_tool(cart_id: str) -> str:
    return _json(client.invoke("conversation.create", {"cart_id": cart_id}))

def conversation_save_message_tool(conversation_id: int, role: str, content: str) -> str:
    return _json(client.invoke(
        "conversation.save_message",
        {
            "conversation_id": conversation_id,
            "role": role,
            "content": content
        }
    ))

def conversation_load_tool(conversation_id: int) -> str:
    return _json(client.invoke(
        "conversation.load",
        {"conversation_id": conversation_id}
    ))
# ---------------------------
# Build LangChain tools (StructuredTool from langchain_core.tools)
# ---------------------------
restaurants_search = StructuredTool.from_function(
    func=restaurants_search_tool,
    name="restaurants.search",
    description="Search open restaurants by city/area/cuisine/rating/price.",
    args_schema=RestaurantsSearchArgs
)
menus_list = StructuredTool.from_function(
    func=menus_list_tool, name="menus.list",
    description="List available menu items for a restaurant.",
    args_schema=MenusListArgs
)
cart_ensure = StructuredTool.from_function(
    func=cart_ensure_tool, name="cart.ensure",
    description="Ensure a cart exists for this session (idempotent).",
    args_schema=CartEnsureArgs
)
cart_view = StructuredTool.from_function(
    func=cart_view_tool, name="cart.view",
    description="View current cart items and subtotal.",
    args_schema=CartViewArgs
)
cart_add_item = StructuredTool.from_function(
    func=cart_add_item_tool, name="cart.add_item",
    description="Add a menu item to the current cart (quantity 1..20).",
    args_schema=CartAddItemArgs
)
cart_update_item = StructuredTool.from_function(
    func=cart_update_item_tool, name="cart.update_item",
    description="Update quantity for a cart item; quantity=0 removes it.",
    args_schema=CartUpdateItemArgs
)
cart_remove_item = StructuredTool.from_function(
    func=cart_remove_item_tool, name="cart.remove_item",
    description="Remove an item from the current cart.",
    args_schema=CartRemoveItemArgs
)
cart_clear = StructuredTool.from_function(
    func=cart_clear_tool, name="cart.clear",
    description="Clear the current cart.",
    args_schema=CartClearArgs
)
orders_create_mock = StructuredTool.from_function(
    func=orders_create_mock_tool, name="orders.create_mock",
    description="Place a mock order from the current cart.",
    args_schema=OrdersCreateMockArgs
)
orders_status_get = StructuredTool.from_function(
    func=orders_status_get_tool, name="orders.status.get",
    description="Get current status and ETA for an order.",
    args_schema=OrdersStatusGetArgs
)
orders_status_advance_mock = StructuredTool.from_function(
    func=orders_status_advance_mock_tool, name="orders.status.advance_mock",
    description="[DEV] Advance the order status.",
    args_schema=OrdersAdvanceMockArgs

)
conversation_create = StructuredTool.from_function(
    func=conversation_create_tool,
    name="conversation.create",
    description="Create a new conversation and return conversation_id",
    args_schema=ConversationCreateArgs
)

conversation_save_message = StructuredTool.from_function(
    func=conversation_save_message_tool,
    name="conversation.save_message",
    description="Save a chat message",
    args_schema=ConversationSaveMessageArgs
)
conversation_load = StructuredTool.from_function(
    func=conversation_load_tool,
    name="conversation.load",
    description="Load full conversation history",
    args_schema=ConversationLoadArgs
)





TOOLS = [
    restaurants_search, menus_list,
    cart_ensure, cart_view, cart_add_item, cart_update_item, cart_remove_item, cart_clear,
    orders_create_mock, orders_status_get, orders_status_advance_mock,conversation_create,conversation_save_message
]



SYSTEM_PROMPT = (
    "You are a food-ordering assistant.\n\n"

    "=========================\n"
    "CRITICAL TOOL EXECUTION RULES (MANDATORY)\n"
    "=========================\n"
    "- You MUST use tools to get real data.\n"
    "- NEVER fabricate restaurants, menus, prices, carts, or order statuses.\n"
    "- If user intent requires data, you MUST call the appropriate tool.\n"
    "- You can call ONLY ONE tool per response.\n"
    "- If multiple tool calls are required, perform them STEP-BY-STEP across turns.\n"
    "- NEVER attempt multiple tool calls in a single response.\n"
    "- Do NOT respond with plain text if a tool is applicable.\n"
    "- After a tool call, respond strictly based on the tool output.\n"
    "- If required information is missing, ask ONE short clarifying question.\n\n"

    "=========================\n"
    "GENERAL BEHAVIOR RULES\n"
    "=========================\n"
    "- Initialize the cart at the first user interaction using cart.ensure.\n"
    "- Be concise, friendly, and helpful.\n"
    "- Never assume missing details.\n\n"

    "=========================\n"
    "RESTAURANT SEARCH RULES\n"
    "=========================\n"
    "- If the user says 'show all restaurants', 'list restaurants', or similar:\n"
    "  → Call restaurants.search with NO filters.\n"
    "- If the user mentions city, area, cuisine, rating, or price:\n"
    "  → Pass ONLY those as filters.\n"
    "- Never invent filters.\n\n"

    "If the user asks for food near a location (example: 'biryani near Guindy'):\n"
    "1) Call restaurants.search using the mentioned filters.\n"
    "2) After receiving search results:\n"
    "   - If ONE restaurant is found:\n"
    "     → Call menus.list for that restaurant in the NEXT turn.\n"
    "   - If MULTIPLE restaurants are found:\n"
    "     → Ask the user which restaurant they want the menu for.\n"
    "   - Do NOT call menus.list for multiple restaurants automatically.\n\n"

    "=========================\n"
    "MENU BROWSING RULES\n"
    "=========================\n"
    "- When the user explicitly asks to see a menu:\n"
    "  → Call menus.list using the provided restaurant_id.\n"
    "- Do not summarize menu items unless asked.\n\n"

    "=========================\n"
    "CART RULES\n"
    "=========================\n"
    "- Ensure the cart exists before any cart operation.\n"
    "- Use cart.add_item, cart.update_item, or cart.remove_item ONLY when explicitly requested.\n"
    "- quantity = 0 means remove the item.\n"
    "- After every cart change, summarize items and subtotal clearly in ₹.\n\n"

    "=========================\n"
    "CART VIEW SAFETY RULES (CRITICAL)\n"
    "=========================\n"
    "- 'View cart', 'show cart', or 'what’s in my cart' is READ-ONLY.\n"
    "- ONLY call cart.view.\n"
    "- NEVER modify the cart during cart viewing.\n"
    "- After showing the cart, ask:\n"
    "  'Would you like to place the order?'\n\n"

    "=========================\n"
    "CHECKOUT RULES\n"
    "=========================\n"
    "- Place an order ONLY if the user explicitly says 'place order' or 'yes'.\n"
    "- Use orders.create_mock to place orders.\n"
    "- After placing an order:\n"
    "  → Show order ID and current status.\n"
    "  → Ask if the user wants to track the order.\n\n"

    "=========================\n"
    "ORDER TRACKING RULES\n"
    "=========================\n"
    "- Use orders.status.get to fetch order status.\n"
    "- Use orders.status.advance_mock ONLY if the user explicitly asks (development only).\n\n"

    "If the user input is unclear, infer intent carefully but NEVER guess data."
)



# ---------------------------
# Model + create_agent (LangChain)
# ---------------------------
# llm = ChatGoogleGenerativeAI(
#     model="gemini-3-flash-preview", 
    # model="gemini-2.5-flash-lite", 
    # model="gemini-2.5-pro",

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2, )
agent = create_agent(llm, 
                     tools=TOOLS,
                       system_prompt=SYSTEM_PROMPT,
                       )
# create_agent builds a graph-based agent you can invoke with a messages list. [1](https://docs.langchain.com/oss/python/langchain/agents)[2](https://reference.langchain.com/python/langchain/agents/)
from langchain_core.messages import AIMessage

def extract_assistant_text(messages):
    """
    Safely extract the last assistant text message.
    Returns None if no final assistant text exists yet.
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content

            if isinstance(content, str):
                return content.strip()

            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        return item["text"].strip()

    return None



def main():
    print(f"CART_ID: {CART_ID}")
    print("Welcome to the Food Ordering Assistant! Type your messages below (Ctrl+C to exit).")
    # messages = [("user", "Initialize the empty cart"),]
    # result = agent.invoke({"messages": messages})
    # print("Assistant:", result["messages"][-1].content[0]["text"])

    # try:
    #     while True:
    #         q = input("\nYou: ").strip()
    #         if not q: 
    #             continue
    #         messages.append(("user", q))
    #         result = agent.invoke({"messages": messages})
    #         # print the last assistant message
    #         print("Assistant:", result["messages"][-1].content)
    #         # keep the whole conversation as state
    #         messages = [(m.type, m.content) for m in result["messages"]]

    # try:
    #     while True:
    #         q = input("\nYou: ").strip()
    #         if not q:
    #             continue

    #         # 🔥 ONLY last user input
    #         messages = [("user", q)]

    #         result = agent.invoke({"messages": messages})
    #         print("Assistant:", result["messages"][-1].content)
    # except KeyboardInterrupt:
    #     print("\nGoodbye!")


    print(f"CART_ID: {CART_ID}")



    # 2. Create conversation
    conv = json.loads(conversation_create_tool(CART_ID))
    # conv = json.loads(conversation_create_tool(CART_ID))
    conversation_id = conv["conversation_id"]

    print("Conversation ID:", conversation_id)


    try:
        while True:
        
            q = input("\nYou: ").strip()
            if q in {"quit","exit","q","bye","goodbye","stop"}:
                break
            if not q:
                continue

            # 3. Save user message
            conversation_save_message_tool(conversation_id, "user", q)

            # 4. Load messages from DB
            history = json.loads(
                conversation_load_tool(conversation_id)
            )["messages"]
            # print("History:", history)

            # 5. Agent invocation
            result = agent.invoke({"messages": history})
            reply = extract_assistant_text(result["messages"])
            #["messages"][-1].content[0]["text"]

            # 6. Save assistant message
            if reply:
                conversation_save_message_tool(conversation_id, "assistant", reply)
                print("Assistant:", reply)
            else:
                print("⏳ Assistant is still processing tools...")

    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()