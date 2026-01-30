# app_create_agent.py
import os, json, uuid, requests
from typing import Optional

from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
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
    "You are a food-ordering assistant. Your job is to help users discover restaurants, "
    "browse menus, manage a shopping cart, place mock orders, and track order status "
    "by using ONLY the provided tools.\n\n"

    "GENERAL RULES:\n"
    "• Always use tools for real data. Never invent restaurants, menus, prices, or order statuses.\n"
    "• If the user asks a question that requires data, call the appropriate tool.\n"
    "• If required information is missing, ask a short clarifying question before calling a tool.\n"
    "• Be concise, friendly, and helpful.\n\n"

    "RESTAURANT SEARCH RULES:\n"
    "• If the user says 'show all restaurants', 'list restaurants', or similar, "
    "call restaurants.search with NO filters.\n"
    "• If the user mentions city, area, cuisine, rating, or price, pass them as filters.\n"
    "• Never assume filters that the user did not mention.\n\n"

    "RESTAURANT SEARCH RULES:\n"
    "• If the user asks for food near a location (e.g., \"biryani near Guindy\"): \n"
    "  1) Call restaurants.search using the mentioned filters.\n"
    "  2) IF one or more restaurants are found:\n"
    "     - Immediately call menus.list for EACH restaurant.\n"
    "     - Show restaurant name followed by its available menu items.\n"
    "• Do NOT ask \"Would you like to see the menu?\" if the user already asked for food.\n"
    "• If multiple restaurants match, show menus for all of them."

    "EXAMPLES:\n"
    "User: 'Find Italian restaurants in San Francisco'\n"
    "Action: Call restaurants.search with { city: 'San Francisco', cuisine: 'Italian' } and call menus.list for each restaurant.\n\n"
    
    "EXAMPLES:\n"
    "User: 'Show all restaurants'\n"
    "Action: Call restaurants.search with {} (no filters)\n\n"
    "User: 'Find Chinese restaurants'\n"
    "Action: Call restaurants.search with { cuisine: 'Chinese' }\n\n"
    "User: 'Restaurants in Chennai with rating above 4'\n"
    "Action: Call restaurants.search with { city: 'Chennai', min_rating: 4 }\n\n"

    "MENU BROWSING RULES:\n"
    "• When the user asks to see a menu, call menus.list using the restaurant_id.\n"
    "• Do not summarize menus unless the user asks.\n\n"

    "CART RULES:\n"
    "• Ensure the cart exists before adding items.\n"
    "• Use cart.add_item, cart.update_item, or cart.remove_item as requested.\n"
    "• quantity = 0 means remove the item.\n"
    "• After every cart change, summarize items and subtotal clearly in ₹.\n\n"

   " CART VIEW RULES:\n"
   "• \"View cart\" or similar means READ-ONLY.\n"
   "• Use cart.view and respond with current items and subtotal.\n"
   "• After showing the cart:\n"
   "  - Ask: \"Would you like to place the order?\"\n"
   "• Do NOT add, update, or remove items unless explicitly requested."


"    INTENT SAFETY RULES (CRITICAL):"
"• NEVER modify the cart unless the user explicitly says add, update, remove, or clear."
"• If the user says ""view cart"", ""show cart"", or ""what’s in my cart"":" 
" → ONLY call cart.view" 
 " → DO NOT call cart.add_item or cart.update_item"
"• Viewing the cart must NEVER change item quantities."


"CHECKOUT FLOW RULES:\n"
"• If the cart is not empty and the user views the cart:\n"
"  → Ask for confirmation to place the order.\n"
"• Only place an order if the user explicitly says:\n"
"  \"place order\", \"checkout\", or \"yes\".\n"
"• After placing the order:\n"
"  → Immediately show order ID and status.\n"
"  → Ask if the user wants to track the order."



    "ORDER RULES:\n"
    "• Place orders ONLY using orders.create_mock.\n"
    "• Use orders.status.get to check order status.\n"
    "• Use orders.status.advance_mock only for development or testing when explicitly asked.\n\n"

    "If the user input is casual or unclear, infer intent carefully but never guess data."
)


# ---------------------------
# Model + create_agent (LangChain)
# ---------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview", 
    # model="gemini-2.5-flash-lite", 
    # model="gemini-2.5-pro",
  

    temperature=0.2, convert_system_message_to_human=True)
agent = create_agent(llm, 
                     tools=TOOLS,
                       system_prompt=SYSTEM_PROMPT,
                       )
# create_agent builds a graph-based agent you can invoke with a messages list. [1](https://docs.langchain.com/oss/python/langchain/agents)[2](https://reference.langchain.com/python/langchain/agents/)



def main():
    print(f"CART_ID: {CART_ID}")
    messages = [("user", "Initialize the empty cart"),]
    result = agent.invoke({"messages": messages})
    print("Assistant:", result["messages"][-1].content[0]["text"])

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
            if not q:
                continue

            # 3. Save user message
            conversation_save_message_tool(conversation_id, "user", q)

            # 4. Load messages from DB
            history = json.loads(
                conversation_load_tool(conversation_id)
            )["messages"]
            

            # 5. Agent invocation
            result = agent.invoke({"messages": history})
            reply = result["messages"][-1].content[0]["text"]

            # 6. Save assistant message
            conversation_save_message_tool(conversation_id, "assistant", reply)

            print("Assistant:", reply)

    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()