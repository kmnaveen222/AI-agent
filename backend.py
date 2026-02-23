# backend.py


from unittest import result
from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
import uuid

DB_PATH = "food1.db"

app = FastAPI(title="Food Order API")

# ---------- DB Helper ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- Request Model ----------
class InvokeRequest(BaseModel):
    tool: str
    params: dict


# ---------- API ----------
@app.post("/invoke")
def invoke(req: InvokeRequest):
    tool = req.tool
    params = req.params

    try:
        if tool == "restaurants.search":
            # print("Invoking restaurants.search with params:", params)
            return restaurants_search(params)

        if tool == "menus.list":
            return menus_list(params)

        if tool == "cart.ensure":
            return cart_ensure(params)

        if tool == "cart.add_item":
            return cart_add_item(params)

        if tool == "cart.view":
            return cart_view(params)
        
        if tool == "cart.update_item":
            return cart_update_item(params)

        if tool == "cart.remove_item":
            return cart_remove_item(params)

        if tool == "cart.clear":
            return cart_clear(params)

        if tool == "orders.create_mock":
            return orders_create(params)
        


        if tool == "conversation.create":
            conversation_id = conversation_create(params["cart_id"])
            return {"conversation_id": conversation_id}

        if tool == "conversation.save_message":
            conversation_save(
                params["conversation_id"],
                params["role"],
                params["content"]
            )
            return {"status": "saved"}

        if tool == "conversation.load":
            return {
                "messages": load_messages(params["conversation_id"])
            }

        return {"error": {"code": "UNKNOWN_TOOL", "message": tool}}

    except Exception as e:
        return {"error": {"code": "SERVER_ERROR", "message": str(e)}}


# ---------- Tool Implementations ----------
# def restaurants_search(p):
#     db = get_db()

#     q = """
#     SELECT *
#     FROM restaurants
#     WHERE is_open = 1
#       AND (:area IS NULL OR LOWER(area) LIKE '%' || LOWER(:area) || '%')
#       AND (:cuisine IS NULL OR LOWER(cuisine_tags) LIKE '%' || LOWER(:cuisine) || '%')
#     """

#     rows = db.execute(
#         q,
#         {
#             "area": p.get("area"),
#             "cuisine": p.get("cuisine")
#         }
#     ).fetchall()

#     return {"restaurants": [dict(r) for r in rows]}




def user_login_or_create(p):
    db = get_db()
    email = p["email"]

    user = db.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    ).fetchone()

    if user:
        return dict(user)

    user_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO users (id, email) VALUES (?, ?)",
        (user_id, email)
    )
    db.commit()

    return {"id": user_id, "email": email}





def restaurants_search(p):
    try:
        db = get_db()
        area = p.get("area") or None
        cuisine = p.get("cuisine") or None

        # 1️⃣ Get matching restaurants
        restaurants = db.execute(
            """
            SELECT *
            FROM restaurants
            WHERE is_open = 1
            AND (:area IS NULL OR LOWER(area) LIKE '%' || LOWER(:area) || '%')
            AND (:cuisine IS NULL OR LOWER(cuisine_tags) LIKE '%' || LOWER(:cuisine) || '%')
            """,
            {
                "area": area,
                "cuisine": cuisine
            }
        ).fetchall()

        result = []
        # print("Restaurants found:", [dict(r) for r in restaurants])

        # 2️⃣ For each restaurant, fetch matching menu items
        for r in restaurants:
            menu_items = db.execute(
            "SELECT * FROM menu_items WHERE restaurant_id = ? AND is_available = 1",
            (r["id"],)
            ).fetchall()

            result.append({
                "restaurant": dict(r),
                "menu": [dict(m) for m in menu_items]
            })
            print(f"Menu items for restaurant {r['id']}:", menu_items)
        print("Final result:", result)  
        return {"results": result}
    except Exception as e:
        print("Error in restaurants_search:", str(e))
        return {"error": {"code": "SERVER_ERROR", "message": str(e)}}


def menus_list(p):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM menu_items WHERE restaurant_id = ? AND is_available = 1",
        (p["restaurant_id"],)
    ).fetchall()
    return {"menu": [dict(r) for r in rows]}


def cart_ensure(p):
    db = get_db()
    cid = p["cart_id"]
    db.execute("INSERT OR IGNORE INTO carts(id) VALUES (?)", (cid,))
    db.commit()
    return {"cart_id": cid, "status": "ready"}


# def cart_add_item(p):
#     db = get_db()
#     item = db.execute(
#         "SELECT price_cents FROM menu_items WHERE id = ?",
#         (p["menu_item_id"],)
#     ).fetchone()

#     db.execute("""
#         INSERT INTO cart_items(cart_id, menu_item_id, quantity, unit_price_cents)
#         VALUES (?, ?, ?, ?)
#     """, (p["cart_id"], p["menu_item_id"], p["quantity"], item["price_cents"]))

#     db.commit()
#     return {"status": "item_added"}

def cart_add_item(p):
    db = get_db()

    cart_id = p["cart_id"]
    menu_item_id = p["menu_item_id"]
    quantity = p["quantity"]

    # 1️⃣ Get item price
    item = db.execute(
        "SELECT price_cents FROM menu_items WHERE id = ?",
        (menu_item_id,)
    ).fetchone()

    if not item:
        return {"error": "Menu item not found"}

    price_cents = item["price_cents"]

    # 2️⃣ Check if item already exists in cart
    existing = db.execute(
        """
        SELECT quantity FROM cart_items
        WHERE cart_id = ? AND menu_item_id = ?
        """,
        (cart_id, menu_item_id)
    ).fetchone()

    if existing:
        # 3️⃣ Update quantity (ADD to existing)
        new_qty = existing["quantity"] + quantity

        db.execute(
            """
            UPDATE cart_items
            SET quantity = ?
            WHERE cart_id = ? AND menu_item_id = ?
            """,
            (new_qty, cart_id, menu_item_id)
        )

        action = "quantity_updated"

    else:
        # 4️⃣ Insert new item
        db.execute(
            """
            INSERT INTO cart_items(cart_id, menu_item_id, quantity, unit_price_cents)
            VALUES (?, ?, ?, ?)
            """,
            (cart_id, menu_item_id, quantity, price_cents)
        )

        action = "item_added"

    db.commit()

    # 5️⃣ Return updated cart
    rows = db.execute(
        """
        SELECT mi.name, ci.quantity, ci.unit_price_cents,
               ci.quantity * ci.unit_price_cents AS total
        FROM cart_items ci
        JOIN menu_items mi ON mi.id = ci.menu_item_id
        WHERE ci.cart_id = ?
        """,
        (cart_id,)
    ).fetchall()

    subtotal = sum(r["total"] for r in rows)

    return {
        "status": action,
        "cart": {
            "items": [dict(r) for r in rows],
            "subtotal_rupees": subtotal / 100
        }
    }



def cart_view(p):
    db = get_db()
    rows = db.execute("""
        SELECT mi.name, ci.quantity, ci.unit_price_cents,
               ci.quantity * ci.unit_price_cents AS total
        FROM cart_items ci
        JOIN menu_items mi ON mi.id = ci.menu_item_id
        WHERE ci.cart_id = ?
    """, (p["cart_id"],)).fetchall()

    subtotal = sum(r["total"] for r in rows)
    return {
        "items": [dict(r) for r in rows],
        "subtotal_rupees": subtotal / 100
    }


def cart_update_item(p):
    db = get_db()

    if p["quantity"] == 0:
        db.execute(
            "DELETE FROM cart_items WHERE cart_id = ? AND menu_item_id = ?",
            (p["cart_id"], p["menu_item_id"])
        )
        db.commit()
        return {"status": "item_removed"}

    db.execute(
        """
        UPDATE cart_items
        SET quantity = ?
        WHERE cart_id = ? AND menu_item_id = ?
        """,
        (p["quantity"], p["cart_id"], p["menu_item_id"])
    )

    db.commit()
    return {
        "status": "item_updated",
        "menu_item_id": p["menu_item_id"],
        "quantity": p["quantity"]
    }


def cart_remove_item(p):
    db = get_db()
    db.execute(
        "DELETE FROM cart_items WHERE cart_id = ? AND menu_item_id = ?",
        (p["cart_id"], p["menu_item_id"])
    )
    db.commit()
    return {
        "status": "item_removed",
        "menu_item_id": p["menu_item_id"]
    }



def cart_clear(p):
    db = get_db()
    db.execute("DELETE FROM cart_items WHERE cart_id = ?", (p["cart_id"],))
    db.commit()
    return {"status": "cart_cleared"}


def orders_create(p):
    db = get_db()
    order_id = str(uuid.uuid4())

    subtotal = db.execute("""
        SELECT SUM(quantity * unit_price_cents) FROM cart_items WHERE cart_id = ?
    """, (p["cart_id"],)).fetchone()[0] or 0

    delivery = 4000  # flat delivery fee in cents
    total = subtotal + delivery

    db.execute("""
        INSERT INTO orders(id, cart_id, status, subtotal_cents, delivery_fee_cents, total_cents)
        VALUES (?, ?, 'PLACED', ?, ?, ?)
    """, (order_id, p["cart_id"], subtotal, delivery, total))

    db.commit()
    return {"order_id": order_id, "total_rupees": total / 100}




# ---------- Conversation Logging ----------

def conversation_create(cart_id: str) -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO conversations (cart_id) VALUES (?)",
        (cart_id,)
    )
    conn.commit()

    conversation_id = cursor.lastrowid  # ✅ cleaner & safer
    conn.close()

    return conversation_id


def conversation_save(conversation_id: int, role: str, content: str):
    conn = get_db()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content)
    )
    conn.commit()
    conn.close()


def load_messages(conversation_id: int):
    conn = get_db()
    cursor = conn.execute(
        "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id",
        (conversation_id,)
    )
    rows = cursor.fetchall()  # ✅ correct
    conn.close()

    return [(row["role"], row["content"]) for row in rows]
