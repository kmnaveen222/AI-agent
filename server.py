import os, json, uuid, sys, textwrap
from typing import Optional

import requests
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# =========================
# Config
# =========================
API_URL = os.getenv("FOOD_API","http://127.0.0.1:8765/invoke")

# One cart per session; the tools will auto-inject this cart_id.
CART_ID = os.getenv("CART_ID") or str(uuid.uuid4())


# =========================
# Thin client for your /invoke endpoint
# =========================
class FoodAPI:
    def __init__(self, api_url: str):
        self.api_url = api_url

    def invoke(self, tool: str, params: dict):
        try:
            res = requests.post(self.api_url, json={"tool": tool, "params": params}, timeout=30)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            return {"error": {"code": "HTTP_ERROR", "message": str(e)}}


client = FoodAPI(API_URL)


# =========================
# Pydantic schemas (tool args)
# =========================

class RestaurantsSearchArgs(BaseModel):
    city: Optional[str] = Field(None, description="City name, e.g., 'Chennai'")
    area: Optional[str] = Field(None, description="Area/neighborhood, e.g., 'Guindy'")
    cuisine: Optional[str] = Field(None, description="Cuisine tag, e.g., 'Biryani'")
    min_rating: Optional[float] = Field(None, description="Minimum rating, e.g., 4.0")
    price_level: Optional[int] = Field(None, description="1=cheap, 2=mid, 3=premium")


class MenusListArgs(BaseModel):
    restaurant_id: int = Field(..., description="Restaurant ID")


class CartEnsureArgs(BaseModel):
    # auto-filled; kept for completeness/debug
    cart_id: Optional[str] = Field(None, description="Cart/session id")


class CartViewArgs(BaseModel):
    cart_id: Optional[str] = Field(None, description="Cart id (auto-filled)")


class CartAddItemArgs(BaseModel):
    menu_item_id: int = Field(..., description="Menu item ID to add")
    quantity: int = Field(1, ge=1, le=20, description="Quantity (1..20)")
    # cart_id injected


class CartUpdateItemArgs(BaseModel):
    menu_item_id: int = Field(..., description="Menu item ID to update")
    quantity: int = Field(..., ge=0, le=20, description="New quantity (0 removes the item)")


class CartRemoveItemArgs(BaseModel):
    menu_item_id: int = Field(..., description="Menu item ID to remove")


class CartClearArgs(BaseModel):
    pass


class OrdersCreateMockArgs(BaseModel):
    delivery_fee_cents: Optional[int] = Field(None, description="Override delivery fee (paise)")
    # cart_id injected


class OrdersStatusGetArgs(BaseModel):
    order_id: str = Field(..., description="Order ID to track")


class OrdersAdvanceMockArgs(BaseModel):
    order_id: str = Field(..., description="Order ID to advance status (dev/test)")


# If you have address tools in your server, uncomment these:
# class AddressSetArgs(BaseModel):
#     line1: str
#     city: str
#     pincode: str
#     line2: Optional[str] = None
#     landmark: Optional[str] = None
#
# class AddressGetArgs(BaseModel):
#     pass


# =========================
# Tool wrappers (each calls your API)
# =========================

def _json(o) -> str:
    """Return pretty JSON string to keep model outputs readable."""
    return json.dumps(o, ensure_ascii=False)


# ---- Restaurants ----
def restaurants_search_tool(city: Optional[str] = None, area: Optional[str] = None,
                            cuisine: Optional[str] = None, min_rating: Optional[float] = None,
                            price_level: Optional[int] = None) -> str:
    params = {
        "city": city, "area": area, "cuisine": cuisine,
        "min_rating": min_rating, "price_level": price_level
    }
    # remove None values
    params = {k: v for k, v in params.items() if v is not None}
    return _json(client.invoke("restaurants.search", params))


restaurants_search = StructuredTool.from_function(
    func=restaurants_search_tool,
    name="restaurants.search",
    description="Search open restaurants by city/area/cuisine/rating/price.",
    args_schema=RestaurantsSearchArgs,
)


# ---- Menus ----
def menus_list_tool(restaurant_id: int) -> str:
    return _json(client.invoke("menus.list", {"restaurant_id": restaurant_id}))


menus_list = StructuredTool.from_function(
    func=menus_list_tool,
    name="menus.list",
    description="List available menu items for a restaurant ID.",
    args_schema=MenusListArgs,
)


# ---- Cart ----
def cart_ensure_tool(cart_id: Optional[str] = None) -> str:
    cid = cart_id or CART_ID
    return _json(client.invoke("cart.ensure", {"cart_id": cid}))


cart_ensure = StructuredTool.from_function(
    func=cart_ensure_tool,
    name="cart.ensure",
    description="Ensure a cart exists for this session (idempotent).",
    args_schema=CartEnsureArgs,
)

def cart_view_tool(cart_id: Optional[str] = None) -> str:
    cid = cart_id or CART_ID
    return _json(client.invoke("cart.view", {"cart_id": cid}))


cart_view = StructuredTool.from_function(
    func=cart_view_tool,
    name="cart.view",
    description="View current cart items and subtotal.",
    args_schema=CartViewArgs,
)

def cart_add_item_tool(menu_item_id: int, quantity: int = 1) -> str:
    return _json(client.invoke("cart.add_item", {"cart_id": CART_ID, "menu_item_id": menu_item_id, "quantity": quantity}))


cart_add_item = StructuredTool.from_function(
    func=cart_add_item_tool,
    name="cart.add_item",
    description="Add a menu item to the current cart (quantity 1..20).",
    args_schema=CartAddItemArgs,
)

def cart_update_item_tool(menu_item_id: int, quantity: int) -> str:
    return _json(client.invoke("cart.update_item", {"cart_id": CART_ID, "menu_item_id": menu_item_id, "quantity": quantity}))


cart_update_item = StructuredTool.from_function(
    func=cart_update_item_tool,
    name="cart.update_item",
    description="Update quantity for a cart item; quantity=0 removes it.",
    args_schema=CartUpdateItemArgs,
)

def cart_remove_item_tool(menu_item_id: int) -> str:
    return _json(client.invoke("cart.remove_item", {"cart_id": CART_ID, "menu_item_id": menu_item_id}))


cart_remove_item = StructuredTool.from_function(
    func=cart_remove_item_tool,
    name="cart.remove_item",
    description="Remove an item from the current cart.",
    args_schema=CartRemoveItemArgs,
)

def cart_clear_tool() -> str:
    return _json(client.invoke("cart.clear", {"cart_id": CART_ID}))


cart_clear = StructuredTool.from_function(
    func=cart_clear_tool,
    name="cart.clear",
    description="Clear the current cart.",
    args_schema=CartClearArgs,
)


# ---- Address (uncomment if your server has address tools) ----
# def address_set_tool(line1: str, city: str, pincode: str, line2: Optional[str] = None, landmark: Optional[str] = None) -> str:
#     return _json(client.invoke("address.set", {
#         "cart_id": CART_ID,
#         "line1": line1, "city": city, "pincode": pincode,
#         "line2": line2, "landmark": landmark
#     }))
#
# address_set = StructuredTool.from_function(
#     func=address_set_tool,
#     name="address.set",
#     description="Set delivery address for the current cart (requires line1, city, 6-digit pincode).",
#     args_schema=AddressSetArgs,
# )
#
# def address_get_tool() -> str:
#     return _json(client.invoke("address.get", {"cart_id": CART_ID}))
#
# address_get = StructuredTool.from_function(
#     func=address_get_tool,
#     name="address.get",
#     description="Get the delivery address for the current cart.",
#     args_schema=AddressGetArgs,
# )


# ---- Orders ----
def orders_create_mock_tool(delivery_fee_cents: Optional[int] = None) -> str:
    params = {"cart_id": CART_ID}
    if delivery_fee_cents is not None:
        params["delivery_fee_cents"] = int(delivery_fee_cents)
    return _json(client.invoke("orders.create_mock", params))


orders_create_mock = StructuredTool.from_function(
    func=orders_create_mock_tool,
    name="orders.create_mock",
    description="Place a mock order from the current cart. Requires non-empty cart (and address if server enforces it).",
    args_schema=OrdersCreateMockArgs,
)

def orders_status_get_tool(order_id: str) -> str:
    return _json(client.invoke("orders.status.get", {"order_id": order_id}))


orders_status_get = StructuredTool.from_function(
    func=orders_status_get_tool,
    name="orders.status.get",
    description="Get current status and ETA for an order.",
    args_schema=OrdersStatusGetArgs,
)

def orders_status_advance_mock_tool(order_id: str) -> str:
    return _json(client.invoke("orders.status.advance_mock", {"order_id": order_id}))


orders_status_advance_mock = StructuredTool.from_function(
    func=orders_status_advance_mock_tool,
    name="orders.status.advance_mock",
    description="[DEV] Advance order status to the next step (PLACED→CONFIRMED→...).",
    args_schema=OrdersAdvanceMockArgs,
)


# =========================
# Assemble tools
# =========================
tools = [
    restaurants_search,
    menus_list,
    cart_ensure, cart_view, cart_add_item, cart_update_item, cart_remove_item, cart_clear,
    # address_set, address_get,  # uncomment if your server exposes these tools
    orders_create_mock, orders_status_get, orders_status_advance_mock,
]


# =========================
# Prompt & Agent
# =========================
SYSTEM_POLICY = """You are a food-ordering assistant. Use the provided tools to:
- Browse restaurants and menus.
- Manage the user's cart (always include the current cart_id; it is injected automatically).
- (If available) Set delivery address before checkout.
- Place mock orders and track their status.
Never fabricate tool results; always call a tool for database-backed operations.
After each cart mutation, summarize the cart with itemized lines and subtotal (₹). Keep responses concise.
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_POLICY),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

# Gemini model (Generative AI API)
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",   # or "gemini-1.5-flash" for cheaper/faster
    temperature=0.2,
)

agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


# =========================
# Simple REPL
# =========================
def main():
    # Ensure a cart for this session
    print(f"Using CART_ID: {CART_ID}")
    print(agent_executor.invoke({"input": "Initialize my cart for this session."})["output"])
    print("\nType your request (e.g., 'Show biryani places in Guindy', 'Add 2 Chicken Biryani from Buhari', 'Checkout').")
    print("Ctrl+C to exit.\n")
    try:
        while True:
            user = input("You: ").strip()
            if not user:
                continue
            out = agent_executor.invoke({"input": user})
            print("\nAssistant:", out["output"], "\n")
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()