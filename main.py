from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import sqlite3
import json
import jwt
import datetime
from datetime import timezone
import hashlib
from typing import Any, Union, List

from models import (
    PATIENTS_TABLE,
    DOCTORS_TABLE,
    NURSES_TABLE,
    STAFF_TABLE,
    USERS_TABLE,
    PatientCreate,
    PatientUpdate,
    DoctorCreate,
    DoctorUpdate,
    NurseCreate,
    NurseUpdate,
    StaffCreate,
    StaffUpdate
)

# Unified JSON source file
HOSPITAL_JSON_FILE = "hospital.json"

DB_FILE = "hospital.db"
PATIENTS_DB_FILE = DB_FILE
DOCTORS_DB_FILE = DB_FILE
NURSES_DB_FILE = DB_FILE
STAFF_DB_FILE = DB_FILE

app = FastAPI()

JWT_SECRET = "hospital-super-secret-key-xyz-789"
JWT_ALGORITHM = "HS256"

def create_access_token(username: str, expires_in_minutes: int = 60) -> str:
    expire = datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=expires_in_minutes)
    payload = {
        "sub": username,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None

@app.middleware("http")
async def jwt_auth_middleware(request: Request, call_next):
    path = request.url.path.rstrip("/")
    if path == "":
        path = "/"
    if path in ["/", "/about", "/login", "/decode", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Missing or invalid authorization credentials"}
        )

    token = auth_header.split(" ")[1]
    username = verify_token(token)
    if not username:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or expired token"}
        )

    # Attach username to request state
    request.state.username = username
    return await call_next(request)

class LoginPayload(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(payload: LoginPayload):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    hashed_password = hashlib.sha256(payload.password.encode()).hexdigest()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (payload.username, hashed_password))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    token = create_access_token(payload.username)
    return {"access_token": token, "token_type": "bearer"}

class DecodePayload(BaseModel):
    token: str

@app.post("/decode")
def decode(payload: DecodePayload):
    try:
        decoded = jwt.decode(payload.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "valid": True,
            "username": decoded.get("sub"),
            "expires_at": decoded.get("exp"),
            "payload": decoded
        }
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token has expired"}
    except jwt.PyJWTError as e:
        return {"valid": False, "error": f"Invalid token: {e}"}


def load_patients_from_json():
        return load_json_to_db(
            "patients",
            PATIENTS_DB_FILE,
            """
            INSERT OR REPLACE INTO patients (
                patient_id, first_name, last_name, dob, gender,
                admission_date, discharge_date, diagnosis, ward, bed,
                attending_physician, contact_phone,
                emergency_contact_name, emergency_contact_phone, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            lambda p: (
                p.get("patient_id"),
                p.get("first_name"),
                p.get("last_name"),
                p.get("dob"),
                p.get("gender"),
                p.get("admission_date"),
                p.get("discharge_date"),
                p.get("diagnosis"),
                p.get("ward"),
                p.get("bed"),
                p.get("attending_physician"),
                p.get("contact_phone"),
                p.get("emergency_contact_name"),
                p.get("emergency_contact_phone"),
                p.get("status"),
            ),
        )


def load_json_to_db(json_key, db_file, insert_sql, row_mapper):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    with open(HOSPITAL_JSON_FILE, "r") as file:
        full_data = json.load(file)

    records = full_data.get(json_key, [])
    data = [row_mapper(record) for record in records]
    cursor.executemany(insert_sql, data)
    conn.commit()
    conn.close()
    return len(data)


def load_doctors_from_json():
    return load_json_to_db(
        "doctors",
        DOCTORS_DB_FILE,
        """
        INSERT OR REPLACE INTO doctors (
            doctor_id, first_name, last_name, title, specialty,
            department, phone, email, office, patient_ids, nurse_ids
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        lambda d: (
            d.get("doctor_id"),
            d.get("first_name"),
            d.get("last_name"),
            d.get("title"),
            d.get("specialty"),
            d.get("department"),
            d.get("phone"),
            d.get("email"),
            d.get("office"),
            json.dumps(d.get("patient_ids", [])),
            json.dumps(d.get("nurse_ids", [])),
        ),
    )


def load_nurses_from_json():
    return load_json_to_db(
        "nurses",
        NURSES_DB_FILE,
        """
        INSERT OR REPLACE INTO nurses (
            nurse_id, first_name, last_name, ward_assignment, shift,
            phone, email, assigned_doctor_id, assigned_patient_ids, supervisor_staff_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        lambda n: (
            n.get("nurse_id"),
            n.get("first_name"),
            n.get("last_name"),
            n.get("ward_assignment"),
            n.get("shift"),
            n.get("phone"),
            n.get("email"),
            n.get("assigned_doctor_id"),
            json.dumps(n.get("assigned_patient_ids", [])),
            n.get("supervisor_staff_id"),
        ),
    )


def load_staff_from_json():
    return load_json_to_db(
        "staff",
        STAFF_DB_FILE,
        """
        INSERT OR REPLACE INTO staff (
            staff_id, first_name, last_name, role, department,
            phone, email, assigned_ward, supports_doctor_ids, supports_nurse_ids
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        lambda s: (
            s.get("staff_id"),
            s.get("first_name"),
            s.get("last_name"),
            s.get("role"),
            s.get("department"),
            s.get("phone"),
            s.get("email"),
            s.get("assigned_ward"),
            json.dumps(s.get("supports_doctor_ids", [])),
            json.dumps(s.get("supports_nurse_ids", [])),
        ),
    )

@app.get("/")
def hello():
    return {"message": "Patient Management System API"}

@app.get("/about")
def about():
    return {"message": "This is a simple API for managing patients in a hospital."}

@app.get("/patient/{patient_id}")
def get_patient(patient_id: str):
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE patient_id = ? AND deleted_at IS NULL", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"message": "Patient not found"}
    
@app.get("/view")
def view():
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE deleted_at IS NULL")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/add")
def add_patient(patient: Any = Body(...)):
    if isinstance(patient, dict) and patient.get("load_from_json"):
        try:
            count = load_patients_from_json()
            return {"message": f"Loaded {count} patients from hospital.json successfully"}
        except Exception as e:
            return {"error": str(e)}

    try:
        if isinstance(patient, list):
            patients_list = [item.dict() if hasattr(item, "dict") else (PatientCreate(**item).dict() if isinstance(item, dict) else item) for item in patient]
        else:
            patients_list = [patient.dict() if hasattr(patient, "dict") else (PatientCreate(**patient).dict() if isinstance(patient, dict) else patient)]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    conn = sqlite3.connect(PATIENTS_DB_FILE)
    cursor = conn.cursor()
    try:
        count = 0
        for p in patients_list:
            cursor.execute("""INSERT INTO patients (patient_id, first_name, last_name, dob, gender, admission_date, discharge_date, diagnosis, ward, bed, attending_physician, contact_phone, emergency_contact_name, emergency_contact_phone, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (p.get("patient_id"), p.get("first_name"), p.get("last_name"), p.get("dob"), p.get("gender"), p.get("admission_date"), p.get("discharge_date"), p.get("diagnosis"), p.get("ward"), p.get("bed"), p.get("attending_physician"), p.get("contact_phone"), p.get("emergency_contact_name"), p.get("emergency_contact_phone"), p.get("status")))
            count += 1
        
        conn.commit()
        conn.close()
        return {"message": f"Added {count} patient(s) successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.get("/doctors")
def list_doctors():
    conn = sqlite3.connect(DOCTORS_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/doctor/{doctor_id}")
def get_doctor(doctor_id: str):
    conn = sqlite3.connect(DOCTORS_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"message": "Doctor not found"}


@app.post("/doctors")
def add_doctor(doctor: Any = Body(...)):
    try:
        if isinstance(doctor, list):
            doctors_list = [item.dict() if hasattr(item, "dict") else (DoctorCreate(**item).dict() if isinstance(item, dict) else item) for item in doctor]
        else:
            doctors_list = [doctor.dict() if hasattr(doctor, "dict") else (DoctorCreate(**doctor).dict() if isinstance(doctor, dict) else doctor)]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    conn = sqlite3.connect(DOCTORS_DB_FILE)
    cursor = conn.cursor()
    try:
        count = 0
        for d in doctors_list:
            cursor.execute(
                """INSERT INTO doctors (doctor_id, first_name, last_name, title, specialty, department, phone, email, office, patient_ids, nurse_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    d.get("doctor_id"),
                    d.get("first_name"),
                    d.get("last_name"),
                    d.get("title"),
                    d.get("specialty"),
                    d.get("department"),
                    d.get("phone"),
                    d.get("email"),
                    d.get("office"),
                    json.dumps(d.get("patient_ids", [])),
                    json.dumps(d.get("nurse_ids", [])),
                ),
            )
            count += 1
        conn.commit()
        conn.close()
        return {"message": f"Added {count} doctor(s) successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.put("/doctor/{doctor_id}")
def update_doctor(doctor: DoctorUpdate, doctor_id: str):
    conn = sqlite3.connect(DOCTORS_DB_FILE)
    cursor = conn.cursor()
    try:
        d = doctor.dict()
        cursor.execute(
            "UPDATE doctors SET first_name = ?, last_name = ?, title = ?, specialty = ?, department = ?, phone = ?, email = ?, office = ?, patient_ids = ?, nurse_ids = ? WHERE doctor_id = ?",
            (
                d.get("first_name"),
                d.get("last_name"),
                d.get("title"),
                d.get("specialty"),
                d.get("department"),
                d.get("phone"),
                d.get("email"),
                d.get("office"),
                json.dumps(d.get("patient_ids", [])),
                json.dumps(d.get("nurse_ids", [])),
                doctor_id,
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Doctor not found"}
        conn.close()
        return {"message": "Doctor updated successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.delete("/doctor/{doctor_id}")
def delete_doctor(doctor_id: str):
    conn = sqlite3.connect(DOCTORS_DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM doctors WHERE doctor_id = ?", (doctor_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Doctor not found"}
        conn.close()
        return {"message": "Doctor deleted successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.get("/nurses")
def list_nurses():
    conn = sqlite3.connect(NURSES_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nurses")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/nurse/{nurse_id}")
def get_nurse(nurse_id: str):
    conn = sqlite3.connect(NURSES_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nurses WHERE nurse_id = ?", (nurse_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"message": "Nurse not found"}


@app.post("/nurses")
def add_nurse(nurse: Any = Body(...)):
    try:
        if isinstance(nurse, list):
            nurses_list = [item.dict() if hasattr(item, "dict") else (NurseCreate(**item).dict() if isinstance(item, dict) else item) for item in nurse]
        else:
            nurses_list = [nurse.dict() if hasattr(nurse, "dict") else (NurseCreate(**nurse).dict() if isinstance(nurse, dict) else nurse)]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    conn = sqlite3.connect(NURSES_DB_FILE)
    cursor = conn.cursor()
    try:
        count = 0
        for n in nurses_list:
            cursor.execute(
                """INSERT INTO nurses (nurse_id, first_name, last_name, ward_assignment, shift, phone, email, assigned_doctor_id, assigned_patient_ids, supervisor_staff_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    n.get("nurse_id"),
                    n.get("first_name"),
                    n.get("last_name"),
                    n.get("ward_assignment"),
                    n.get("shift"),
                    n.get("phone"),
                    n.get("email"),
                    n.get("assigned_doctor_id"),
                    json.dumps(n.get("assigned_patient_ids", [])),
                    n.get("supervisor_staff_id"),
                ),
            )
            count += 1
        conn.commit()
        conn.close()
        return {"message": f"Added {count} nurse(s) successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.put("/nurse/{nurse_id}")
def update_nurse(nurse: NurseUpdate, nurse_id: str):
    conn = sqlite3.connect(NURSES_DB_FILE)
    cursor = conn.cursor()
    try:
        n = nurse.dict()
        cursor.execute(
            "UPDATE nurses SET first_name = ?, last_name = ?, ward_assignment = ?, shift = ?, phone = ?, email = ?, assigned_doctor_id = ?, assigned_patient_ids = ?, supervisor_staff_id = ? WHERE nurse_id = ?",
            (
                n.get("first_name"),
                n.get("last_name"),
                n.get("ward_assignment"),
                n.get("shift"),
                n.get("phone"),
                n.get("email"),
                n.get("assigned_doctor_id"),
                json.dumps(n.get("assigned_patient_ids", [])),
                n.get("supervisor_staff_id"),
                nurse_id,
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Nurse not found"}
        conn.close()
        return {"message": "Nurse updated successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.delete("/nurse/{nurse_id}")
def delete_nurse(nurse_id: str):
    conn = sqlite3.connect(NURSES_DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM nurses WHERE nurse_id = ?", (nurse_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Nurse not found"}
        conn.close()
        return {"message": "Nurse deleted successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.get("/staff")
def list_staff():
    conn = sqlite3.connect(STAFF_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/staff/{staff_id}")
def get_staff(staff_id: str):
    conn = sqlite3.connect(STAFF_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff WHERE staff_id = ?", (staff_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"message": "Staff member not found"}


@app.post("/staff")
def add_staff(member: Any = Body(...)):
    try:
        if isinstance(member, list):
            staff_list = [item.dict() if hasattr(item, "dict") else (StaffCreate(**item).dict() if isinstance(item, dict) else item) for item in member]
        else:
            staff_list = [member.dict() if hasattr(member, "dict") else (StaffCreate(**member).dict() if isinstance(member, dict) else member)]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    conn = sqlite3.connect(STAFF_DB_FILE)
    cursor = conn.cursor()
    try:
        count = 0
        for s in staff_list:
            cursor.execute(
                """INSERT INTO staff (staff_id, first_name, last_name, role, department, phone, email, assigned_ward, supports_doctor_ids, supports_nurse_ids) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    s.get("staff_id"),
                    s.get("first_name"),
                    s.get("last_name"),
                    s.get("role"),
                    s.get("department"),
                    s.get("phone"),
                    s.get("email"),
                    s.get("assigned_ward"),
                    json.dumps(s.get("supports_doctor_ids", [])),
                    json.dumps(s.get("supports_nurse_ids", [])),
                ),
            )
            count += 1
        conn.commit()
        conn.close()
        return {"message": f"Added {count} staff member(s) successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.put("/staff/{staff_id}")
def update_staff(member: StaffUpdate, staff_id: str):
    conn = sqlite3.connect(STAFF_DB_FILE)
    cursor = conn.cursor()
    try:
        m = member.dict()
        cursor.execute(
            "UPDATE staff SET first_name = ?, last_name = ?, role = ?, department = ?, phone = ?, email = ?, assigned_ward = ?, supports_doctor_ids = ?, supports_nurse_ids = ? WHERE staff_id = ?",
            (
                m.get("first_name"),
                m.get("last_name"),
                m.get("role"),
                m.get("department"),
                m.get("phone"),
                m.get("email"),
                m.get("assigned_ward"),
                json.dumps(m.get("supports_doctor_ids", [])),
                json.dumps(m.get("supports_nurse_ids", [])),
                staff_id,
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Staff member not found"}
        conn.close()
        return {"message": "Staff updated successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.delete("/staff/{staff_id}")
def delete_staff(staff_id: str):
    conn = sqlite3.connect(STAFF_DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM staff WHERE staff_id = ?", (staff_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Staff member not found"}
        conn.close()
        return {"message": "Staff deleted successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}


@app.post("/import-json")
def import_json():
    """Import all patient records from hospital.json into the SQLite DB in bulk.

    Uses `load_patients_from_json()` which performs an INSERT OR REPLACE operation.
    """
    try:
        count = load_patients_from_json()
        return {"message": f"Imported {count} patients from hospital.json"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/import-all")
def import_all_json():
    """Import patients, doctors, nurses, and staff sections from hospital.json into the database."""
    try:
        patient_count = load_patients_from_json()
        doctor_count = load_doctors_from_json()
        nurse_count = load_nurses_from_json()
        staff_count = load_staff_from_json()
        return {
            "message": "Imported all JSON sections successfully from hospital.json",
            "counts": {
                "patients": patient_count,
                "doctors": doctor_count,
                "nurses": nurse_count,
                "staff": staff_count,
            },
        }
    except Exception as e:
        return {"error": str(e)}


@app.put("/update/{patient_id}")
def update_patient(patient: PatientUpdate, patient_id: str):
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    cursor = conn.cursor()
    try:
        p = patient.dict()
        cursor.execute("UPDATE patients SET first_name = ?, last_name = ?, diagnosis = ?, status = ?, discharge_date = ? WHERE patient_id = ? AND deleted_at IS NULL", (p.get("first_name"), p.get("last_name"), p.get("diagnosis"), p.get("status"), p.get("discharge_date"), patient_id))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Patient not found or already deleted"}
        conn.close()
        return {"message": "Patient updated successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}
        
        
@app.delete("/delete/{patient_id}")
def delete_patient(patient_id: str):
    """Soft delete: mark patient as deleted with timestamp."""
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    cursor = conn.cursor()
    try:
        from datetime import datetime
        deleted_at = datetime.utcnow().isoformat()
        cursor.execute("UPDATE patients SET deleted_at = ? WHERE patient_id = ? AND deleted_at IS NULL", (deleted_at, patient_id))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Patient not found or already deleted"}
        conn.close()
        return {"message": "Patient soft deleted successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}

@app.get("/deleted")
def view_deleted():
    """View all soft-deleted patients."""
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients WHERE deleted_at IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.put("/recover/{patient_id}")
def recover_patient(patient_id: str):
    """Recover a soft-deleted patient."""
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE patients SET deleted_at = NULL WHERE patient_id = ? AND deleted_at IS NOT NULL", (patient_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Patient not found or not deleted"}
        conn.close()
        return {"message": "Patient recovered successfully"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}

@app.delete("/permanent-delete/{patient_id}")
def permanent_delete_patient(patient_id: str):
    """Permanently delete a soft-deleted patient from DB."""
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM patients WHERE patient_id = ? AND deleted_at IS NOT NULL", (patient_id,))
        conn.commit()
        if cursor.rowcount == 0:
            conn.close()
            return {"message": "Patient not found or not soft-deleted"}
        conn.close()
        return {"message": "Patient permanently deleted"}
    except Exception as e:
        conn.close()
        return {"error": str(e)}
    
def init_db():

    # Patients DB
    conn = sqlite3.connect(PATIENTS_DB_FILE)
    cursor = conn.cursor()
    cursor.execute(PATIENTS_TABLE)

    try:
        cursor.execute(
            "ALTER TABLE patients ADD COLUMN deleted_at TEXT NULL"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

    # Doctors DB
    conn = sqlite3.connect(DOCTORS_DB_FILE)
    cursor = conn.cursor()
    cursor.execute(DOCTORS_TABLE)
    conn.commit()
    conn.close()

    # Nurses DB
    conn = sqlite3.connect(NURSES_DB_FILE)
    cursor = conn.cursor()
    cursor.execute(NURSES_TABLE)
    conn.commit()
    conn.close()

    # Staff DB
    conn = sqlite3.connect(STAFF_DB_FILE)
    cursor = conn.cursor()
    cursor.execute(STAFF_TABLE)
    conn.commit()
    conn.close()

    # Users Table
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(USERS_TABLE)
    # Seed default user if not exists
    cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", hashed_password))
    conn.commit()
    conn.close()
    
@app.on_event("startup")
def startup():
    init_db()    