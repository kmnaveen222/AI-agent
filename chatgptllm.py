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
        r = requests.post(self.api_url, json={"tool": tool, "params": params}, timeout=30)
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

TOOLS = [
    restaurants_search, menus_list,
    cart_ensure, cart_view, cart_add_item, cart_update_item, cart_remove_item, cart_clear,
    orders_create_mock, orders_status_get, orders_status_advance_mock
]


SYSTEM_PROMPT = (
    "You are a food-ordering assistant. Use the tools to browse restaurants and menus, "
    "manage the user's cart (CART_ID is injected automatically), place mock orders, and track status. "
    "After each cart change, summarize items and subtotal in ₹ concisely."
)

# ---------------------------
# Model + create_agent (LangChain)
# ---------------------------
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4o-mini",   # fast + cheap
    # model="gpt-4o",      # stronger reasoning (optional)
    temperature=0.2
)

agent = create_agent(llm, 
                     tools=TOOLS,
                       system_prompt=SYSTEM_PROMPT,
                       )
# create_agent builds a graph-based agent you can invoke with a messages list. [1](https://docs.langchain.com/oss/python/langchain/agents)[2](https://reference.langchain.com/python/langchain/agents/)



def main():
    print(f"CART_ID: {CART_ID}")
    messages = [("user", "Initialize the empty cart"),]
    result = agent.invoke({"messages": messages})
    print("Assistant:", result["messages"][-1].content)

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

    try:
        while True:
            q = input("\nYou: ").strip()
            if not q:
                continue

            # 🔥 ONLY last user input
            messages = [("user", q)]

            result = agent.invoke({"messages": messages})
            print("Assistant:", result["messages"][-1].content)
    except KeyboardInterrupt:
        print("\nGoodbye!")

if __name__ == "__main__":
    main()