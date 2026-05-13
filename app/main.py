from datetime import datetime
from io import BytesIO

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
    get_password_hash,
)
from app.database import engine
from app.models import (
    Asset,
    AssetMovement,
    Assignment,
    AuditLog,
    Base,
    DepreciationRecord,
    Employee,
    LifecycleEvent,
    LostReport,
    MaintenanceHistory,
    Office,
    ProcurementRecommendation,
    Repair,
    User,
    Vendor,
)
from app.schemas import (
    AssetCreate,
    AssignmentCreate,
    DepreciationCreate,
    EmployeeCreate,
    LifecycleEventCreate,
    LostReportCreate,
    MaintenanceHistoryCreate,
    MovementScanCreate,
    OfficeCreate,
    ProcurementRecommendationCreate,
    RepairCreate,
    Token,
    UserCreate,
    VendorCreate,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Office Asset Intelligence")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def audit(db: Session, action: str, entity: str, entity_id: int):
    db.add(AuditLog(action=action, entity=entity, entity_id=entity_id))
    db.commit()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "office-asset-intelligence"}


@app.post("/auth/register")
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(username=payload.username, hashed_password=get_password_hash(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    audit(db, "create", "user", user.id)
    return {"id": user.id, "username": user.username}


@app.post("/auth/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=None,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/offices")
def create_office(payload: OfficeCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    office = Office(**payload.model_dump())
    db.add(office)
    db.commit()
    db.refresh(office)
    audit(db, "create", "office", office.id)
    return {"id": office.id, "name": office.name, "location": office.location}


@app.get("/offices")
def list_offices(db: Session = Depends(get_db), _=Depends(get_current_user)):
    offices = db.query(Office).all()
    return [{"id": o.id, "name": o.name, "location": o.location} for o in offices]


@app.post("/vendors")
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    audit(db, "create", "vendor", vendor.id)
    return {"id": vendor.id, "name": vendor.name, "contact_email": vendor.contact_email}


@app.post("/employees")
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    audit(db, "create", "employee", employee.id)
    return {"id": employee.id, "name": employee.name, "department": employee.department}


@app.get("/employees")
def list_employees(db: Session = Depends(get_db), _=Depends(get_current_user)):
    employees = db.query(Employee).all()
    return [{"id": e.id, "name": e.name, "department": e.department} for e in employees]


@app.post("/assets")
def create_asset(payload: AssetCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    db.add(DepreciationRecord(asset_id=asset.id, current_value=asset.purchase_cost, annual_rate=0.2))
    db.commit()
    audit(db, "create", "asset", asset.id)
    return {
        "id": asset.id,
        "name": asset.name,
        "category": asset.category,
        "serial_number": asset.serial_number,
        "barcode": asset.barcode,
        "office_id": asset.office_id,
        "vendor_id": asset.vendor_id,
        "purchase_cost": asset.purchase_cost,
        "status": asset.status,
    }


@app.get("/assets")
def list_assets(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    office_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(Asset)
    if q:
        query = query.filter(Asset.name.ilike(f"%{q}%"))
    if category:
        query = query.filter(Asset.category == category)
    if office_id:
        query = query.filter(Asset.office_id == office_id)
    assets = query.all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "category": a.category,
            "serial_number": a.serial_number,
            "barcode": a.barcode,
            "office_id": a.office_id,
            "vendor_id": a.vendor_id,
            "purchase_cost": a.purchase_cost,
            "status": a.status,
        }
        for a in assets
    ]


@app.post("/assets/scan")
def scan_asset(payload: MovementScanCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.barcode == payload.barcode).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    movement = AssetMovement(asset_id=asset.id, office_id=payload.office_id)
    db.add(movement)
    db.commit()
    db.refresh(movement)
    audit(db, "scan", "asset", asset.id)
    return {"asset_id": asset.id, "movement_id": movement.id, "timestamp": movement.scanned_at}


@app.post("/assignments")
def assign_asset(payload: AssignmentCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    assignment = Assignment(**payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    db.add(LifecycleEvent(asset_id=payload.asset_id, event_type="assigned", notes=f"employee:{payload.employee_id}"))
    db.commit()
    audit(db, "create", "assignment", assignment.id)
    return {
        "id": assignment.id,
        "asset_id": assignment.asset_id,
        "employee_id": assignment.employee_id,
        "assigned_at": assignment.assigned_at,
        "returned_at": assignment.returned_at,
    }


@app.post("/lifecycle")
def create_lifecycle_event(
    payload: LifecycleEventCreate, db: Session = Depends(get_db), _=Depends(get_current_user)
):
    event = LifecycleEvent(**payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    audit(db, "create", "lifecycle_event", event.id)
    return {
        "id": event.id,
        "asset_id": event.asset_id,
        "event_type": event.event_type,
        "notes": event.notes,
        "created_at": event.created_at,
    }


@app.post("/repairs")
def create_repair(payload: RepairCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repair = Repair(**payload.model_dump())
    db.add(repair)
    db.commit()
    db.refresh(repair)
    db.add(MaintenanceHistory(asset_id=payload.asset_id, details=payload.description))
    db.commit()
    audit(db, "create", "repair", repair.id)
    return {
        "id": repair.id,
        "asset_id": repair.asset_id,
        "description": repair.description,
        "repair_cost": repair.repair_cost,
        "repaired_at": repair.repaired_at,
    }


@app.post("/lost-reports")
def create_lost_report(payload: LostReportCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    report = LostReport(**payload.model_dump())
    db.add(report)
    asset = db.query(Asset).filter(Asset.id == payload.asset_id).first()
    if asset:
        asset.status = "lost"
    db.commit()
    db.refresh(report)
    db.add(LifecycleEvent(asset_id=payload.asset_id, event_type="lost", notes=payload.reason))
    db.commit()
    audit(db, "create", "lost_report", report.id)
    return {
        "id": report.id,
        "asset_id": report.asset_id,
        "reported_by": report.reported_by,
        "reason": report.reason,
        "created_at": report.created_at,
    }


@app.post("/depreciation")
def update_depreciation(payload: DepreciationCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    years = max((datetime.utcnow() - asset.purchase_date).days / 365, 0)
    current_value = max(asset.purchase_cost * ((1 - payload.annual_rate) ** years), 0)
    record = (
        db.query(DepreciationRecord)
        .filter(DepreciationRecord.asset_id == payload.asset_id)
        .order_by(DepreciationRecord.id.desc())
        .first()
    )
    if record:
        record.annual_rate = payload.annual_rate
        record.current_value = current_value
        record.updated_at = datetime.utcnow()
    else:
        record = DepreciationRecord(asset_id=payload.asset_id, annual_rate=payload.annual_rate, current_value=current_value)
        db.add(record)
    db.commit()
    audit(db, "update", "depreciation", record.id)
    return {"asset_id": payload.asset_id, "current_value": current_value, "annual_rate": payload.annual_rate}


@app.get("/warranty/expiring")
def warranty_expiring(days: int = 60, db: Session = Depends(get_db), _=Depends(get_current_user)):
    deadline = datetime.utcnow().timestamp() + days * 24 * 3600
    assets = db.query(Asset).filter(Asset.warranty_expiry.isnot(None)).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "warranty_expiry": a.warranty_expiry,
            "status": a.status,
        }
        for a in assets
        if a.warranty_expiry and a.warranty_expiry.timestamp() <= deadline and a.warranty_expiry.timestamp() >= datetime.utcnow().timestamp()
    ]


@app.get("/audit-logs")
def list_audit_logs(db: Session = Depends(get_db), _=Depends(get_current_user)):
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()
    return [
        {
            "id": l.id,
            "action": l.action,
            "entity": l.entity,
            "entity_id": l.entity_id,
            "created_at": l.created_at,
        }
        for l in logs
    ]


@app.post("/ai/replacement-timeline")
def replacement_timeline(asset_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    age_years = max((datetime.utcnow() - asset.purchase_date).days / 365, 0)
    recommended_after = max(4 - age_years, 0)
    return {
        "asset_id": asset_id,
        "estimated_replacement_in_years": round(recommended_after, 2),
        "confidence": "medium",
    }


@app.get("/ai/unusual-movement")
def unusual_movement(db: Session = Depends(get_db), _=Depends(get_current_user)):
    suspect_assets = []
    rows = (
        db.query(AssetMovement.asset_id, func.count(func.distinct(AssetMovement.office_id)).label("office_count"))
        .group_by(AssetMovement.asset_id)
        .all()
    )
    for row in rows:
        if row.office_count >= 3:
            suspect_assets.append({"asset_id": row.asset_id, "risk": "high", "reason": "Moved across 3+ offices"})
    return suspect_assets


@app.post("/ai/procurement-recommendations")
def procurement_recommendations(db: Session = Depends(get_db), _=Depends(get_current_user)):
    categories = (
        db.query(Asset.category, func.count(Asset.id).label("count"), func.avg(Asset.purchase_cost).label("avg_cost"))
        .group_by(Asset.category)
        .all()
    )
    results = []
    for category, count, avg_cost in categories:
        if count < 3:
            reason = "Low inventory buffer"
            recommended = 5 - count
        else:
            reason = "Healthy inventory"
            recommended = 1
        rec = ProcurementRecommendation(category=category, recommended_count=max(recommended, 0), reason=reason)
        db.add(rec)
        results.append({"category": category, "recommended_count": rec.recommended_count, "reason": reason, "avg_cost": avg_cost})
    db.commit()
    return results


@app.get("/dashboard/analytics")
def dashboard_analytics(db: Session = Depends(get_db), _=Depends(get_current_user)):
    total_assets = db.query(func.count(Asset.id)).scalar() or 0
    total_cost = db.query(func.coalesce(func.sum(Asset.purchase_cost), 0)).scalar() or 0
    by_department = (
        db.query(Employee.department, func.count(Assignment.id))
        .join(Assignment, Assignment.employee_id == Employee.id, isouter=True)
        .group_by(Employee.department)
        .all()
    )
    maintenance_count = db.query(func.count(MaintenanceHistory.id)).scalar() or 0
    return {
        "total_assets": total_assets,
        "total_cost": total_cost,
        "department_usage": [{"department": d, "assignments": c} for d, c in by_department],
        "maintenance_events": maintenance_count,
    }


@app.get("/export/assets.pdf")
def export_assets_pdf(db: Session = Depends(get_db), _=Depends(get_current_user)):
    assets = db.query(Asset).all()
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Asset Inventory Report")
    pdf.drawString(72, 760, "Office Asset Intelligence - Asset Inventory")
    y = 730
    for asset in assets:
        line = f"{asset.id} | {asset.name} | {asset.category} | {asset.status} | ${asset.purchase_cost:.2f}"
        pdf.drawString(72, y, line[:95])
        y -= 20
        if y < 72:
            pdf.showPage()
            y = 760
    pdf.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=assets.pdf"})
