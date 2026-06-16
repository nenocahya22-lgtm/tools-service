import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict
from core.models import CheckInRecord, DeviceInfo, BatteryHealth


DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "service_hp.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    """Inisialisasi tabel shared. Tabel utama dibuat oleh app.py.
    Core module juga buat pelanggan (shared) + ampere_rules & adb_logs."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabel pelanggan — shared antara CLI dan Web
    cursor.execute("""CREATE TABLE IF NOT EXISTS pelanggan (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT NOT NULL, no_hp TEXT DEFAULT '',
        device_model TEXT NOT NULL, chipset TEXT DEFAULT '', platform TEXT DEFAULT 'android',
        imei TEXT DEFAULT '', serial_device TEXT DEFAULT '', keluhan TEXT NOT NULL,
        ampere_reading REAL DEFAULT 0.0, voltage_reading REAL DEFAULT 0.0,
        kondisi TEXT DEFAULT 'mati_total', severity TEXT DEFAULT 'unknown',
        diagnosis TEXT DEFAULT '', rekomendasi TEXT DEFAULT '',
        service_status TEXT DEFAULT 'check_in', teknisi TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    # Tambah kolom jika belum ada (migrasi DB lama)
    for col in ["service_status TEXT DEFAULT 'check_in'", "teknisi TEXT DEFAULT ''"]:
        try:
            cursor.execute(f"ALTER TABLE pelanggan ADD COLUMN {col}")
        except:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS adb_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            serial          TEXT DEFAULT '',
            model           TEXT DEFAULT '',
            android_version TEXT DEFAULT '',
            bootloader_status TEXT DEFAULT 'unknown',
            adb_connected   INTEGER DEFAULT 0,
            fastboot_connected INTEGER DEFAULT 0,
            battery_level   INTEGER DEFAULT 0,
            detected_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS battery_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            pelanggan_id    INTEGER,
            current_capacity_mah REAL DEFAULT 0,
            design_capacity_mah  REAL DEFAULT 0,
            health_percent       REAL DEFAULT 0,
            cycle_count     INTEGER DEFAULT 0,
            voltage         REAL DEFAULT 0,
            temperature     REAL DEFAULT 0,
            status_text     TEXT DEFAULT '',
            created_at      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ampere_rules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            min_ampere      REAL NOT NULL,
            max_ampere      REAL NOT NULL,
            condition_note  TEXT NOT NULL,
            diagnosis       TEXT NOT NULL,
            severity        TEXT NOT NULL DEFAULT 'medium',
            recommendation  TEXT NOT NULL,
            priority        INTEGER DEFAULT 0
        )
    """)

    # Indexes
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_created ON pelanggan(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_status ON pelanggan(service_status)",
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_model ON pelanggan(device_model)",
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_imei ON pelanggan(imei)",
    ]:
        try:
            cursor.execute(idx_sql)
        except:
            pass

    conn.commit()
    conn.close()
    _seed_ampere_rules()


def _seed_ampere_rules():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ampere_rules")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return

    rules = [
        (0.000, 0.005, "mati_total",
         "Tidak ada sirkuit aktif — kemungkinan putus total di jalur BATT+ atau konektor baterai rusak",
         "high",
         "Periksa konektor baterai, ukur tegangan diode mode pada jalur BATT+, periksa jalur VBUS dan fleksibel cas",
         10),
        (0.010, 0.040, "mati_total",
         "Terindikasi Software Brick atau kerusakan IC eMMC/UFS/CPU — arus hanya cukup untuk RTC",
         "medium",
         "Coba masuk Mode EDL / Download Mode / Fastboot. Jika tidak bisa, indikasi eMMC/UFS korup atau IC CPU short rendah",
         9),
        (0.010, 0.040, "tekan_power",
         "HP on tapi arus sangat rendah — kemungkinan boot loop atau crash di kernel awal",
         "medium",
         "Coba masuk Recovery Mode (Vol Up + Power). Jika tidak bisa, indikasikan kerusakan software atau IC RAM",
         8),
        (0.050, 0.200, "mati_total",
         "Arus rendah — kemungkinan short parsial di jalur sinyal atau IC power supply tidak bekerja optimal",
         "medium",
         "Periksa tegangan keluaran PMIC/PMU, ukur di inductor sekitar PMIC, thermal detection untuk cari komponen panas",
         7),
        (0.050, 0.200, "tekan_power",
         "HP boot loop — arus naik turun, indikasi short di jalur peripheral atau baterai drop",
         "low",
         "Lepaskan fleksibel peripheral satu per satu (LCD, camera, speaker), lihat apakah arus normal kembali",
         7),
        (0.500, 1.000, "mati_total",
         "Arus tinggi pasif — kemungkinan short di komponen pemakaian daya sedang (PA, RF, WiFi IC)",
         "medium",
         "Gunakan thermal imaging atau sentuh komponen satu per satu untuk cari yang panas. Periksa IC PA/RF",
         6),
        (1.000, 9.999, "mati_total",
         "SHORT BESAR terdeteksi — arus tembus >1A di jalur utama VCC_MAIN / VBAT tanpa tekan power",
         "critical",
         "MATIKAN SEGERA power supply! Cari komponen panas dengan thermal cam atau alkohol test. Ukur resistansi VCC_MAIN ke GND",
         10),
        (1.000, 9.999, "tekan_power",
         "Arus sangat tinggi saat power ditekan — kemungkinan short di komponen switching atau IC power utama",
         "high",
         "Periksa IC Power/PMIC, kapasitor di jalur VCC_MAIN, kurangi beban dengan lepaskan peripheral",
         9),
    ]

    cursor.executemany("""
        INSERT INTO ampere_rules
            (min_ampere, max_ampere, condition_note, diagnosis, severity, recommendation, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rules)

    conn.commit()
    conn.close()


def save_check_in(record: CheckInRecord) -> int:
    """Simpan data check-in ke tabel pelanggan (shared dengan app.py)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pelanggan
            (nama, no_hp, device_model, imei, keluhan,
             ampere_reading, voltage_reading, kondisi,
             diagnosis, severity, rekomendasi, service_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record.customer_name,
        getattr(record, 'no_hp', ''),
        record.device_model,
        record.imei,
        record.symptoms,
        record.ampere_reading,
        record.voltage_reading,
        record.condition_note or "mati_total",
        record.diagnosis_result,
        record.severity,
        record.recommendation,
        getattr(record, 'service_status', 'check_in'),
    ))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_all_check_ins(limit: int = 20) -> List[Dict]:
    """Ambil data check-in dari tabel pelanggan."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nama as customer_name, no_hp, device_model, imei,
               keluhan as symptoms, ampere_reading, voltage_reading,
               kondisi as condition_note, diagnosis as diagnosis_result,
               severity, rekomendasi as recommendation, service_status,
               created_at
        FROM pelanggan ORDER BY created_at DESC LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def search_check_ins(keyword: str, limit: int = 20) -> List[Dict]:
    """Cari data pelanggan berdasarkan nama/IMEI/model HP."""
    conn = get_connection()
    cursor = conn.cursor()
    like = f"%{keyword}%"
    cursor.execute("""
        SELECT id, nama as customer_name, no_hp, device_model, imei,
               keluhan as symptoms, ampere_reading, voltage_reading,
               kondisi as condition_note, diagnosis as diagnosis_result,
               severity, rekomendasi as recommendation, service_status,
               created_at
        FROM pelanggan
        WHERE nama LIKE ? OR imei LIKE ? OR device_model LIKE ? OR no_hp LIKE ?
        ORDER BY created_at DESC LIMIT ?
    """, (like, like, like, like, limit))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def update_check_in(record_id: int, **kwargs) -> bool:
    """Update field tertentu pada record pelanggan. kwargs: column=value."""
    allowed = {'nama','no_hp','device_model','imei','keluhan','service_status','teknisi'}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [record_id]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE pelanggan SET {set_clause} WHERE id = ?", values)
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def delete_check_in(record_id: int) -> bool:
    """Hapus record pelanggan berdasarkan ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pelanggan WHERE id = ?", (record_id,))
    ok = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def save_adb_log(device: DeviceInfo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO adb_logs
            (serial, model, android_version, bootloader_status,
             adb_connected, fastboot_connected, battery_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        device.serial,
        device.model,
        device.android_version,
        device.bootloader_status,
        int(device.adb_connected),
        int(device.fastboot_connected),
        device.battery_level,
    ))
    conn.commit()
    conn.close()


def save_battery_log(pelanggan_id: int, battery: BatteryHealth):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO battery_logs
            (pelanggan_id, current_capacity_mah, design_capacity_mah,
             health_percent, cycle_count, voltage, temperature, status_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pelanggan_id,
        battery.current_capacity_mah,
        battery.design_capacity_mah,
        battery.health_percent,
        battery.cycle_count,
        battery.voltage,
        battery.temperature,
        battery.status_text,
    ))
    conn.commit()
    conn.close()


def get_ampere_rule(ampere: float, condition: str) -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM ampere_rules
        WHERE ? >= min_ampere AND ? <= max_ampere
          AND ? LIKE '%' || condition_note || '%'
        ORDER BY priority DESC
        LIMIT 1
    """, (ampere, ampere, condition))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {
        "diagnosis": "Pola arus tidak dikenali dalam basis pengetahuan",
        "severity": "low",
        "recommendation": "Periksa secara manual menggunakan multimeter dan thermal camera",
    }
