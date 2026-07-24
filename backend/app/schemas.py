from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

ROLES = {"admin", "factory_manager", "quality_engineer", "maintenance_engineer", "viewer"}


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class LocalRecoveryIn(BaseModel):
    email: EmailStr
    recovery_key: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)


class AdminPasswordResetIn(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    role: str
    active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = None
    active: bool | None = None


class FactoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    location: str = Field(default="Industrial Zone", max_length=180)
    timezone: str = Field(default="Asia/Dubai", max_length=80)
    target_oee: float = Field(default=85, ge=0, le=100)


class FactoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    location: str | None = Field(default=None, max_length=180)
    timezone: str | None = Field(default=None, max_length=80)
    target_oee: float | None = Field(default=None, ge=0, le=100)


class MachineCreate(BaseModel):
    factory_id: int = 1
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(min_length=2, max_length=120)
    machine_type: str = "CNC"
    manufacturer: str = "Unspecified"
    model_number: str = ""
    line_name: str = "Line A"
    age_years: float = Field(default=1, ge=0, le=80)
    operating_hours: float = Field(default=0, ge=0)
    tool_wear: float = Field(default=0, ge=0, le=300)
    rated_power_kw: float = Field(default=15, ge=0, le=10000)
    installation_date: str = ""
    notes: str = ""


class MachineUpdate(BaseModel):
    name: str | None = None
    machine_type: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    line_name: str | None = None
    status: str | None = None
    age_years: float | None = Field(default=None, ge=0, le=80)
    operating_hours: float | None = Field(default=None, ge=0)
    tool_wear: float | None = Field(default=None, ge=0, le=300)
    rated_power_kw: float | None = Field(default=None, ge=0, le=10000)
    installation_date: str | None = None
    notes: str | None = None
    archived: bool | None = None


class MachineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    factory_id: int
    code: str
    name: str
    machine_type: str
    manufacturer: str
    model_number: str
    line_name: str
    status: str
    age_years: float
    operating_hours: float
    tool_wear: float
    rated_power_kw: float
    installation_date: str
    notes: str
    archived: bool
    created_at: datetime
    updated_at: datetime


class SensorReadingIn(BaseModel):
    machine_id: str | int
    temperature: float = Field(ge=-40, le=250)
    vibration: float = Field(ge=0, le=20)
    pressure: float = Field(ge=0, le=500)
    rpm: float = Field(ge=0, le=30000)
    torque: float = Field(default=45, ge=0, le=5000)
    power: float = Field(ge=0, le=10000)
    operating_hours: float | None = Field(default=None, ge=0)
    tool_wear: float | None = Field(default=None, ge=0, le=300)
    source: str = "hardware"


class MaintenanceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    action: str = Field(min_length=2, max_length=220)
    priority: str = "medium"
    assigned_to: str = ""
    scheduled_for: str = ""
    cost_estimate: float = Field(default=0, ge=0)
    notes: str = ""


class MaintenanceUpdate(BaseModel):
    title: str | None = None
    action: str | None = None
    priority: str | None = None
    status: str | None = None
    assigned_to: str | None = None
    scheduled_for: str | None = None
    cost_estimate: float | None = Field(default=None, ge=0)
    notes: str | None = None


class ProductionCreate(BaseModel):
    factory_id: int = 1
    line_name: str = "Line A"
    product_name: str = "Industrial Component"
    planned: int = Field(default=50, ge=0)
    produced: int = Field(ge=0)
    rejected: int = Field(default=0, ge=0)
    downtime_minutes: float = Field(default=0, ge=0)
    runtime_minutes: float = Field(default=60, ge=0.1)
    ideal_cycle_seconds: float = Field(default=60, ge=0.1)
    shift: str = "A"


class AssistantQuery(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    conversation_id: int | None = None
    locale: str = Field(default="en", pattern="^(en|ar)$")


class DeviceCommandIn(BaseModel):
    machine_id: str | int
    command: str
    payload: dict = Field(default_factory=dict)


class SimulationConfigIn(BaseModel):
    speed_seconds: float = Field(default=3, ge=0.5, le=60)
    degradation_rate: float = Field(default=1.0, ge=0.1, le=5)
    anomaly_frequency: float = Field(default=0.08, ge=0, le=0.8)
    production_rate: int = Field(default=52, ge=5, le=500)


class ReportGenerateIn(BaseModel):
    report_type: str = "executive"
    start_date: str = ""
    end_date: str = ""


class SettingUpdateIn(BaseModel):
    value: dict
    description: str = ""
