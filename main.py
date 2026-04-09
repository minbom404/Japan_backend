from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid
import os

app = FastAPI(title="BrewGo API", version="1.0.0")

# ✅ CORS (allow all for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Enums ─────────────────────────────────────────

class OrderStatus(str, Enum):
    pending = "pending"
    making = "making"
    ready = "ready"
    collected = "collected"
    cancelled = "cancelled"

class UserRole(str, Enum):
    admin = "admin"
    barista = "barista"
    cashier = "cashier"
    customer = "customer"

# ─── Models ────────────────────────────────────────

class MenuItem(BaseModel):
    id: str
    name: str
    description: str
    category: str
    price: float
    available: bool = True
    emoji: str = "☕"

class OrderItem(BaseModel):
    menu_item_id: str
    name: str
    quantity: int
    unit_price: float

class OrderCreate(BaseModel):
    customer_name: str
    items: List[OrderItem]
    note: Optional[str] = ""

class Order(BaseModel):
    id: str
    customer_name: str
    items: List[OrderItem]
    note: str
    status: OrderStatus
    total: float
    created_at: str

class StaffMember(BaseModel):
    id: str
    name: str
    role: UserRole
    email: str
    active: bool = True

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    available: Optional[bool] = None

# ─── In-memory DB ──────────────────────────────────

MENU: List[MenuItem] = [
    MenuItem(id="1", name="Espresso", description="Pure shot", category="Espresso", price=2.5),
    MenuItem(id="2", name="Latte", description="Milk coffee", category="Latte", price=4.0),
]

ORDERS: List[Order] = []
STAFF: List[StaffMember] = []

# ─── Health Check (IMPORTANT for Render) ───────────

@app.get("/")
def root():
    return {"status": "ok", "message": "BrewGo API running"}

# ─── Menu Routes ───────────────────────────────────

@app.get("/menu", response_model=List[MenuItem])
def get_menu():
    return [m for m in MENU if m.available]

@app.patch("/menu/{item_id}", response_model=MenuItem)
def update_menu_item(item_id: str, update: MenuItemUpdate):
    item = next((m for m in MENU if m.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    for field, value in update.dict(exclude_none=True).items():
        setattr(item, field, value)

    return item

# ─── Orders ────────────────────────────────────────

@app.post("/orders", response_model=Order)
def create_order(body: OrderCreate):
    total = sum(i.unit_price * i.quantity for i in body.items)

    order = Order(
        id=str(uuid.uuid4())[:6],
        customer_name=body.customer_name,
        items=body.items,
        note=body.note or "",
        status=OrderStatus.pending,
        total=round(total, 2),
        created_at=datetime.now().isoformat(),
    )

    ORDERS.append(order)
    return order

@app.get("/orders", response_model=List[Order])
def get_orders():
    return ORDERS

@app.patch("/orders/{order_id}/status", response_model=Order)
def update_order_status(order_id: str, status: OrderStatus):
    order = next((o for o in ORDERS if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = status
    return order

# ─── Staff ─────────────────────────────────────────

@app.get("/staff", response_model=List[StaffMember])
def get_staff():
    return STAFF

@app.post("/staff", response_model=StaffMember)
def add_staff(member: StaffMember):
    member.id = f"s{len(STAFF)+1}"
    STAFF.append(member)
    return member

# ─── Analytics ─────────────────────────────────────

@app.get("/analytics")
def analytics():
    total = sum(o.total for o in ORDERS)
    return {
        "orders": len(ORDERS),
        "revenue": total
    }

# ─── Run locally (Render ignores this) ─────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
