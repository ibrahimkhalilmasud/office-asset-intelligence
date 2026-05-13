from datetime import datetime

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class OfficeCreate(BaseModel):
    name: str
    location: str


class VendorCreate(BaseModel):
    name: str
    contact_email: str | None = None


class EmployeeCreate(BaseModel):
    name: str
    department: str


class AssetCreate(BaseModel):
    name: str
    category: str
    serial_number: str
    barcode: str
    office_id: int
    vendor_id: int | None = None
    purchase_cost: float = 0
    warranty_expiry: datetime | None = None


class AssignmentCreate(BaseModel):
    asset_id: int
    employee_id: int


class LifecycleEventCreate(BaseModel):
    asset_id: int
    event_type: str
    notes: str | None = None


class RepairCreate(BaseModel):
    asset_id: int
    description: str
    repair_cost: float = 0


class LostReportCreate(BaseModel):
    asset_id: int
    reported_by: str
    reason: str


class MovementScanCreate(BaseModel):
    barcode: str
    office_id: int


class ProcurementRecommendationCreate(BaseModel):
    category: str
    recommended_count: int
    reason: str


class DepreciationCreate(BaseModel):
    asset_id: int
    annual_rate: float


class MaintenanceHistoryCreate(BaseModel):
    asset_id: int
    details: str
