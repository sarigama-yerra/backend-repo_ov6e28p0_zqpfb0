import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Component, Build

app = FastAPI(title="PC Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo docs

def serialize(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    # Convert any nested ObjectIds if present
    for k, v in list(doc.items()):
        if isinstance(v, ObjectId):
            doc[k] = str(v)
    return doc


@app.get("/")
def read_root():
    return {"message": "PC Builder Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected & Working"
            response["database_url"] = "✅ Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ----- Components Endpoints -----

@app.get("/api/components", response_model=List[dict])
def list_components(type: Optional[str] = None):
    """List all components, optional filter by type"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    query = {}
    if type:
        query["type"] = type
    items = get_documents("component", query)
    return [serialize(i) for i in items]


@app.post("/api/components", status_code=201)
def add_component(comp: Component):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    new_id = create_document("component", comp)
    return {"id": new_id}


# Seed minimal catalog for demo
@app.post("/api/components/seed")
def seed_components():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    if db["component"].count_documents({}) > 0:
        return {"message": "Already seeded"}

    demo_items = [
        {"type": "cpu", "name": "Intel Core i5-12400F", "brand": "Intel", "price": 160.0, "socket": "LGA1700", "tdp": 65, "power_draw": 65},
        {"type": "cpu", "name": "AMD Ryzen 5 5600", "brand": "AMD", "price": 130.0, "socket": "AM4", "tdp": 65, "power_draw": 65},
        {"type": "motherboard", "name": "ASUS PRIME B660-PLUS", "brand": "ASUS", "price": 140.0, "socket": "LGA1700", "chipset": "B660", "ram_type": "DDR4", "form_factor": "ATX"},
        {"type": "motherboard", "name": "MSI B550M PRO-VDH WIFI", "brand": "MSI", "price": 110.0, "socket": "AM4", "chipset": "B550", "ram_type": "DDR4", "form_factor": "mATX"},
        {"type": "ram", "name": "Corsair Vengeance 16GB (2x8) 3200", "brand": "Corsair", "price": 45.0, "ram_type": "DDR4", "ram_speed": 3200, "capacity_gb": 16},
        {"type": "gpu", "name": "NVIDIA RTX 3060 12GB", "brand": "NVIDIA", "price": 280.0, "tdp": 170, "power_draw": 170},
        {"type": "storage", "name": "Samsung 970 EVO 1TB NVMe", "brand": "Samsung", "price": 75.0, "capacity_gb": 1000},
        {"type": "psu", "name": "Corsair CX650M 650W", "brand": "Corsair", "price": 80.0, "power_draw": 650},
        {"type": "case", "name": "NZXT H510", "brand": "NZXT", "price": 70.0, "supported_form_factors": ["ATX", "mATX", "ITX"]},
    ]

    for item in demo_items:
        create_document("component", item)

    return {"message": "Seeded demo components", "count": len(demo_items)}


# ----- Build Endpoints -----

class BuildCreate(BaseModel):
    name: str
    cpu_id: Optional[str] = None
    motherboard_id: Optional[str] = None
    ram_id: Optional[str] = None
    gpu_id: Optional[str] = None
    storage_id: Optional[str] = None
    psu_id: Optional[str] = None
    case_id: Optional[str] = None


def compute_build_stats(build: Dict[str, Optional[str]]):
    total_price = 0.0
    total_power = 0
    compatibility: Dict[str, str] = {}

    def fetch(id_):
        if not id_:
            return None
        try:
            obj = db["component"].find_one({"_id": ObjectId(id_)})
            return obj
        except Exception:
            return None

    cpu = fetch(build.get("cpu_id"))
    mobo = fetch(build.get("motherboard_id"))
    ram = fetch(build.get("ram_id"))
    gpu = fetch(build.get("gpu_id"))
    storage = fetch(build.get("storage_id"))
    psu = fetch(build.get("psu_id"))
    case = fetch(build.get("case_id"))

    for comp in [cpu, mobo, ram, gpu, storage, psu, case]:
        if comp and comp.get("price"):
            total_price += float(comp["price"])
        if comp and comp.get("power_draw"):
            total_power += int(comp["power_draw"])

    # Simple compatibility checks
    if cpu and mobo:
        if cpu.get("socket") != mobo.get("socket"):
            compatibility["cpu_motherboard"] = "Socket mismatch"
        else:
            compatibility["cpu_motherboard"] = "OK"

    if mobo and ram:
        if mobo.get("ram_type") and ram.get("ram_type") and mobo["ram_type"] != ram["ram_type"]:
            compatibility["motherboard_ram"] = "RAM type mismatch"
        else:
            compatibility["motherboard_ram"] = "OK"

    if psu and gpu:
        if psu.get("power_draw") and gpu.get("power_draw") and psu["power_draw"] < (gpu["power_draw"] + 100):
            compatibility["psu_gpu"] = "PSU wattage may be insufficient"
        else:
            compatibility["psu_gpu"] = "OK"

    if case and mobo:
        supported = case.get("supported_form_factors") or []
        if supported and mobo.get("form_factor") and mobo["form_factor"] not in supported:
            compatibility["case_motherboard"] = "Motherboard size not supported by case"
        else:
            compatibility["case_motherboard"] = "OK"

    return round(total_price, 2), total_power, compatibility


@app.post("/api/builds", status_code=201)
def create_build(payload: BuildCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    data = payload.model_dump()
    total_price, total_power, compatibility = compute_build_stats(data)
    data.update({
        "total_price": total_price,
        "total_power": total_power,
        "compatibility": compatibility,
    })

    new_id = create_document("build", data)
    return {"id": new_id, "total_price": total_price, "total_power": total_power, "compatibility": compatibility}


@app.get("/api/builds", response_model=List[dict])
def list_builds():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    items = get_documents("build")
    return [serialize(i) for i in items]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
