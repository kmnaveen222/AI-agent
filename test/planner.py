# planner.py
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

# ---------------------------
# Planner Output Schema
# ---------------------------
class Plan(BaseModel):
    tool: Optional[str] = None
    args: Dict[str, Any] = {}
    reason: Optional[str] = None


# ---------------------------
# Planner System Prompt
# ---------------------------
PLANNER_PROMPT = """
You are a planning assistant for a food ordering system.

Your job:
- Decide WHICH tool should be called
- Provide the correct arguments for that tool
- DO NOT execute any tool
- DO NOT explain in natural language
- Output ONLY valid JSON

Available tools:
- restaurants.search(city, area, cuisine, min_rating, price_level)
- menus.list(restaurant_id)
- cart.ensure(cart_id)
- cart.view(cart_id)
- cart.add_item(menu_item_id, quantity)
- cart.update_item(menu_item_id, quantity)
- cart.remove_item(menu_item_id)
- cart.clear()
- orders.create_mock(delivery_fee_cents)
- orders.status.get(order_id)
- orders.status.advance_mock(order_id)

Rules:
- If no tool is required, return tool=null
- args must be an object (even if empty)
- Do not add extra keys

Example:
{
  "tool": "cart.add_item",
  "args": { "menu_item_id": 12, "quantity": 2 }
}
"""


# ---------------------------
# Planner LLM
# ---------------------------
planner_llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=0,
)


# ---------------------------
# Planner Function
# ---------------------------
def plan(user_input: str) -> Plan:
    """
    Takes user input and returns a Plan:
    {
        tool: str | null,
        args: dict
    }
    """

    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": user_input}
    ]

    response = planner_llm.invoke(messages)
    print("Raw Planner Response:", response)

    # Gemini may return text or structured content
    content = response.content  
 
    if not content or content[0]["type"] != "text":
        raise ValueError("Planner did not return text")
 
    last = content[0]["text"]
    # print("Plannerstring:", last)
 
    return json.loads(last)

    # try:
    #     return Plan.model_validate_json(raw)
    # except Exception as e:
    #     raise ValueError(
    #         f"Planner returned invalid JSON:\n{raw}"
    #     ) from e


# ---------------------------
# Local Test
# ---------------------------
if __name__ == "__main__":
    while True:
        q = input("You: ").strip()
        if q in {"exit", "quit"}:
            break

        plan_result = plan(q)
        print("\nPLAN ↓",plan_result)
        # print(plan_result.model_dump_json(indent=2))
        # print("-" * 50)
