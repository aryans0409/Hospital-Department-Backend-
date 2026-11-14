PATIENTS_TABLE = """
CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    dob TEXT,
    gender TEXT,
    admission_date TEXT,
    discharge_date TEXT,
    diagnosis TEXT,
    ward TEXT,
    bed TEXT,
    attending_physician TEXT,
    contact_phone TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    status TEXT,
    deleted_at TEXT NULL
)
"""

DOCTORS_TABLE = """
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    title TEXT,
    specialty TEXT,
    department TEXT,
    phone TEXT,
    email TEXT,
    office TEXT,
    patient_ids TEXT,
    nurse_ids TEXT
)
"""

NURSES_TABLE = """
CREATE TABLE IF NOT EXISTS nurses (
    nurse_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    ward_assignment TEXT,
    shift TEXT,
    phone TEXT,
    email TEXT,
    assigned_doctor_id TEXT,
    assigned_patient_ids TEXT,
    supervisor_staff_id TEXT
)
"""

STAFF_TABLE = """
CREATE TABLE IF NOT EXISTS staff (
    staff_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    role TEXT,
    department TEXT,
    phone TEXT,
    email TEXT,
    assigned_ward TEXT,
    supports_doctor_ids TEXT,
    supports_nurse_ids TEXT
)
"""

USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
"""

from pydantic import BaseModel
from typing import Optional, List

class PatientCreate(BaseModel):
    patient_id: str
    first_name: str
    last_name: str
    dob: str
    gender: str
    admission_date: str
    discharge_date: Optional[str] = None
    diagnosis: str
    ward: str
    bed: str
    attending_physician: str
    contact_phone: str
    emergency_contact_name: str
    emergency_contact_phone: str
    status: str

class PatientUpdate(BaseModel):
    first_name: str
    last_name: str
    diagnosis: str
    status: str
    discharge_date: Optional[str] = None

class DoctorCreate(BaseModel):
    doctor_id: str
    first_name: str
    last_name: str
    title: str
    specialty: str
    department: str
    phone: str
    email: str
    office: str
    patient_ids: Optional[List[str]] = []
    nurse_ids: Optional[List[str]] = []

class DoctorUpdate(BaseModel):
    first_name: str
    last_name: str
    title: str
    specialty: str
    department: str
    phone: str
    email: str
    office: str
    patient_ids: Optional[List[str]] = []
    nurse_ids: Optional[List[str]] = []

class NurseCreate(BaseModel):
    nurse_id: str
    first_name: str
    last_name: str
    ward_assignment: str
    shift: str
    phone: str
    email: str
    assigned_doctor_id: Optional[str] = None
    assigned_patient_ids: Optional[List[str]] = []
    supervisor_staff_id: Optional[str] = None

class NurseUpdate(BaseModel):
    first_name: str
    last_name: str
    ward_assignment: str
    shift: str
    phone: str
    email: str
    assigned_doctor_id: Optional[str] = None
    assigned_patient_ids: Optional[List[str]] = []
    supervisor_staff_id: Optional[str] = None

class StaffCreate(BaseModel):
    staff_id: str
    first_name: str
    last_name: str
    role: str
    department: str
    phone: str
    email: str
    assigned_ward: Optional[str] = None
    supports_doctor_ids: Optional[List[str]] = []
    supports_nurse_ids: Optional[List[str]] = []

class StaffUpdate(BaseModel):
    first_name: str
    last_name: str
    role: str
    department: str
    phone: str
    email: str
    assigned_ward: Optional[str] = None
    supports_doctor_ids: Optional[List[str]] = []
    supports_nurse_ids: Optional[List[str]] = []