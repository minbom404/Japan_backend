"""
BrewGo – FastAPI Backend
Run: uvicorn main:app --reload
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

app = FastAPI(title="BrewGo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Enums ────────────────────────────────────────────────────────────────────

class OrderStatus(str, Enum):
    pending  = "pending"
    making   = "making"
    ready    = "ready"
    collected = "collected"
    cancelled = "cancelled"

class UserRole(str, Enum):
    admin    = "admin"
    barista  = "barista"
    cashier  = "cashier"
    customer = "customer"

# ─── Models ───────────────────────────────────────────────────────────────────

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

# ─── In-memory store (swap with PostgreSQL in production) ─────────────────────

MENU: List[MenuItem] = [
    MenuItem(id="1", name="Espresso",       description="Pure concentrated shot",    category="Espresso", price=2.50, emoji="☕"),
    MenuItem(id="2", name="Americano",      description="Espresso with hot water",   category="Espresso", price=3.00, emoji="🫖"),
    MenuItem(id="3", name="Flat White",     description="Micro-foam milk blend",     category="Latte",    price=4.00, emoji="🥛"),
    MenuItem(id="4", name="Caramel Latte",  description="Vanilla & caramel swirl",   category="Latte",    price=4.50, emoji="🍮"),
    MenuItem(id="5", name="Matcha Latte",   description="Ceremonial grade matcha",   category="Latte",    price=4.75, emoji="🍵"),
    MenuItem(id="6", name="Cold Brew",      description="12-hour steeping process",  category="Cold",     price=4.25, emoji="🧊"),
    MenuItem(id="7", name="Iced Mocha",     description="Dark choc espresso",        category="Cold",     price=5.00, emoji="🍫"),
    MenuItem(id="8", name="Croissant",      description="Butter, flaky pastry",      category="Food",     price=3.50, emoji="🥐"),
    MenuItem(id="9", name="Avocado Toast",  description="Sourdough & sea salt",      category="Food",     price=6.50, emoji="🥑"),
    MenuItem(id="10",name="Blueberry Muffin",description="Baked fresh daily",        category="Food",     price=3.00, emoji="🫐"),
]

ORDERS: List[Order] = []

STAFF: List[StaffMember] = [
    StaffMember(id="s1", name="Marco Silva",  role=UserRole.admin,   email="marco@brewgo.com"),
    StaffMember(id="s2", name="Priya Patel",  role=UserRole.barista, email="priya@brewgo.com"),
    StaffMember(id="s3", name="Jake Monroe",  role=UserRole.barista, email="jake@brewgo.com"),
    StaffMember(id="s4", name="Yuna Kim",     role=UserRole.barista, email="yuna@brewgo.com"),
    StaffMember(id="s5", name="Carlos Reyes", role=UserRole.cashier, email="carlos@brewgo.com"),
    StaffMember(id="s6", name="Nina Okafor",  role=UserRole.cashier, email="nina@brewgo.com"),
]

# ─── Menu Routes ──────────────────────────────────────────────────────────────

@app.get("/menu", response_model=List[MenuItem])
def get_menu(category: Optional[str] = None):
    items = [m for m in MENU if m.available]
    if category:
        items = [m for m in items if m.category.lower() == category.lower()]
    return items

@app.get("/menu/{item_id}", response_model=MenuItem)
def get_menu_item(item_id: str):
    item = next((m for m in MENU if m.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.patch("/menu/{item_id}", response_model=MenuItem)
def update_menu_item(item_id: str, update: MenuItemUpdate):
    item = next((m for m in MENU if m.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    for field, value in update.dict(exclude_none=True).items():
        setattr(item, field, value)
    return item

# ─── Order Routes ─────────────────────────────────────────────────────────────

@app.post("/orders", response_model=Order, status_code=201)
def create_order(body: OrderCreate):
    total = sum(i.unit_price * i.quantity for i in body.items)
    order = Order(
        id=f"#{str(uuid.uuid4())[:4].upper()}",
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
def get_orders(status: Optional[OrderStatus] = None):
    orders = ORDERS
    if status:
        orders = [o for o in orders if o.status == status]
    return sorted(orders, key=lambda o: o.created_at, reverse=True)

@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    order = next((o for o in ORDERS if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.patch("/orders/{order_id}/status", response_model=Order)
def update_order_status(order_id: str, status: OrderStatus):
    order = next((o for o in ORDERS if o.id == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status
    return order

# ─── Staff Routes ─────────────────────────────────────────────────────────────

@app.get("/staff", response_model=List[StaffMember])
def get_staff():
    return STAFF

@app.post("/staff", response_model=StaffMember, status_code=201)
def add_staff(member: StaffMember):
    member.id = f"s{len(STAFF)+1}"
    STAFF.append(member)
    return member

# ─── Analytics ────────────────────────────────────────────────────────────────

@app.get("/analytics/summary")
def get_summary():
    total_revenue = sum(o.total for o in ORDERS if o.status != OrderStatus.cancelled)
    active_orders = [o for o in ORDERS if o.status in [OrderStatus.pending, OrderStatus.making]]
    return {
        "total_orders": len(ORDERS),
        "total_revenue": round(total_revenue, 2),
        "active_orders": len(active_orders),
        "avg_order_value": round(total_revenue / max(len(ORDERS), 1), 2),
    }
