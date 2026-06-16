"""
app.py — Smart Service HP Workstation v4.0
Single-File Streamlit Application — Cross-Platform Multi-OS
Semua fungsi bekerja riil dengan interaksi sistem via subprocess dan SQLite.
Tidak ada data dummy. Setiap modul memiliki kecerdasan otonom.

Jalankan:  streamlit run app.py
"""

import streamlit as st
import sqlite3
import subprocess
import shutil
import os
import re
import zipfile
import time
from datetime import datetime
from typing import Tuple
from pathlib import Path

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    from core.hardware_diagnosis import (
        diagnose_usb_flapping, diagnose_emmc, diagnose_ram,
        diagnose_wifi_bt, diagnose_baseband, diagnose_all, generate_diagnosis_report
    )
    HAS_HW_DIAG = True
except ImportError:
    HAS_HW_DIAG = False

st.set_page_config(
    page_title="Smart Service HP Workstation v4",
    page_icon="\U0001f527",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = str(BASE_DIR / "service_hp.db")
ZIP_NAME = "SmartServiceHP.zip"
ZIP_PATH = str(BASE_DIR / ZIP_NAME)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS pelanggan (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT NOT NULL, no_hp TEXT DEFAULT '',
        device_model TEXT NOT NULL, chipset TEXT DEFAULT '', platform TEXT DEFAULT 'android',
        imei TEXT DEFAULT '', serial_device TEXT DEFAULT '', keluhan TEXT NOT NULL,
        ampere_reading REAL DEFAULT 0.0, voltage_reading REAL DEFAULT 0.0,
        kondisi TEXT DEFAULT 'mati_total', severity TEXT DEFAULT 'unknown',
        diagnosis TEXT DEFAULT '', rekomendasi TEXT DEFAULT '',
        service_status TEXT DEFAULT 'check_in', teknisi TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    # Tambah kolom service_status jika belum ada (migrasi DB lama)
    try:
        c.execute("ALTER TABLE pelanggan ADD COLUMN service_status TEXT DEFAULT 'check_in'")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE pelanggan ADD COLUMN teknisi TEXT DEFAULT ''")
    except Exception:
        pass

    c.execute("""CREATE TABLE IF NOT EXISTS inventory_sparepart (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT NOT NULL,
        kategori TEXT NOT NULL DEFAULT 'other', sku TEXT UNIQUE, stock INTEGER NOT NULL DEFAULT 0,
        harga_beli REAL NOT NULL DEFAULT 0, harga_jual REAL NOT NULL DEFAULT 0,
        kompatibel TEXT DEFAULT '', min_stock INTEGER DEFAULT 5,
        terjual_bulan_ini INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS log_service (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pelanggan_id INTEGER REFERENCES pelanggan(id),
        inventory_id INTEGER REFERENCES inventory_sparepart(id),
        tipe_service TEXT NOT NULL DEFAULT 'software', status TEXT NOT NULL DEFAULT 'pending',
        biaya_jasa REAL DEFAULT 0, biaya_sparepart REAL DEFAULT 0, total_biaya REAL DEFAULT 0,
        teknisi_note TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')), completed_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS security_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pelanggan_id INTEGER REFERENCES pelanggan(id),
        device_model TEXT NOT NULL, platform TEXT DEFAULT 'android', chipset TEXT DEFAULT '',
        serial_device TEXT DEFAULT '', udid TEXT DEFAULT '',
        frp_checked INTEGER DEFAULT 0, activation_lock INTEGER DEFAULT 0,
        backup_checked INTEGER DEFAULT 0, arb_level INTEGER DEFAULT 0,
        arb_warning TEXT DEFAULT '', is_safe INTEGER DEFAULT 0,
        teknisi_note TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS battery_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pelanggan_id INTEGER REFERENCES pelanggan(id),
        platform TEXT DEFAULT 'android', level INTEGER DEFAULT 0,
        current_mah REAL DEFAULT 0, design_mah REAL DEFAULT 0, health_pct REAL DEFAULT 0,
        voltage REAL DEFAULT 0, temperature REAL DEFAULT 0, cycle_count INTEGER DEFAULT 0,
        current_ua INTEGER DEFAULT 0, usb_online INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS testpoint_guides (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chipset_brand TEXT NOT NULL,
        chipset_model TEXT DEFAULT '', platform TEXT DEFAULT 'android',
        mode_type TEXT NOT NULL DEFAULT 'edl_9008', description TEXT NOT NULL,
        koordinat TEXT DEFAULT '', difficulty TEXT DEFAULT 'medium',
        image_url TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS cleaning_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_serial TEXT DEFAULT '',
        platform TEXT DEFAULT 'android', action_type TEXT NOT NULL,
        space_saved_mb REAL DEFAULT 0, result TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS firmware_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_model TEXT NOT NULL,
        platform TEXT DEFAULT 'android', firmware_version TEXT DEFAULT '',
        file_type TEXT DEFAULT 'firmware_rom', source TEXT DEFAULT '',
        download_url TEXT NOT NULL, md5_hash TEXT DEFAULT '', is_verified INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS adb_scan_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, serial TEXT DEFAULT '',
        model TEXT DEFAULT '', manufacturer TEXT DEFAULT '', chipset TEXT DEFAULT '',
        android_version TEXT DEFAULT '', sdk TEXT DEFAULT '',
        bootloader TEXT DEFAULT 'unknown', security_patch TEXT DEFAULT '',
        product_name TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS ios_scan_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, udid TEXT DEFAULT '',
        model TEXT DEFAULT '', ios_version TEXT DEFAULT '', serial_number TEXT DEFAULT '',
        activation_status TEXT DEFAULT '', battery_health REAL DEFAULT 0,
        cycle_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS backup_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_serial TEXT NOT NULL,
        platform TEXT DEFAULT 'android', mode TEXT DEFAULT 'unknown',
        partition_name TEXT NOT NULL, file_path TEXT NOT NULL,
        file_size_bytes INTEGER DEFAULT 0, sha256_before TEXT DEFAULT '',
        sha256_after TEXT DEFAULT '', status TEXT DEFAULT 'completed',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS dead_phone_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, detected_mode TEXT NOT NULL,
        serial TEXT DEFAULT '', vendor TEXT DEFAULT '', product TEXT DEFAULT '',
        vid_pid TEXT DEFAULT '', chipset TEXT DEFAULT '',
        detected_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS flash_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_serial TEXT NOT NULL,
        device_model TEXT DEFAULT '', partition_name TEXT DEFAULT '',
        firmware_file TEXT DEFAULT '', firmware_verified INTEGER DEFAULT 0,
        backup_before TEXT DEFAULT '', backup_sha256 TEXT DEFAULT '',
        operation TEXT DEFAULT 'flash', status TEXT DEFAULT 'pending',
        error_log TEXT DEFAULT '', teknisi TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        completed_at TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS safety_checklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_serial TEXT NOT NULL,
        check_type TEXT NOT NULL, check_name TEXT NOT NULL,
        result INTEGER DEFAULT 0, detail TEXT DEFAULT '',
        checked_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

    c.execute("SELECT COUNT(*) FROM inventory_sparepart")
    if c.fetchone()[0] == 0:
        seed_inv = [
            ('LCD Redmi Note 13 Original','lcd','SKU-LCD-RN13',5,180000,350000,'Redmi Note 13, Redmi Note 13 Pro',3,0),
            ('LCD Samsung A54 Original','lcd','SKU-LCD-A54',3,220000,420000,'Samsung A54, Samsung A34',3,0),
            ('LCD iPhone 11 Original','lcd','SKU-LCD-IP11',2,450000,750000,'iPhone 11, iPhone 11 Pro',2,0),
            ('LCD iPhone 12 Pro Max','lcd','SKU-LCD-IP12PM',2,650000,950000,'iPhone 12 Pro Max',2,0),
            ('Baterai Redmi Note 13','battery','SKU-BAT-RN13',8,85000,150000,'Redmi Note 13',4,0),
            ('Baterai Samsung A54','battery','SKU-BAT-A54',6,95000,165000,'Samsung A54',4,0),
            ('Baterai iPhone 11','battery','SKU-BAT-IP11',4,180000,300000,'iPhone 11',2,0),
            ('Baterai iPhone 12/13','battery','SKU-BAT-IP12',3,220000,350000,'iPhone 12, iPhone 13',2,0),
            ('IC Power Mediatek MT6853','ic_power','SKU-IC-MT6853',10,35000,85000,'Redmi Note 10/11/12',5,0),
            ('IC Power Qualcomm PM8150','ic_power','SKU-IC-PM8150',8,45000,95000,'Xiaomi Mi 10, OnePlus 8, Samsung S20',5,0),
            ('IC Power Apple 338S00348','ic_power','SKU-IC-AP338',5,120000,200000,'iPhone 11 Series',3,0),
            ('IC Power Apple 338S00648','ic_power','SKU-IC-AP648',3,150000,250000,'iPhone 12/13 Series',2,0),
            ('Fleksibel Charging Redmi Note 13','flex_cable','SKU-FLX-RN13',7,25000,55000,'Redmi Note 13',5,0),
            ('Fleksibel Charging Samsung A54','flex_cable','SKU-FLX-A54',5,28000,60000,'Samsung A54',5,0),
            ('Fleksibel Charging iPhone 11','flex_cable','SKU-FLX-IP11',4,40000,80000,'iPhone 11',4,0),
            ('Fleksibel Charging iPhone 12/13','flex_cable','SKU-FLX-IP12',3,50000,95000,'iPhone 12, iPhone 13',4,0),
            ('Speaker Redmi Note 13','speaker','SKU-SPK-RN13',6,30000,65000,'Redmi Note 13',4,0),
            ('Housing Redmi Note 13 Original','housing','SKU-HSN-RN13',3,75000,150000,'Redmi Note 13',2,0),
            ('Housing iPhone 11','housing','SKU-HSN-IP11',2,180000,300000,'iPhone 11',2,0),
            ('Kamera Belakang Redmi Note 13','camera','SKU-CAM-RN13',4,55000,110000,'Redmi Note 13',3,0),
            ('Kamera Belakang iPhone 11','camera','SKU-CAM-IP11',2,250000,400000,'iPhone 11',2,0),
        ]
        c.executemany("INSERT INTO inventory_sparepart (nama,kategori,sku,stock,harga_beli,harga_jual,kompatibel,min_stock,terjual_bulan_ini) VALUES(?,?,?,?,?,?,?,?,?)", seed_inv)

    c.execute("SELECT COUNT(*) FROM testpoint_guides")
    if c.fetchone()[0] == 0:
        seed_tp = [
            ('qualcomm','','android','edl_9008','Cari titik testpoint di sekitar IC Power/PMIC dekat konektor USB. Biasanya berupa 2 titik tembaga kecil (golden pad) berdekatan. Gunakan pinsil runcing untuk short kedua titik.', '{"x":320,"y":480}', 'medium', ''),
            ('mediatek','','android','edl_9008','Cari titik testpoint di dekat IC CPU/eMMC. Biasanya berupa 1 titik tembaga kecil di tepi PCB. Colokkan USB tanpa baterai, probe titik ke GND menggunakan pinsil.', '{"x":150,"y":620}', 'medium', ''),
            ('exynos','','android','edl_9008','Untuk Samsung Exynos: tekan Volume Bawah + Volume Atas lalu colok USB. Jika tidak masuk, buka casing dan cari titik JTAG di dekat IC CPU.', '{"x":280,"y":400}', 'hard', ''),
            ('huawei_kirin','','android','edl_9008','Untuk Huawei Kirin: tekan Volume Bawah sambil colok USB. Atau gunakan testpoint yang ada di dekat IC Power PMU.', '{"x":200,"y":350}', 'medium', ''),
            ('apple','','ios','dfu_mode','Untuk iPhone Tombol Home (hingga iPhone 8/SE):\\n1. Colok ke komputer\\n2. Tekan & tahan Tombol Power (3 detik)\\n3. Sambil tahan Power, tekan & tahan Tombol Home (10 detik)\\n4. Lepas Power tapi tetap tahan Home (5 detik)\\n5. Layar tetap hitam = DFU Mode', '{"x":0,"y":0}', 'medium', ''),
            ('apple_faceid','','ios','dfu_mode','Untuk iPhone Face ID (iPhone X ke atas):\\n1. Colok ke komputer\\n2. Tekan Volume Up lekas, Volume Down lekas\\n3. Tahan Tombol Side (Power) 10 detik\\n4. Sambil tahan Side, tekan Volume Down 5 detik\\n5. Lepas Side tapi tetap tahan Volume Down 10 detik\\n6. Layar tetap hitam = DFU Mode', '{"x":0,"y":0}', 'medium', ''),
            ('apple','','ios','recovery_mode','Untuk iPhone Tombol Home: Tekan & tahan Home + Power 10-15 detik sampai logo iTunes/kabel.\\nUntuk iPhone Face ID: Tekan Volume Up lekas, Volume Down lekas, lalu tahan Side sampai logo iTunes/kabel.', '{"x":0,"y":0}', 'easy', ''),
        ]
        c.executemany("INSERT INTO testpoint_guides (chipset_brand,chipset_model,platform,mode_type,description,koordinat,difficulty,image_url) VALUES(?,?,?,?,?,?,?,?)", seed_tp)

    # Indexes untuk performa
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_created ON pelanggan(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_status ON pelanggan(service_status)",
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_model ON pelanggan(device_model)",
        "CREATE INDEX IF NOT EXISTS idx_pelanggan_imei ON pelanggan(imei)",
        "CREATE INDEX IF NOT EXISTS idx_log_service_status ON log_service(status)",
        "CREATE INDEX IF NOT EXISTS idx_log_service_created ON log_service(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_stock ON inventory_sparepart(stock)",
        "CREATE INDEX IF NOT EXISTS idx_inventory_kategori ON inventory_sparepart(kategori)",
        "CREATE INDEX IF NOT EXISTS idx_flash_log_serial ON flash_log(device_serial)",
        "CREATE INDEX IF NOT EXISTS idx_backup_log_serial ON backup_log(device_serial)",
        "CREATE INDEX IF NOT EXISTS idx_adb_scan_serial ON adb_scan_log(serial)",
        "CREATE INDEX IF NOT EXISTS idx_testpoint_chipset ON testpoint_guides(chipset_brand,mode_type)",
    ]:
        try:
            c.execute(idx_sql)
        except Exception:
            pass

    conn.commit()
    conn.close()

ADB_ERROR_HINTS = {
    "device unauthorized": "HP belum di-authorize! Buka HP → izinkan USB Debugging (centang 'Always allow')",
    "device offline": "HP terdeteksi tapi offline. Coba cabut-colok USB lagi",
    "no devices/emulators found": "Tidak ada HP terdeteksi. Pastikan USB Debugging ON dan kabel data sync",
    "insufficient permissions": "Izin USB kurang. Jalankan: adb kill-server && adb start-server && adb root",
    "not found": "Perintah tidak ditemukan. Install ADB: scoop install adb (Windows) atau download https://developer.android.com/studio/releases/platform-tools",
    "closed": "Koneksi USB terputus. Coba ganti kabel atau port USB",
    "unauthorized": "HP belum di-authorize di popup USB Debugging",
}

def _run(cmd: list, timeout: int = 15) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        ok = r.returncode == 0
        err = r.stderr.strip()
        if not ok:
            for key, hint in ADB_ERROR_HINTS.items():
                if key in err.lower():
                    err = f"{err}\n💡 {hint}"
                    break
        return ok, r.stdout.strip(), err
    except FileNotFoundError:
        return False, "", f"❌ Perintah '{cmd[0]}' tidak ditemukan. Install: scoop install adb (Windows) / apt install android-tools-adb (Linux)"
    except subprocess.TimeoutExpired:
        return False, "", f"⏱ Timeout {timeout}s — HP terlalu lambat merespon. Coba colok ulang USB."
    except Exception as e:
        return False, "", f"❌ Error: {e}"


def adb_devices() -> list:
    ok, out, _ = _run(["adb", "devices"], timeout=8)
    if not ok: return []
    devices = []
    for line in out.splitlines():
        if "\tdevice" in line and "List" not in line:
            s = line.split("\t")[0].strip()
            if s: devices.append(s)
    return devices


def adb_unauthorized() -> list:
    ok, out, _ = _run(["adb", "devices"], timeout=8)
    if not ok: return []
    result = []
    for line in out.splitlines():
        if "\tunauthorized" in line:
            s = line.split("\t")[0].strip()
            if s: result.append(s)
    return result


def adb_device_status() -> dict:
    """Returns full device connection status."""
    ok, out, _ = _run(["adb", "devices"], timeout=8)
    if not ok: return {"authorized": [], "unauthorized": [], "offline": [], "recovering": []}
    result = {"authorized": [], "unauthorized": [], "offline": [], "recovering": []}
    for line in out.splitlines():
        if "List" in line: continue
        if "\t" in line:
            parts = line.split("\t")
            s = parts[0].strip()
            status = parts[1].strip() if len(parts) > 1 else ""
            if status == "device":
                result["authorized"].append(s)
            elif status == "unauthorized":
                result["unauthorized"].append(s)
            elif status == "offline":
                result["offline"].append(s)
            else:
                result["recovering"].append(s)
    return result


def fastboot_devices() -> list:
    ok, out, _ = _run(["fastboot", "devices"], timeout=8)
    if not ok: return []
    devices = []
    for line in out.splitlines():
        if line.strip() and "fastboot" in line:
            devices.append(line.split()[0])
    return devices


def adb_getprop(serial: str, prop: str) -> str:
    ok, out, _ = _run(["adb", "-s", serial, "shell", "getprop", prop], timeout=5)
    return out.strip() if ok else ""


def adb_shell(serial: str, cmd: str) -> tuple:
    return _run(["adb", "-s", serial, "shell", cmd], timeout=15)


def fastboot_getvar(serial: str, var: str) -> str:
    ok, out, _ = _run(["fastboot", "-s", serial, "getvar", var], timeout=8)
    m = re.search(rf'{re.escape(var)}:\s*(\S+)', out)
    return m.group(1) if m else ""


def check_adb_installed() -> bool:
    return shutil.which("adb") is not None


def check_fastboot_installed() -> bool:
    return shutil.which("fastboot") is not None


def deep_scan_android(serial: str) -> dict:
    info = {"platform": "android", "serial": serial, "model": "", "chipset": "",
            "android": "", "sdk": "", "bootloader": "unknown", "security_patch": "",
            "manufacturer": "", "product": "", "fingerprint": "", "serialno": "",
            "battery": {}, "storage": {}, "partitions": [], "cpu_info": "",
            "mem_total": "", "wlan_mac": "", "bt_mac": "", "usb_config": ""}
    props = [("model","ro.product.model"),("chipset","ro.board.platform"),
             ("android","ro.build.version.release"),("sdk","ro.build.version.sdk"),
             ("manufacturer","ro.product.manufacturer"),("product","ro.product.name"),
             ("fingerprint","ro.build.fingerprint"),("security_patch","ro.build.version.security_patch"),
             ("serialno","ro.serialno")]
    for k, p in props:
        info[k] = adb_getprop(serial, p)
    ok, out, _ = adb_shell(serial, "cat /proc/cpuinfo | head -20")
    if ok: info["cpu_info"] = out
    ok, out, _ = adb_shell(serial, "cat /proc/meminfo | head -5")
    if ok: info["mem_total"] = out
    info["wlan_mac"] = adb_getprop(serial, "ro.wifi.mac")
    info["bt_mac"] = adb_getprop(serial, "ro.bt.mac")
    info["usb_config"] = adb_getprop(serial, "sys.usb.config")
    bl = adb_getprop(serial, "ro.boot.flash.locked")
    if bl == "1": info["bootloader"] = "locked"
    elif bl == "0": info["bootloader"] = "unlocked"
    else:
        vbs = adb_getprop(serial, "ro.boot.verifiedbootstate")
        info["bootloader"] = "locked" if vbs == "green" else "unlocked" if vbs == "orange" else vbs if vbs else "unknown"
    info["battery"] = android_battery_raw(serial)
    info["storage"] = android_storage_info(serial)
    ok, out, _ = adb_shell(serial, "cat /proc/partitions")
    if ok: info["partitions"] = out.splitlines()
    return info


def android_battery_raw(serial: str) -> dict:
    data = {"level": 0, "voltage": 0.0, "temperature": 0.0, "current_now": 0,
            "health": "unknown", "status": "unknown", "usb_online": 0}
    ok, out, _ = adb_shell(serial, "dumpsys battery")
    if not ok: return data
    for line in out.splitlines():
        if "level:" in line:
            m = re.search(r'level:\s*(\d+)', line)
            if m: data["level"] = int(m.group(1))
        if "voltage:" in line:
            m = re.search(r'voltage:\s*(\d+)', line)
            if m: data["voltage"] = round(int(m.group(1))/1000, 3)
        if "temperature:" in line:
            m = re.search(r'temperature:\s*(\d+)', line)
            if m: data["temperature"] = round(int(m.group(1))/10, 1)
        if "current now:" in line:
            m = re.search(r'current now:\s*(-?\d+)', line)
            if m: data["current_now"] = int(m.group(1))
        if "health:" in line:
            m = re.search(r'health:\s*(\d+)', line)
            if m:
                hm = {"2":"good","3":"overheat","4":"dead","5":"over_voltage","6":"unspecified_failure","7":"cold"}
                data["health"] = hm.get(m.group(1),"unknown")
        if "status:" in line:
            m = re.search(r'status:\s*(\d+)', line)
            if m:
                sm = {"1":"unknown","2":"charging","3":"discharging","4":"not_charging","5":"full"}
                data["status"] = sm.get(m.group(1),"unknown")
        if "USB online:" in line:
            m = re.search(r'USB online:\s*(\w+)', line)
            if m: data["usb_online"] = 1 if m.group(1)=="true" else 0
    return data


def auto_read_ampere_adb(serial: str) -> dict:
    """Baca ampere langsung dari HP via ADB (dumpsys battery current_now).
    Returns: {"ampere": float, "source": str, "voltage": float, "detail": str}
    """
    result = {"ampere": 0.0, "source": "", "voltage": 0.0, "detail": "Tidak terdeteksi"}
    ok, out, _ = adb_shell(serial, "dumpsys battery")
    if not ok:
        result["detail"] = "Gagal baca dumpsys battery"
        return result
    current_now = 0
    voltage = 0
    for line in out.splitlines():
        if "current now:" in line:
            m = re.search(r'current now:\s*(-?\d+)', line)
            if m: current_now = int(m.group(1))
        if "voltage:" in line:
            m = re.search(r'voltage:\s*(\d+)', line)
            if m: voltage = int(m.group(1))
    if current_now == 0:
        result["detail"] = "Arus 0 — HP mungkin tidak dicharge atau idle"
        return result
    ampere_val = abs(current_now) / 1_000_000  # uA to A
    result["ampere"] = round(ampere_val, 4)
    result["voltage"] = round(voltage / 1000, 3)
    result["source"] = f"ADB ({serial[:8]}…)"
    result["detail"] = f"{ampere_val:.4f}A @ {voltage/1000:.2f}V (via ADB)"
    return result


def _detect_power_meter_serial() -> list:
    """Cari USB power meter / serial port yang terhubung.
    Mendukung: FNIRSI FNB58, TC66C, ATORCH, dan power meter generic.
    Returns: list of {"port": str, "name": str, "vid": str, "pid": str}
    """
    import glob
    found = []
    patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyS[0-9]*", "/dev/ttyAMA*", "/dev/cu.*"]
    for pat in patterns:
        for path in glob.glob(pat):
            if not os.path.exists(path):
                continue
            info = {"port": path, "name": "Unknown Power Meter", "vid": "", "pid": ""}
            try:
                import subprocess
                ok, out, _ = _run(["udevadm", "info", "--query=property", path], timeout=3)
                if ok:
                    for line in out.splitlines():
                        if line.startswith("ID_VENDOR="):
                            info["name"] = line.split("=", 1)[1]
                        elif line.startswith("ID_MODEL="):
                            info["name"] += " " + line.split("=", 1)[1]
                        elif line.startswith("ID_VENDOR_ID="):
                            info["vid"] = line.split("=", 1)[1]
                        elif line.startswith("ID_MODEL_ID="):
                            info["pid"] = line.split("=", 1)[1]
            except Exception:
                pass
            found.append(info)
    return found


POWER_METER_PROFILES = {
    "f NB58": {"baud": 115200, "parser": "fnirsi"},
    "fnirsi": {"baud": 115200, "parser": "fnirsi"},
    "tc66": {"baud": 115200, "parser": "tc66"},
    "atorch": {"baud": 115200, "parser": "generic"},
    "rd tech": {"baud": 115200, "parser": "generic"},
    "dps": {"baud": 115200, "parser": "generic"},
}


def auto_read_ampere_from_power_meter(timeout: float = 2.0) -> dict:
    """Baca ampere dari USB power meter yang terdeteksi.
    Returns: {"ampere": float, "source": str, "voltage": float, "detail": str}
    """
    result = {"ampere": 0.0, "source": "", "voltage": 0.0, "detail": "Tidak ada power meter"}
    ports = _detect_power_meter_serial()
    if not ports:
        result["detail"] = "Tidak ada USB power meter terdeteksi"
        return result
    for p in ports:
        port_name = p["port"]
        name_lower = p["name"].lower()
        baud = 115200
        for key, profile in POWER_METER_PROFILES.items():
            if key in name_lower:
                baud = profile["baud"]
                break
        try:
            import serial
            with serial.Serial(port_name, baud, timeout=int(timeout)) as ser:
                ser.reset_input_buffer()
                ser.write(b"r\r\n")
                import time as _time
                _time.sleep(0.3)
                raw = ser.read(1024).decode("utf-8", errors="ignore")
                if not raw:
                    continue
                lines = raw.strip().split("\n")
                for line in lines:
                    parts = line.strip().split(",")
                    if len(parts) >= 4:
                        try:
                            amp = float(parts[2])
                            volt = float(parts[3])
                            if 0 < amp < 10:
                                result["ampere"] = round(amp, 4)
                                result["voltage"] = round(volt, 3)
                                result["source"] = f"{p['name']} ({port_name})"
                                result["detail"] = f"{amp:.4f}A @ {volt:.2f}V (via {port_name})"
                                return result
                        except ValueError:
                            continue
                    m = re.search(r'([\d.]+)\s*A', line, re.I)
                    if m:
                        try:
                            amp = float(m.group(1))
                            if 0 < amp < 10:
                                result["ampere"] = round(amp, 4)
                                result["source"] = f"{p['name']} ({port_name})"
                                result["detail"] = f"{amp:.4f}A (via {port_name})"
                                return result
                        except ValueError:
                            continue
        except Exception:
            continue
    result["detail"] = f"Port ditemukan ({len(ports)}) tapi gagal baca data"
    return result


def auto_detect_ampere() -> dict:
    """Otomatis deteksi ampere dari semua sumber yang tersedia.
    Priority: Power Meter > ADB
    Returns: {"ampere": float, "source": str, "voltage": float, "detail": str}
    """
    # Priority 1: USB Power Meter
    meter = auto_read_ampere_from_power_meter()
    if meter["ampere"] > 0:
        return meter
    # Priority 2: ADB
    adb_devs = adb_devices()
    if adb_devs:
        adb_val = auto_read_ampere_adb(adb_devs[0])
        if adb_val["ampere"] > 0:
            return adb_val
    return {"ampere": 0.0, "source": "", "voltage": 0.0, "detail": "Tidak terdeteksi otomatis — isi manual"}


def android_battery_capacity(serial: str) -> dict:
    cap = {"current_mah": 0.0, "design_mah": 0.0, "cycle_count": 0, "health_pct": 0.0}
    ok1, out1, _ = adb_shell(serial, "cat /sys/class/power_supply/battery/charge_full")
    ok2, out2, _ = adb_shell(serial, "cat /sys/class/power_supply/battery/charge_full_design")
    ok3, out3, _ = adb_shell(serial, "cat /sys/class/power_supply/battery/cycle_count")
    if ok1 and out1.strip().isdigit(): cap["current_mah"] = round(int(out1.strip())/1000, 2)
    if ok2 and out2.strip().isdigit(): cap["design_mah"] = round(int(out2.strip())/1000, 2)
    if ok3 and out3.strip().isdigit(): cap["cycle_count"] = int(out3.strip())
    if cap["design_mah"] > 0 and cap["current_mah"] > 0:
        cap["health_pct"] = round((cap["current_mah"]/cap["design_mah"])*100, 2)
    return cap


def android_storage_info(serial: str) -> dict:
    info = {"total_gb": 0, "used_gb": 0, "free_gb": 0, "free_percent": 0}
    ok, out, _ = adb_shell(serial, "df /data")
    if ok:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 6 and parts[1].isdigit():
                total_k = int(parts[1]); used_k = int(parts[2]); free_k = int(parts[3])
                info["total_gb"] = round(total_k/1024/1024, 2)
                info["used_gb"] = round(used_k/1024/1024, 2)
                info["free_gb"] = round(free_k/1024/1024, 2)
                if total_k > 0: info["free_percent"] = round((free_k/total_k)*100, 1)
                break
    return info


def android_partitions_detail(serial: str) -> list:
    ok, out, _ = adb_shell(serial, "ls -la /dev/block/platform/*/by-name/ 2>/dev/null || ls -la /dev/block/bootdevice/by-name/ 2>/dev/null")
    return out.splitlines() if ok else []


# iOS
def check_idevice_installed() -> bool:
    return shutil.which("ideviceinfo") is not None


def idevice_devices() -> list:
    ok, out, _ = _run(["idevice_id", "-l"], timeout=8)
    if ok and out.strip():
        return [l.strip() for l in out.splitlines() if l.strip()]
    return []


def idevice_get_info(udid: str = "") -> dict:
    info = {"platform": "ios", "udid": udid or "", "model": "", "product_type": "",
            "ios_version": "", "serial_number": "", "activation_status": "",
            "device_name": "", "device_color": "", "baseband_version": "",
            "wifi_mac": "", "bt_mac": "", "battery": {}}
    cmd = ["ideviceinfo"] + (["-u", udid] if udid else [])
    ok, out, _ = _run(cmd, timeout=10)
    if not ok: return info
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1); k = k.strip(); v = v.strip()
            if k == "ProductType": info["product_type"] = info["model"] = v
            elif k == "ProductVersion": info["ios_version"] = v
            elif k == "SerialNumber": info["serial_number"] = v
            elif k == "UniqueDeviceID": info["udid"] = v
            elif k == "ActivationState": info["activation_status"] = v
            elif k == "DeviceName": info["device_name"] = v
            elif k == "DeviceColor": info["device_color"] = v
            elif k == "BasebandVersion": info["baseband_version"] = v
            elif k == "WiFiAddress": info["wifi_mac"] = v
            elif k == "BluetoothAddress": info["bt_mac"] = v
    return info


def _safe_float(val, default=0.0):
    try:
        return float(val.rstrip('%C')) if isinstance(val, str) else default
    except (ValueError, AttributeError):
        return default

def idevice_battery_info(udid: str = "") -> dict:
    bat = {"health_pct": 0.0, "cycle_count": 0, "voltage": 0.0, "temperature": 0.0,
           "current_capacity": 0, "design_capacity": 0, "status": "unknown"}
    cmd = ["ideviceinfo", "-q", "com.apple.mobile.battery"]
    if udid: cmd = ["ideviceinfo", "-u", udid, "-q", "com.apple.mobile.battery"]
    ok, out, _ = _run(cmd, timeout=10)
    if ok:
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1); k = k.strip(); v = v.strip()
                if k == "BatteryCurrentCapacity": bat["current_capacity"] = int(v) if v.isdigit() else 0
                elif k == "BatteryDesignCapacity": bat["design_capacity"] = int(v) if v.isdigit() else 0
                elif k == "BatteryCycleCount": bat["cycle_count"] = int(v) if v.isdigit() else 0
                elif k == "BatteryHealthPercentage": bat["health_pct"] = _safe_float(v)
                elif k == "BatteryVoltage": bat["voltage"] = _safe_float(v)
                elif k == "BatteryTemperature": bat["temperature"] = _safe_float(v)
                elif k == "BatteryStatus": bat["status"] = v
        if bat["health_pct"] == 0 and bat["design_capacity"] > 0 and bat["current_capacity"] > 0:
            bat["health_pct"] = round((bat["current_capacity"]/bat["design_capacity"])*100, 2)
    return bat


def idevice_activation_lock(udid: str = "") -> dict:
    lock = {"activation_lock": 0, "find_my_iphone": 0, "status": "unknown"}
    cmd = ["ideviceinfo", "-q", "com.apple.mobile.findmy"]
    if udid: cmd = ["ideviceinfo", "-u", udid, "-q", "com.apple.mobile.findmy"]
    ok, out, _ = _run(cmd, timeout=10)
    if ok:
        for line in out.splitlines():
            if "FindMyiPhoneEnabled" in line:
                v = line.split(":", 1)[1].strip()
                lock["find_my_iphone"] = 1 if v.lower()=="true" or v=="1" else 0
            elif "ActivationLock" in line:
                v = line.split(":", 1)[1].strip()
                lock["activation_lock"] = 1 if v.lower()=="true" or v=="1" else 0
        lock["status"] = "locked" if lock["activation_lock"] or lock["find_my_iphone"] else "unlocked"
    return lock


# Network scan
def network_scan(subnet: str = "") -> list:
    results = []
    if not subnet:
        ok, out, _ = _run(["hostname", "-I"], timeout=5)
        if ok and out.strip():
            ip = out.strip().split()[0]
            subnet = ".".join(ip.split(".")[:3]) + ".0"
        else:
            ok, out, _ = _run(["ip", "route"], timeout=5)
            if ok:
                for line in out.splitlines():
                    if "default" in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            subnet = ".".join(parts[2].split(".")[:3]) + ".0"
                            break
    if not subnet: return results
    base = ".".join(subnet.split(".")[:3])
    progress_bar = st.progress(0)
    status_text = st.empty()
    for i in range(1, 255):
        ip = f"{base}.{i}"
        ok, _, _ = _run(["ping", "-c", "1", "-W", "1", ip], timeout=3)
        if ok:
            h_ok, host_out, _ = _run(["hostname", ip], timeout=3) if shutil.which("hostname") else (False,"","")
            hostname = host_out.strip() if h_ok and host_out else ""
            os_type = ""
            if shutil.which("nmap"):
                nm_ok, nm_out, _ = _run(["nmap", "-O", "--osscan-guess", ip], timeout=30)
                if nm_ok:
                    for line in nm_out.splitlines():
                        if "OS details" in line or "Aggressive OS" in line or "Running" in line:
                            os_type = line.strip(); break
            results.append({"ip": ip, "hostname": hostname, "os_type": os_type or "Unknown", "ping": "alive"})
        progress_bar.progress(i/254)
        status_text.text(f"Scanning {i}/254... ({len(results)} ditemukan)")
    progress_bar.empty()
    status_text.empty()
    return results


def firmware_urls(model: str, chipset: str = "", platform: str = "android") -> list:
    query = model.replace(" ", "+")
    urls = [("Google Search", f"https://www.google.com/search?q={query}+stock+rom+firmware+download+free"),
            ("Firmware27 (Indonesia)", f"https://firmware27.com/?s={model.replace(' ', '-')}"),
            ("XDA Developers", f"https://www.xda-developers.com/?s={query}")]
    ml = model.lower()
    if any(x in ml for x in ["samsung"]): urls.append(("SamMobile", f"https://www.sammobile.com/?s={query}"))
    if any(x in ml for x in ["xiaomi","redmi","poco","mi "]): urls.append(("MIUI ROM", f"https://miuirom.org/?s={model.replace(' ', '-')}"))
    if platform=="ios" or any(x in ml for x in ["iphone","ipad","ipod"]):
        urls.append(("IPSW.me", "https://ipsw.me/"))
        urls.append(("iOS Jailbreak Guide", "https://ios.cfw.guide/"))
    if "mediatek" in chipset.lower() or "mt" in chipset.lower(): urls.append(("SP Flash Tool", "https://spflashtool.com/"))
    if "qualcomm" in chipset.lower() or "snapdragon" in chipset.lower(): urls.append(("QPST/QFIL", "https://qpsttool.com/"))
    if "exynos" in chipset.lower(): urls.append(("Odin", "https://odindownload.com/"))
    urls.append(("Platform Tools", "https://developer.android.com/studio/releases/platform-tools"))
    return urls

AI_RULES = [
    (0.000, 0.005, "mati_total", "TIDAK ADA SIRKUIT AKTIF — Putus total di jalur BATT+ atau konektor baterai rusak.", "high",
     "1. Ukur tegangan di konektor baterai dengan multimeter (mode DCV). Jika 0V -> putus jalur.\n2. Ukur diode mode pada jalur BATT+ ke GND. Jika OL (Open Loop) -> putus total.\n3. Periksa jalur VBUS dari port USB ke IC Charging.\n4. Periksa konektor fleksibel charging."),
    (0.010, 0.040, "mati_total", "HP GANTUNG — Terindikasi SOFTWARE BRICK atau IC eMMC/UFS/CPU rusak. Arus hanya cukup untuk RTC.", "medium",
     "1. Coba masuk EDL MODE (Qualcomm) / DOWNLOAD MODE (MediaTek) / DFU (iOS).\n2. Jika bisa masuk EDL -> flashing ulang firmware.\n3. Jika TIDAK bisa masuk EDL -> kemungkinan IC eMMC/UFS korup.\n4. Ukur tegangan di inductor PMIC."),
    (0.010, 0.040, "tekan_power", "HP ON TAPI ARUS RENDAH — Boot loop atau kernel crash di awal.", "medium",
     "1. Coba masuk RECOVERY MODE (Volume Up + Power).\n2. Jika bisa masuk recovery -> wipe cache partition.\n3. Flash ulang boot.img via fastboot."),
    (0.050, 0.200, "mati_total", "ARUS RENDAH — Short parsial di jalur sinyal atau IC power supply tidak optimal.", "medium",
     "1. Periksa tegangan keluaran PMIC/PMU di inductor sekitar.\n2. Thermal detection: sentuh komponen satu per satu.\n3. Lepaskan peripheral satu per satu (LCD, camera, speaker)."),
    (0.050, 0.200, "tekan_power", "BOOT LOOP — Arus naik turun. Short di peripheral atau baterai drop.", "low",
     "1. Lepaskan fleksibel peripheral (LCD, kamera, fingerprint) satu per satu.\n2. Ganti baterai dengan power supply."),
    (0.200, 0.500, "mati_total", "ARUS SEDANG — Short di komponen display atau IC daya menengah.", "medium",
     "1. Lepaskan fleksibel LCD -> jika arus turun drastis, ganti LCD.\n2. Thermal detection."),
    (0.500, 1.000, "mati_total", "ARUS TINGGI PASIF — Short di IC PA/RF/WiFi atau komponen daya sedang.", "high",
     "1. Thermal detection: cari komponen yang panas dalam 5 detik.\n2. Fokus pada IC PA, IC WiFi, IC Audio.\n3. Ganti IC yang short."),
    (1.000, 9.999, "mati_total", "SHORT BESAR — Arus >1A pada jalur VCC_MAIN/VBAT tanpa tekan power! Kondisi KRITIS!", "critical",
     "LANGKAH DARURAT:\n1. MATIKAN SEGERA POWER SUPPLY!\n2. Thermal detection atau alkohol test.\n3. Ukur resistansi VCC_MAIN ke GND.\n4. Tersangka: IC Power/PMIC, kapasitor filter, Mosfet."),
    (1.000, 9.999, "tekan_power", "ARUS SANGAT TINGGI SAAT POWER — Short di komponen switching atau IC power utama.", "high",
     "1. Periksa IC Power/PMIC utama.\n2. Lepaskan beban -> cabut semua fleksibel.\n3. Jika masih short: ganti IC Power."),
]

IOS_AI_RULES = [
    (0.000, 0.005, "mati_total", "iPhone mati total — Tidak ada konsumsi arus. Putus jalur BATT+ atau konektor baterai.", "high",
     "1. Periksa konektor baterai iPhone.\n2. Ukur diode mode pada jalur BATT_VCC ke GND.\n3. Periksa IC Power Apple (338S).\n4. Cek USB/VBUS ke IC Tristar."),
    (0.010, 0.040, "mati_total", "iPhone mati total arus rendah — DFU mode atau IC NAND rusak.", "medium",
     "1. Coba masuk DFU Mode.\n2. Jika masuk DFU -> restore via iTunes/Finder.\n3. Jika tidak -> IC NAND atau CPU rusak."),
    (0.050, 0.200, "mati_total", "iPhone boot loop — arus rendah naik turun. Short di PMIC atau baterai habis.", "medium",
     "1. Coba masuk Recovery Mode.\n2. Periksa IC Tristar (USB/charging) -> sering short iPhone 7/8/X.\n3. Periksa IC Audio -> iPhone 7 disease."),
    (0.500, 9.999, "mati_total", "iPhone SHORT BESAR — IC Power Apple hampir pasti short!", "critical",
     "LANGKAH DARURAT:\n1. MATIKAN POWER SUPPLY!\n2. Cari IC panas: IC Power, IC Audio, IC WiFi.\n3. iPhone 7: lepas IC Audio.\n4. iPhone 8/X: lepas IC Power.\n5. Ganti IC short dengan reballing."),
]


def diagnose_ampere(ampere: float, kondisi: str, platform: str = "android") -> Tuple[str, str, str]:
    rules = IOS_AI_RULES if platform == "ios" else AI_RULES
    for mn, mx, cond, dia, sev, rek in rules:
        if mn <= ampere <= mx and cond in kondisi:
            return dia, sev, rek
    return "Pola arus tidak dikenali.", "low", "Periksa manual dengan multimeter."


def analyze_symptoms(text: str) -> str:
    s = text.lower()
    patterns = [
        (["jatuh","terjatuh","benturan"],"Kerusakan fisik akibat benturan. Periksa LCD, konektor, dan komponen BGA."),
        (["air","cairan","tumpah","korosi","kecemplung"],"Korosi cairan. Lakukan ultrasonic cleaning pada PCB."),
        (["panas","overheat","kembung","bocor"],"Baterai atau IC Power bermasalah."),
        (["cas","ngecas","charging","charge","masuk power"],"Kerusakan jalur charging. Periksa port USB, fleksibel, IC BQ."),
        (["sinyal","no signal","telepon","network"],"Kerusakan jalur RF/PA. Periksa IC PA dan antenna."),
        (["layar","lcd","pecah","retak","gelap"],"Kerusakan LCD/Touchscreen."),
        (["kamera","foto"],"Kerusakan modul kamera."),
        (["suara","speaker","audio"],"Kerusakan jalur audio."),
        (["restart","reboot","hang","macet","bootloop"],"Kerusakan software atau IC RAM/eMMC."),
        (["getar","vibrator"],"Kerusakan motor vibrator."),
        (["touch","touchscreen","tidak responsif"],"Kerusakan digitizer/touchscreen."),
        (["baterai cepat habis","boros"],"Baterai menua atau short di jalur power."),
    ]
    for kw, ins in patterns:
        if any(k in s for k in kw):
            return ins
    return ""


def generate_battery_status_text(health_pct: float, cycle_count: int, platform: str = "android") -> str:
    lines = []
    if health_pct >= 85: lines.append("Status: BAIK — Baterai masih prima")
    elif health_pct >= 70: lines.append("Status: CUKUP — Mulai degradasi")
    elif health_pct >= 50: lines.append("Status: BURUK — Sangat disarankan ganti baterai")
    else: lines.append("Status: KRITIS — Baterai harus diganti!")
    if platform == "ios" and health_pct < 80:
        lines.append("iPhone akan throttle performa jika health < 80%.")
    if cycle_count > 800:
        lines.append(f"Siklus {cycle_count} >800 — kapasitas turun signifikan. Segera ganti baterai.")
    if platform == "ios" and cycle_count > 500 and cycle_count <= 800:
        lines.append(f"Siklus {cycle_count} — pertimbangkan ganti baterai.")
    if health_pct < 70 and cycle_count < 300:
        lines.append("Health rendah tapi cycle sedikit — kemungkinan cacat pabrik.")
    return "\n".join(lines)


ARB_DATABASE = {
    "xiaomi": {"level": 4, "min_ver": "MIUI 13.0.2.0", "note": "Xiaomi ARB sejak Android 11. Downgrade berbahaya."},
    "redmi": {"level": 5, "min_ver": "MIUI 14.0.2.0", "note": "Redmi ARB Level 5. Hati-hati downgrade!"},
    "poco": {"level": 4, "min_ver": "MIUI 13.0.5.0", "note": "POCO ARB Level 4."},
    "samsung": {"level": 2, "min_ver": "One UI 5.1", "note": "Samsung Knox — lebih longgar."},
    "oppo": {"level": 3, "min_ver": "ColorOS 13", "note": ""},
    "vivo": {"level": 3, "min_ver": "Funtouch OS 13", "note": ""},
    "realme": {"level": 3, "min_ver": "Realme UI 4.0", "note": ""},
    "oneplus": {"level": 3, "min_ver": "OxygenOS 13", "note": ""},
    "google": {"level": 1, "min_ver": "Android 14", "note": "Pixel ARB rendah."},
    "asus": {"level": 2, "min_ver": "ZenUI", "note": ""},
    "nokia": {"level": 2, "min_ver": "Android 13", "note": ""},
    "motorola": {"level": 1, "min_ver": "", "note": ""},
    "tecno": {"level": 3, "min_ver": "HiOS 13", "note": ""},
    "infinix": {"level": 3, "min_ver": "XOS 13", "note": ""},
    "huawei": {"level": 4, "min_ver": "HarmonyOS 3", "note": "Huawei bootloader terkunci rapat."},
}


def get_arb_level(model: str) -> dict:
    ml = model.lower()
    for key, info in ARB_DATABASE.items():
        if key in ml: return info
    return {"level": 1, "min_ver": "N/A", "note": "Tidak terdeteksi ARB spesifik."}


def check_frp_android(serial: str) -> dict:
    result = {"frp_locked": 0, "accounts": [], "details": ""}
    ok, out, _ = adb_shell(serial, "pm list packages 2>/dev/null | grep -i 'google' | head -5")
    if ok: result["details"] += f"Google packages: {out[:200]}\n"
    ok, out, _ = adb_shell(serial, "dumpsys account 2>/dev/null | grep -i 'Account {' | head -10")
    if ok and out:
        result["accounts"] = [l.strip() for l in out.splitlines() if l.strip()]
        result["frp_locked"] = 1 if result["accounts"] else 0
    ok, out, _ = adb_shell(serial, "settings get secure frp_device_locked 2>/dev/null")
    if ok and out.strip() == "1":
        result["frp_locked"] = 1
        result["details"] += "FRP device locked = 1\n"
    return result


def get_testpoint_guide(chipset: str = "", platform: str = "android", mode: str = "") -> dict:
    conn = get_conn(); c = conn.cursor()
    brand = ""
    if platform == "ios" or "apple" in chipset.lower():
        brand = "apple_faceid" if any(x in chipset.lower() for x in ["x ","11","12","13","14","15"]) else "apple"
    elif "qualcomm" in chipset.lower() or "snapdragon" in chipset.lower(): brand = "qualcomm"
    elif "mediatek" in chipset.lower() or "mt" in chipset.lower() or "dimensity" in chipset.lower(): brand = "mediatek"
    elif "exynos" in chipset.lower(): brand = "exynos"
    elif "kirin" in chipset.lower(): brand = "huawei_kirin"
    else: brand = "mediatek"
    if brand:
        if mode: c.execute("SELECT * FROM testpoint_guides WHERE chipset_brand=? AND mode_type=? LIMIT 1", (brand, mode))
        else: c.execute("SELECT * FROM testpoint_guides WHERE chipset_brand=? LIMIT 1", (brand,))
        row = c.fetchone(); conn.close(); return dict(row) if row else {}
    conn.close(); return {}


def android_clean_cache(serial: str) -> dict:
    result = {"actions": [], "total_saved_mb": 0, "errors": [], "before": {}, "after": {}}
    before = android_storage_info(serial)
    result["before"] = before
    cmds = [
        ("pm trim-caches 999G", "pm trim-caches 999G"),
        ("rm -rf /sdcard/.thumbnails/* 2>/dev/null; echo done", "rm -rf /sdcard/.thumbnails/*"),
        ("rm -rf /sdcard/Android/data/*/cache/* 2>/dev/null; echo done", "rm -rf Android/data/*/cache/*"),
        ("rm -rf /sdcard/Android/obb/* 2>/dev/null; echo done", "rm -rf Android/obb/*"),
        ("rm -rf /data/local/tmp/* 2>/dev/null; echo done", "rm -rf /data/local/tmp/*"),
        ("rm -rf /data/tombstones/* 2>/dev/null; echo done", "rm -rf /data/tombstones/*"),
        ("rm -rf /cache/* 2>/dev/null; echo done", "rm -rf /cache/*"),
        ("logcat -c 2>/dev/null; echo done", "logcat -c"),
        ("rm -rf /sdcard/bugreports/* 2>/dev/null; echo done", "rm -rf bugreports/*"),
    ]
    for full_cmd, display_cmd in cmds:
        ok, out, err = adb_shell(serial, full_cmd)
        if ok and "done" in out:
            result["actions"].append({"cmd": display_cmd, "status": "success"})
        else:
            result["errors"].append(f"{display_cmd}: {err[:80]}")
    after = android_storage_info(serial)
    result["after"] = after
    result["total_saved_mb"] = max(0, round((after["free_gb"] - before["free_gb"]) * 1024, 2))
    return result


def ios_clean_cache(udid: str = "") -> dict:
    result = {"actions": [], "total_saved_mb": 0, "errors": [],
              "note": "iOS tidak menyediakan akses cache via libimobiledevice.\nPembersihan manual: Settings -> General -> iPhone Storage -> Offload Apps\nSettings -> Safari -> Clear History and Website Data\nRestart paksa untuk membersihkan RAM cache."}
    ok, out, err = _run(["idevicediagnostics", "restart"], timeout=10)
    if ok: result["actions"].append({"cmd": "Connection OK", "status": "success"})
    else: result["errors"].append(f"Koneksi: {err[:80]}")
    return result


def financial_narrative() -> str:
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(total_biaya),0) FROM log_service WHERE status='completed'")
    row = c.fetchone(); total_services = row[0]; total_revenue = row[1]
    c.execute("""SELECT i.nama, i.kategori, SUM(l.biaya_sparepart) as total, COUNT(*) as cnt
        FROM log_service l JOIN inventory_sparepart i ON l.inventory_id = i.id
        WHERE l.created_at >= datetime('now','-30 days') AND l.status='completed' AND l.inventory_id IS NOT NULL
        GROUP BY i.id ORDER BY total DESC LIMIT 5""")
    top_parts = c.fetchall()
    c.execute("""SELECT i.kategori, COUNT(*) as cnt FROM log_service l
        JOIN inventory_sparepart i ON l.inventory_id = i.id
        WHERE l.created_at >= datetime('now','-30 days') GROUP BY i.kategori ORDER BY cnt DESC""")
    cat_stats = c.fetchall()
    c.execute("""SELECT strftime('%Y-%m-%d', created_at) as day, SUM(total_biaya) as revenue
        FROM log_service WHERE status='completed' AND created_at >= datetime('now','-30 days')
        GROUP BY day ORDER BY day""")
    daily_rev = c.fetchall()
    c.execute("""SELECT tipe_service, COUNT(*) as cnt FROM log_service
        WHERE created_at >= datetime('now','-30 days') GROUP BY tipe_service""")
    stype_stats = c.fetchall()
    conn.close()
    lines = [f"LAPORAN ANALISIS KEUANGAN — {datetime.now().strftime('%B %Y')}", "="*50]
    lines.append(f"Total Service Selesai: {total_services} transaksi")
    lines.append(f"Total Pendapatan: Rp {total_revenue:,.0f}")
    if total_services > 0: lines.append(f"Rata-rata: Rp {total_revenue/total_services:,.0f}")
    if stype_stats:
        lines.append(f"\nTIPE SERVICE:")
        total_t = sum(r[1] for r in stype_stats)
        for t, cnt in stype_stats: lines.append(f"  {t.upper():20s}: {cnt}x ({cnt/total_t*100:.0f}%)")
    if top_parts:
        lines.append(f"\nTOP 5 SPAREPART TERLARIS (30 hari):")
        for i, row in enumerate(top_parts, 1):
            lines.append(f"  {i}. {row[0][:30]} — Rp {row[2]:,.0f} ({row[1]}) — {row[3]}x")
    if cat_stats:
        lines.append(f"\nTREN KATEGORI KERUSAKAN (30 hari):")
        total_cat = sum(r[1] for r in cat_stats)
        for cat, cnt in cat_stats:
            pct = cnt/total_cat*100 if total_cat else 0
            lines.append(f"  {cat.upper():15s} {'█'*int(pct/5)} {cnt}x ({pct:.0f}%)")
    lines.append(f"\nINSIGHT OTOMATIS:")
    if cat_stats:
        top_cat = cat_stats[0]
        lines.append(f"  Kategori {top_cat[0].upper()} paling sering diperbaiki ({top_cat[1]} kasus).")
        rekom_stok = {"lcd":"LCD","battery":"Baterai","ic_power":"IC Power","flex_cable":"Fleksibel"}
        lines.append(f"  Disarankan tambah stok {rekom_stok.get(top_cat[0],top_cat[0])}.")
    if top_parts: lines.append(f"  {top_parts[0][0][:30]} paling laku — pastikan stok cukup.")
    if daily_rev:
        revs = [r[1] for r in daily_rev]
        lines.append(f"  Tren revenue: {'naik' if revs[-1]>revs[0] else 'turun'} (rata2 Rp {sum(revs)/len(revs):,.0f}/hari).")
    return "\n".join(lines)


def create_zip():
    try:
        with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(__file__, os.path.basename(__file__))
            if os.path.exists(DB_PATH): zf.write(DB_PATH, os.path.basename(DB_PATH))
            for f in ["requirements.txt","main.py"]:
                fp = str(BASE_DIR / f)
                if os.path.exists(fp): zf.write(fp, f)
            for dname in ["core","cli","streamlit_app"]:
                dpath = BASE_DIR / dname
                if dpath.exists():
                    for cf in dpath.rglob("*.py"):
                        zf.write(str(cf), str(cf.relative_to(BASE_DIR)))
        return True, ZIP_PATH
    except Exception as e:
        return False, str(e)


def copy_to_sdcard():
    if not os.path.exists(ZIP_PATH): return False, "File ZIP belum ada."
    for dest in ["/sdcard/Download/","/storage/emulated/0/Download/","/mnt/sdcard/Download/","/data/media/0/Download/"]:
        try:
            subprocess.run(["cp", ZIP_PATH, dest], capture_output=True, timeout=10)
            if os.path.exists(os.path.join(dest, ZIP_NAME)):
                return True, f"Tersimpan di {dest}{ZIP_NAME}"
        except Exception: pass
    try:
        subprocess.run(["adb","push",ZIP_PATH,"/sdcard/Download/"], capture_output=True, text=True, timeout=15)
        return True, f"Terkirim via ADB ke /sdcard/Download/{ZIP_NAME}"
    except Exception: pass
    return False, "Tidak dapat menyalin. /sdcard tidak tersedia."


USB_VENDOR_DB = {
    "05c6": {"name": "Qualcomm", "modes": {"9008": "EDL Mode (Qualcomm HS-USB QDLoader 9008)", "900e": "EDL Mode (Qualcomm HS-USB Diagnostics 900E)"}},
    "18d1": {"name": "Google/Android", "modes": {"4ee0": "Fastboot Mode", "4ee1": "Fastboot Mode", "d001": "ADB Mode", "4ee7": "Android"}},
    "0bb4": {"name": "HTC", "modes": {"0c01": "Fastboot Mode"}},
    "04e8": {"name": "Samsung", "modes": {"1234": "Fastboot Mode", "6601": "Download Mode (Odin)"}},
    "2717": {"name": "Xiaomi", "modes": {"ff48": "Fastboot Mode", "ff90": "EDL Mode"}},
    "12d1": {"name": "Huawei", "modes": {"3609": "Fastboot Mode", "360b": "Hisuite Mode"}},
    "0fce": {"name": "Sony", "modes": {"0dde": "Fastboot Mode"}},
    "22b8": {"name": "Motorola", "modes": {"2e71": "Fastboot Mode"}},
    "2c02": {"name": "OnePlus/Oppo", "modes": {"f004": "EDL Mode"}},
    "0e8d": {"name": "MediaTek", "modes": {"2000": "Preloader Mode", "0003": "BROM Mode"}},
    "1d6b": {"name": "Linux Foundation", "modes": {"0102": "Mass Storage"}},
    "05ac": {"name": "Apple", "modes": {"1227": "iPhone DFU Mode", "1222": "iPhone Recovery Mode", "1220": "iPhone Normal Mode", "1281": "iPhone Recovery Mode (A6)"}},
}


def detect_usb_devices_linux() -> list:
    ok, out, _ = _run(["lsusb"], timeout=5)
    if not ok:
        return []
    results = []
    for line in out.splitlines():
        m = re.search(r'ID\s+(\w{4}):(\w{4})\s+(.+)', line)
        if m:
            vid, pid, desc = m.group(1).lower(), m.group(2).lower(), m.group(3).strip()
            match = USB_VENDOR_DB.get(vid, {})
            mode_name = "Unknown"
            if match:
                mode_name = match["modes"].get(pid, f"{match['name']} Device ({desc})") if "modes" in match else desc
            results.append({"vid": vid, "pid": pid, "desc": desc, "mode": mode_name, "vendor": match.get("name", "Unknown")})
    return results


def detect_usb_devices_windows() -> list:
    ps_script = """
    Get-PnpDevice -PresentOnly | Where-Object {$_.Class -eq 'Ports' -or $_.Class -eq 'USB' -or $_.Class -eq 'WPD'} |
    Select-Object FriendlyName, DeviceID, Class | ConvertTo-Json
    """
    try:
        r = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return []
        import json as _json
        data = _json.loads(r.stdout)
        if not isinstance(data, list):
            data = [data] if data else []
        results = []
        for d in data:
            friendly = d.get("FriendlyName", "")
            dev_id = d.get("DeviceID", "")
            vid_m = re.search(r'VID_(\w{4})', dev_id, re.I)
            pid_m = re.search(r'PID_(\w{4})', dev_id, re.I)
            vid = vid_m.group(1).lower() if vid_m else ""
            pid = pid_m.group(1).lower() if pid_m else ""
            match = USB_VENDOR_DB.get(vid, {})
            mode_name = "Unknown"
            if match:
                mode_name = match["modes"].get(pid, f"{match['name']} Device") if "modes" in match else friendly
            results.append({"vid": vid, "pid": pid, "desc": friendly, "mode": mode_name, "vendor": match.get("name", "Unknown")})
        return results
    except Exception:
        return []


def dead_phone_scan() -> dict:
    fb_devs = fastboot_devices()
    usb_devs = detect_usb_devices_linux() if os.name != "nt" else detect_usb_devices_windows()
    adb_devs = adb_devices()
    results = {
        "fastboot_devices": fb_devs,
        "adb_devices": adb_devs,
        "usb_devices": usb_devs,
        "recovery_adb": [],
        "recovery_manual_candidates": [],
        "edl_devices": [],
        "dfu_devices": [],
        "summary": "",
    }
    for d in usb_devs:
        if "EDL" in d["mode"] or d["pid"] in ["9008", "900e", "ff90", "f004"]:
            results["edl_devices"].append(d)
        if "DFU" in d["mode"] or d["pid"] in ["1227"]:
            results["dfu_devices"].append(d)
        if "Preloader" in d["mode"] or d["pid"] == "2000":
            results["edl_devices"].append(d)
    for s in adb_devs:
        ok, out, _ = adb_shell(s, "getprop ro.bootmode")
        if ok and "recovery" in out.lower():
            results["recovery_adb"].append(s)
    total = len(fb_devs) + len(results["edl_devices"]) + len(results["dfu_devices"]) + len(adb_devs)
    parts = []
    if fb_devs:
        parts.append(f"{len(fb_devs)} Fastboot")
    if results["edl_devices"]:
        parts.append(f"{len(results['edl_devices'])} EDL")
    if results["dfu_devices"]:
        parts.append(f"{len(results['dfu_devices'])} DFU")
    if adb_devs:
        parts.append(f"{len(adb_devs)} ADB")
    results["summary"] = f"Terdeteksi {total} device: {', '.join(parts)}" if parts else "Tidak ada device terdeteksi."
    conn = get_conn()
    c = conn.cursor()
    for d in results["edl_devices"]:
        c.execute("INSERT INTO dead_phone_log (detected_mode,vendor,vid_pid) VALUES('edl',?,?)", (d["vendor"], f"{d['vid']}:{d['pid']}"))
    for d in results["dfu_devices"]:
        c.execute("INSERT INTO dead_phone_log (detected_mode,vendor,vid_pid) VALUES('dfu',?,?)", (d["vendor"], f"{d['vid']}:{d['pid']}"))
    for s in fb_devs:
        c.execute("INSERT INTO dead_phone_log (detected_mode,serial) VALUES('fastboot',?)", (s,))
    conn.commit()
    conn.close()
    return results


def sha256_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def backup_partition_fastboot(serial: str, partition: str, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{partition}.img")
    ok, out, err = _run(["fastboot", "-s", serial, "flash:raw", out_path, partition], timeout=30)
    if not ok:
        return {"partition": partition, "file": "", "size_bytes": 0, "sha256": "", "status": "failed", "error": err}
    sha = sha256_file(out_path)
    sz = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    res = {"partition": partition, "file": out_path, "size_bytes": sz, "sha256": sha, "status": "ok", "error": ""}
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO backup_log (device_serial,platform,mode,partition_name,file_path,file_size_bytes,sha256_before,status) VALUES(?,?,'fastboot',?,?,?,?,'completed')",
              (serial, "android", partition, out_path, sz, sha))
    conn.commit()
    conn.close()
    return res


def backup_partition_adb(serial: str, partition: str, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{partition}.img")
    ok, out, err = adb_shell(serial, f"dd if=/dev/block/bootdevice/by-name/{partition} of=/data/local/tmp/{partition}.img 2>/dev/null")
    if not ok:
        ok, out, err = adb_shell(serial, f"su -c 'dd if=/dev/block/bootdevice/by-name/{partition} of=/data/local/tmp/{partition}.img' 2>/dev/null")
    if not ok:
        ok, out, err = adb_shell(serial, f"cat /dev/block/by-name/{partition} > /data/local/tmp/{partition}.img 2>/dev/null")
    if not ok:
        return {"partition": partition, "file": "", "size_bytes": 0, "sha256": "", "status": "failed", "error": err}
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO backup_log (device_serial,platform,mode,partition_name,status) VALUES(?,?,'adb',?,'pending')",
              (serial, "android", partition))
    conn.commit()
    conn.close()
    return {"partition": partition, "file": f"/data/local/tmp/{partition}.img", "size_bytes": 0, "sha256": "", "status": "ok", "error": ""}


def auto_backup(serial: str, platform: str = "android") -> dict:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = str(BASE_DIR / "backups" / f"{serial}_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)
    results = []
    if platform == "android":
        fastboot_mode = False
        if serial in fastboot_devices():
            fastboot_mode = True
        partitions = ["persist", "efs", "nvram", "modem", "boot", "recovery", "misc", "fsg"]
        if fastboot_mode:
            for p in partitions:
                r = backup_partition_fastboot(serial, p, output_dir)
                results.append(r)
        else:
            for p in partitions:
                r = backup_partition_adb(serial, p, output_dir)
                results.append(r)
    elif platform == "ios":
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO backup_log (device_serial,platform,mode,partition_name,status) VALUES(?,?,'libimobiledevice','full_backup','pending')",
                  (serial, "ios"))
        conn.commit()
        conn.close()
        ok, out, err = _run(["idevicebackup2", "-u", serial, "backup", "--full", output_dir], timeout=120)
        results.append({"partition": "full_backup", "file": output_dir, "size_bytes": 0, "sha256": "", "status": "ok" if ok else "failed", "error": err})
    summary = f"Backup {platform}: {len([r for r in results if r['status']=='ok'])}/{len(results)} berhasil"
    sha = sha256_file(os.path.join(output_dir, "backup_summary.sha256")) if results else ""
    return {"output_dir": output_dir, "results": results, "summary": summary, "sha256": sha}


def detect_device_for_flash() -> dict:
    adb_d = adb_devices()
    fb_d = fastboot_devices()
    dead = dead_phone_scan()
    info = {"platform": "", "serial": "", "model": "", "chipset": "", "android": "", "bootloader": "", "mode": "unknown", "sources": [], "detected": False}
    if adb_d:
        s = adb_d[0]
        info["serial"] = s
        info["platform"] = "android"
        info["mode"] = "adb"
        info["model"] = adb_getprop(s, "ro.product.model")
        info["chipset"] = adb_getprop(s, "ro.board.platform")
        info["android"] = adb_getprop(s, "ro.build.version.release")
        info["bootloader"] = adb_getprop(s, "ro.bootloader")
        info["detected"] = True
        info["sources"].append("adb")
    elif fb_d:
        s = fb_d[0]
        info["serial"] = s
        info["platform"] = "android"
        info["mode"] = "fastboot"
        info["model"] = fastboot_getvar(s, "product") or adb_getprop(s, "ro.product.model")
        info["bootloader"] = fastboot_getvar(s, "version-bootloader") or ""
        info["detected"] = True
        info["sources"].append("fastboot")
    elif dead["edl_devices"]:
        d = dead["edl_devices"][0]
        info["serial"] = f"{d['vid']}:{d['pid']}"
        info["platform"] = "android"
        info["mode"] = "edl"
        info["model"] = f"EDL Device ({d['vendor']})"
        info["chipset"] = "Qualcomm" if d["vid"] == "05c6" else ("MediaTek" if d["vid"] == "0e8d" else "Unknown")
        info["detected"] = True
        info["sources"].append("edl")
    elif dead["dfu_devices"]:
        d = dead["dfu_devices"][0]
        info["serial"] = f"{d['vid']}:{d['pid']}"
        info["platform"] = "ios"
        info["mode"] = "dfu"
        info["model"] = "iPhone (DFU Mode)"
        info["detected"] = True
        info["sources"].append("dfu")
    if info["detected"]:
        info["firmware_urls"] = firmware_urls(info["model"], info["chipset"])
    return info


def verify_firmware_file(filepath: str, device_info: dict) -> dict:
    model = device_info.get("model", "").lower()
    chipset = device_info.get("chipset", "").lower()
    result = {"valid": False, "match_score": 0, "reason": "", "detected_model": "", "file_size_mb": 0, "is_zip": False, "checks": []}
    if not os.path.exists(filepath):
        result["reason"] = "File tidak ditemukan."
        return result
    fsize = os.path.getsize(filepath)
    result["file_size_mb"] = round(fsize / (1024 * 1024), 1)
    if fsize < 1024 * 1024:
        result["reason"] = f"File terlalu kecil ({result['file_size_mb']} MB) — bukan firmware."
        result["checks"].append("size:FAIL")
        return result
    result["checks"].append(f"size:PASS ({result['file_size_mb']} MB)")
    if not zipfile.is_zipfile(filepath):
        result["reason"] = "File bukan ZIP valid."
        result["checks"].append("zip:FAIL")
        return result
    result["is_zip"] = True
    result["checks"].append("zip:PASS")
    score = 0
    detected_model = ""
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            names = [n.lower() for n in zf.namelist()]
            has_img = any(n.endswith(".img") for n in names)
            has_bin = any(n.endswith(".bin") for n in names)
            has_updater = any("updater-script" in n for n in names)
            has_android_info = any("android-info" in n for n in names)
            firmware_indicators = [has_img, has_bin, has_updater, has_android_info]
            fw_count = sum(firmware_indicators)
            if fw_count >= 2:
                score += 40
                result["checks"].append(f"firmware_structure:PASS ({fw_count}/4 indicators)")
            else:
                result["checks"].append(f"firmware_structure:WEAK ({fw_count}/4 indicators)")
        model_slugs = model.replace(" ", "").replace("-", "").lower() if model else ""
        name_text = " ".join(names)
        chipset_slugs = chipset.replace(" ", "").replace("-", "").lower() if chipset else ""
        model_match = 0
        if model_slugs:
            if re.search(re.escape(model_slugs[:8]), name_text, re.I):
                model_match = 1
            elif re.search(re.escape(model_slugs[:6]), name_text, re.I):
                model_match = 1
            if model_match:
                score += 30
                result["checks"].append(f"model_match:PASS (model terdeteksi di dalam file)")
            else:
                if has_updater:
                    try:
                        us = zf.read([n for n in zf.namelist() if "updater-script" in n.lower()][0]).decode("utf-8", errors="ignore")
                        m = re.search(r'getprop\("ro\.product\.device"\)\s*==\s*"(\w+)"', us)
                        if m:
                            detected_model = m.group(1)
                            if (detected_model.lower() in model_slugs or model_slugs[:6] in detected_model.lower()):
                                score += 30
                                result["checks"].append(f"model_updater:PASS ({detected_model})")
                            else:
                                result["checks"].append(f"model_updater:WRONG ({detected_model} ≠ {model[:20]})")
                    except Exception:
                        result["checks"].append(f"model_updater:SKIP")
                result["checks"].append(f"model_match:WARN (model '{model[:20]}' tidak ditemukan di file)")
        if chipset_slugs and len(chipset_slugs) > 3:
            if chipset_slugs in name_text:
                score += 10
                result["checks"].append(f"chipset_match:PASS")
        has_fastboot_img = any(n.endswith((".img", ".bin")) and "boot" in n for n in names)
        has_system_img = any("system" in n and n.endswith((".img", ".new", ".dat")) for n in names)
        if has_fastboot_img:
            score += 10
            if has_system_img:
                score += 10
            result["detected_model"] = detected_model
    except Exception as e:
        result["reason"] = f"Error membaca ZIP: {e}"
        result["checks"].append(f"zip_read:FAIL ({e})")
        return result
    result["match_score"] = min(score, 100)
    if result["match_score"] >= 60:
        result["valid"] = True
        result["reason"] = f"Firmware COCOK ({result['match_score']}%) — siap flashing."
    elif result["match_score"] >= 30:
        result["valid"] = False
        result["reason"] = f"Firmware MIRIP ({result['match_score']}%) — perlu konfirmasi manual."
    else:
        result["valid"] = False
        result["reason"] = f"Firmware TIDAK COCOK ({result['match_score']}%) — cari firmware lain."
    return result


def flash_partition_fastboot(serial: str, partition: str, image_path: str) -> dict:
    if not os.path.exists(image_path):
        return {"partition": partition, "status": "failed", "error": f"File {image_path} tidak ditemukan."}
    fsize = os.path.getsize(image_path)
    st.info(f"Flash {partition} ({fsize//1024//1024} MB)...")
    ok, out, err = _run(["fastboot", "-s", serial, "flash", partition, image_path], timeout=120)
    if ok:
        return {"partition": partition, "status": "ok", "output": out[:200]}
    else:
        return {"partition": partition, "status": "failed", "error": err[:200]}


SAFETY_RULES = {
    "battery_min_pct": {"android": 50, "ios": 50, "desc": "Baterai minimal 50% sebelum flash"},
    "usb_cable_check": {"desc": "Pastikan kabel data sync (bukan charge-only). Gunakan kabel original."},
    "backup_required": {"desc": "Backup partisi penting (persist, efs, nvram, modem, boot, recovery)."},
    "driver_check": {"desc": "Pastikan driver ADB/Fastboot terinstall dengan benar."},
    "model_match": {"desc": "Firmware harus cocok dengan model device (verified ≥60%)."},
    "variant_match": {"desc": "Periksa varian device (global/CN/IN/EU) — firmware antar varian beda."},
    "android_version": {"desc": "Firmware harus untuk Android version yang sama atau lebih baru."},
    "anti_rollback": {"desc": "Periksa ARB (Anti-Rollback) — downgrade bisa hardbrick pada device dengan ARB."},
    "bootloader_unlock": {"desc": "Beberapa partisi hanya bisa di-flash jika bootloader UNLOCKED."},
    "space_check": {"desc": "Pastikan PC/laptop memiliki ruang disk yang cukup untuk backup."},
}


def check_battery_level(serial: str) -> dict:
    info = {"level": -1, "ok": False, "detail": "Tidak dapat membaca baterai."}
    try:
        ok, out, _ = adb_shell(serial, "dumpsys battery | grep level")
        if ok:
            m = re.search(r'level:\s*(\d+)', out)
            if m:
                info["level"] = int(m.group(1))
                info["ok"] = info["level"] >= SAFETY_RULES["battery_min_pct"]["android"]
                info["detail"] = f"Baterai: {info['level']}% — {'OK' if info['ok'] else 'ISI DULU!'}"
                return info
    except Exception:
        pass
    try:
        ok, out, _ = _run(["fastboot", "-s", serial, "getvar", "battery-voltage"], timeout=5)
        if ok and out.strip():
            info["detail"] = "Device di Fastboot — voltase terdeteksi"
            info["ok"] = True
            return info
    except Exception:
        pass
    return info


def check_usb_stability(serial: str, retries: int = 3) -> dict:
    results = []
    is_adb = serial in adb_devices()
    is_fastboot = serial in fastboot_devices() if not is_adb else False
    for i in range(retries):
        t1 = time.time()
        if is_adb:
            ok, _, _ = _run(["adb", "-s", serial, "get-state"], timeout=5)
        elif is_fastboot:
            ok, _, _ = _run(["fastboot", "-s", serial, "getvar", "battery-voltage"], timeout=5)
        else:
            ok = False
        t2 = time.time()
        results.append({"ok": ok, "latency_ms": round((t2 - t1) * 1000)})
    success_rate = sum(1 for r in results if r["ok"]) / len(results)
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    stable = success_rate >= 0.66 and avg_latency < 2000
    return {"stable": stable, "success_rate": round(success_rate * 100), "avg_latency_ms": round(avg_latency), "checks": results}


def pre_flash_safety_check(serial: str, mode: str = "adb") -> dict:
    checks = []
    device_model = adb_getprop(serial, "ro.product.model") if mode == "adb" else ""
    battery = check_battery_level(serial)
    checks.append({"name": "Battery Level", "pass": battery["ok"], "detail": battery["detail"]})
    if mode == "adb":
        usb = check_usb_stability(serial, 2)
        checks.append({"name": "USB Stability", "pass": usb["stable"], "detail": f"Rate: {usb['success_rate']}%, Latency: {usb['avg_latency_ms']}ms"})
    devs = fastboot_devices() if mode == "fastboot" else adb_devices()
    checks.append({"name": f"Device Connected ({mode})", "pass": serial in devs, "detail": f"Device {serial}: {'TERDETEKSI' if serial in devs else 'HILANG!'}"})
    adb_bootloader = adb_getprop(serial, "ro.boot.bootloader") if mode == "adb" else fastboot_getvar(serial, "version-bootloader")
    checks.append({"name": "Bootloader Detected", "pass": bool(adb_bootloader), "detail": f"Bootloader: {adb_bootloader or 'Tidak terdeteksi'}"})
    arb_result = get_arb_level(device_model or serial)
    checks.append({"name": "Anti-Rollback Check", "pass": arb_result["level"] < 7, "detail": f"ARB Level: {arb_result['level']} — {arb_result['note']}"})
    all_pass = all(c["pass"] for c in checks)
    for c in checks:
        conn = get_conn()
        curr = conn.cursor()
        curr.execute("INSERT INTO safety_checklist (device_serial,check_type,check_name,result,detail) VALUES(?,?,?,?,?)",
                     (serial, "pre_flash", c["name"], 1 if c["pass"] else 0, c["detail"]))
        conn.commit()
        conn.close()
    return {"all_pass": all_pass, "checks": checks, "summary": f"Safety Check: {sum(1 for c in checks if c['pass'])}/{len(checks)} passed"}


def emergency_recovery_guide(mode: str = "") -> list:
    guides = {
        "edl_9008": [
            "Device terdeteksi sebagai EDL 9008 — masih ada harapan.",
            "1. Install Qualcomm USB Driver (QPST/QFIL).",
            "2. Buka QFIL → pilih 'Flat Build' → browse Programmer Path (.elf file untuk chipset kamu).",
            "3. Klik 'Download' atau 'Do job' → tunggu proses selesai.",
            "4. Jika tidak masuk QFIL: coba short testpoint lagi sambil colok USB.",
            "5. Alternatif: gunakan 'EDL Cable' atau 'Deep Flash Cable' untuk bypass.",
        ],
        "mtk_preloader": [
            "Device terdeteksi sebagai MediaTek Preloader.",
            "1. Install MediaTek USB VCOM driver.",
            "2. Buka SP Flash Tool → pilih Scatter File dari firmware.",
            "3. Centang partisi yang ingin di-flash (jangan centang preloader jika tidak perlu).",
            "4. Klik 'Download' → colok device (tanpa baterai untuk MTK).",
            "5. Tunggu progress bar sampai selesai (format kuning → hijau).",
        ],
        "fastboot_unbrick": [
            "Device dalam mode Fastboot — bisa diperbaiki.",
            "1. Backup partisi dulu: persist, efs, nvram, modem, boot, recovery.",
            "2. Cari firmware yang cocok (model + varian harus sama persis!).",
            "3. Flash partisi satu per satu: boot, recovery, system, vendor.",
            "4. Jika system error: flash 'super' partition (untuk device dynamic partition).",
            "5. Jika stuck di logo: wipe data via recovery atau `fastboot -w`.",
            "6. Terakhir: `fastboot reboot`.",
        ],
        "dfu_recovery": [
            "iPhone dalam mode DFU / Recovery.",
            "1. Buka Finder (macOS) atau iTunes (Windows).",
            "2. Akan muncul notifikasi 'iPhone detected in recovery mode'.",
            "3. Klik 'Restore' atau 'Update' — pilih IPSW firmware yang cocok.",
            "4. Untuk keluar dari DFU tanpa restore: tekan Vol Up + Vol Down + Side (Face ID) atau Home + Power (Tombol Home).",
            "5. Jika restore gagal: coba DFU mode lagi, ganti kabel, ganti port USB.",
        ],
        "black_screen": [
            "Device hidup (ada getar/led) tapi layar hitam.",
            "1. Coba paksa restart: Vol Down + Power 15 detik.",
            "2. Jika ada getar: kemungkinan LCD rusak — ganti LCD.",
            "3. Jika tidak ada getar: coba colok charger — jika ada LED, kemungkinan IC Power.",
            "4. Coba masuk Recovery: Vol Up + Power (atau kombinasi sesuai brand).",
            "5. Jika masuk Recovery: backup data, lalu flash ulang.",
        ],
        "bootloop": [
            "Device restart terus-menerus (bootloop).",
            "1. Coba masuk Safe Mode (untuk Samsung: Vol Down saat boot logo).",
            "2. Jika bisa masuk Safe Mode: hapus app bermasalah (yang baru diinstall).",
            "3. Wipe cache partition dari Recovery Mode.",
            "4. Jika masih bootloop: factory reset dari Recovery.",
            "5. Jika masih: flash ulang firmware via fastboot/ODIN/SP Flash Tool.",
            "6. Pastikan tidak melakukan downgrade jika device punya ARB!",
        ],
        "no_download_mode": [
            "Device tidak bisa masuk Download Mode / EDL.",
            "1. Coba kombinasi tombol yang benar: Vol Down + Vol Up + colok USB (Qualcomm).",
            "2. Untuk MTK: colok USB tanpa baterai, tekan Vol Up + Vol Down lalu colok.",
            "3. Coba testpoint EDL: buka casing, cari 2 titik tembaga kecil di dekat IC Power.",
            "4. Gunakan 'EDL Cable' (kabel USB dengan resistor 2.2k ohm khusus).",
            "5. Alternatif: gunakan 'Deep Flash Cable' atau 'Brom Bypass' untuk MTK.",
        ],
    }
    if mode and mode in guides:
        return guides[mode]
    return guides


def log_flash_transaction(serial: str, model: str, partition: str, firmware: str, verified: bool, status: str, error: str = ""):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO flash_log (device_serial,device_model,partition_name,firmware_file,
        firmware_verified,status,error_log) VALUES(?,?,?,?,?,?,?)""",
              (serial, model, partition, firmware, 1 if verified else 0, status, error))
    conn.commit()
    conn.close()


init_database()

st.markdown("""<style>
    :root {
        --bg-primary: #FAFAF8;
        --bg-card: #FFFFFF;
        --bg-sidebar: #1A1A1A;
        --text-primary: #1A1A1A;
        --text-secondary: #6B7280;
        --text-muted: #9CA3AF;
        --accent-gold: #C9A84C;
        --accent-blue: #2563EB;
        --accent-blue-hover: #1D4ED8;
        --success: #059669;
        --warning: #D97706;
        --error: #DC2626;
    }
    .stApp { background-color: var(--bg-primary); }
    .main > div { padding: 1.5rem 2rem; }
    h1, h2, h3 { color: var(--text-primary) !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    h1 { font-size: 1.75rem !important; } h2 { font-size: 1.35rem !important; }
    section[data-testid="stSidebar"] { background-color: var(--bg-sidebar); min-width: 260px; }
    section[data-testid="stSidebar"] .stMarkdown { color: #FFFFFF; }
    .sidebar-logo { padding: 1.5rem 1.2rem 0.8rem; border-bottom: 1px solid #2D2D2D; margin-bottom: 1rem; }
    .sidebar-logo h2 { color: var(--accent-gold) !important; font-size: 1.1rem; margin: 0; letter-spacing: 0.5px; }
    .sidebar-logo p { color: var(--text-muted); font-size: 0.7rem; margin: 0.2rem 0 0 0; }
    section[data-testid="stSidebar"] .stRadio { gap: 2px !important; }
    section[data-testid="stSidebar"] .stRadio > label {
        color: var(--text-muted) !important; padding: 0.6rem 1.2rem; border-radius: 6px;
        font-size: 0.85rem; font-weight: 500; margin: 1px 0; border-left: 3px solid transparent;
        transition: all 0.2s ease;
    }
    section[data-testid="stSidebar"] .stRadio > label:hover {
        background: rgba(255,255,255,0.06); color: #FFF !important;
    }
    section[data-testid="stSidebar"] .stRadio > label[data-checked="true"] {
        background: rgba(201,168,76,0.1); border-left: 3px solid var(--accent-gold); color: var(--accent-gold) !important;
    }
    .sidebar-footer { padding: 1rem 1.2rem; border-top: 1px solid #2D2D2D; margin-top: auto; }
    .section-header { color: #4B5563; font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; padding: 0.5rem 1.2rem 0.3rem; }
    .card { background: var(--bg-card); border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.2rem; box-shadow: 0 1px 2px rgba(0,0,0,0.04); margin-bottom: 0.8rem; transition: box-shadow 0.2s ease; }
    .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .card-gold { border-left: 4px solid var(--accent-gold); }
    .card-blue { border-left: 4px solid var(--accent-blue); }
    .card-red { border-left: 4px solid var(--error); }
    .card-green { border-left: 4px solid var(--success); }
    .banner-critical { background: linear-gradient(135deg, var(--error), #991B1B); color: white; padding: 0.8rem 1.2rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; font-size: 0.9rem; }
    .banner-warning { background: linear-gradient(135deg, var(--warning), #92400E); color: white; padding: 0.8rem 1.2rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; font-size: 0.9rem; }
    .banner-success { background: linear-gradient(135deg, var(--success), #065F46); color: white; padding: 0.8rem 1.2rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; font-size: 0.9rem; }
    .banner-info { background: linear-gradient(135deg, var(--accent-blue), #1E40AF); color: white; padding: 0.8rem 1.2rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; font-size: 0.9rem; }
    div[data-testid="stMetric"] { background: white; padding: 1rem 1.2rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #E5E7EB; }
    div[data-testid="stMetric"] label { color: var(--text-secondary) !important; font-weight: 600 !important; font-size: 0.8rem !important; }
    div[data-testid="stMetric"] div { color: var(--text-primary) !important; font-weight: 700 !important; }
    div[data-testid="stTabs"] button { font-weight: 600; font-size: 0.85rem; }
    div[data-testid="stTabs"] button[aria-selected="true"] { border-bottom: 2px solid var(--accent-gold); color: var(--accent-gold); }
    [data-testid="stSidebar"] button[kind="primary"] { background: var(--accent-gold); color: #1A1A1A; font-weight: 600; border: none; }
    [data-testid="stSidebar"] button[kind="primary"]:hover { background: #B8943A; }
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""<div class="sidebar-logo">
        <h2>✦ Smart Service HP</h2>
        <p>Workstation v4.0 — AI-Powered</p>
    </div>""", unsafe_allow_html=True)
    _dev_status = adb_device_status()
    _fb = fastboot_devices()
    if _dev_status["unauthorized"]:
        st.markdown(f"<div style='background:#DC2626;color:white;padding:6px 10px;border-radius:6px;font-size:0.75rem;margin-bottom:8px;'>🔒 Unauthorized!<br><small>Buka HP → izinkan USB Debugging</small></div>", unsafe_allow_html=True)
    if _dev_status["authorized"]:
        _s = _dev_status["authorized"][0]
        _m = adb_getprop(_s, "ro.product.model") or _s
        _a = auto_read_ampere_adb(_s)
        if _a["ampere"] > 0:
            st.markdown(f"<div style='background:#1A1A2E;color:#C9A84C;padding:6px 10px;border-radius:6px;font-size:0.8rem;margin-bottom:4px;font-weight:bold;'>⚡ {_a['ampere']:.4f}A @ {_a['voltage']:.2f}V</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='background:#059669;color:white;padding:6px 10px;border-radius:6px;font-size:0.75rem;margin-bottom:8px;'>📱 {_m}<br><small>ADB: {_s[:12]}…</small></div>", unsafe_allow_html=True)
    elif _fb:
        st.markdown(f"<div style='background:#2563EB;color:white;padding:6px 10px;border-radius:6px;font-size:0.75rem;margin-bottom:8px;'>⚡ Fastboot: {_fb[0][:16]}…</div>", unsafe_allow_html=True)
    elif not _dev_status["unauthorized"]:
        st.markdown(f"<div style='background:#4B5563;color:#9CA3AF;padding:6px 10px;border-radius:6px;font-size:0.75rem;margin-bottom:8px;'>📵 No device detected</div>", unsafe_allow_html=True)

    menu = "Dashboard"
    _submenu_options = {
        "📊 Dashboard": ["Dashboard"],
        "🔧 Service": ["Check-In & Diagnosis", "Manajemen Tiket Service", "Ampere & Baterai", "Hardware Diagnosis (Windows)"],
        "📱 Device Scanner": ["Deep ADB Scanner (Android)", "iOS Scanner (iPhone)", "Dead Phone Scanner", "Network Scan (PC/Laptop)"],
        "🛠️ Repair Tools": ["Flash Wizard", "Auto Backup & Restore", "Pre-Flashing Security", "Recovery & Testpoint Guide", "Emergency Recovery Guide", "Deep Cache Cleaner"],
        "📦 Inventory & Finance": ["Inventory & Financial", "Cari Firmware"],
    }
    _categories = list(_submenu_options.keys())
    st.markdown("<div class='section-header'>Navigasi</div>", unsafe_allow_html=True)
    category = st.radio("KATEGORI", _categories, label_visibility="collapsed")

    if "_submenu_init" not in st.session_state:
        st.session_state["_submenu_init"] = True
        for cat, opts in _submenu_options.items():
            st.session_state[f"_submenu_{cat}"] = opts[0]

    if category == "📊 Dashboard":
        menu = "Dashboard"
    else:
        _opts = _submenu_options[category]
        _key = f"_submenu_{category}"
        _saved = st.session_state.get(_key, _opts[0])
        if _saved in _opts:
            _idx = _opts.index(_saved)
        else:
            _idx = 0
        menu = st.selectbox("", _opts, index=_idx, label_visibility="collapsed", key=_key)
        st.markdown(f"<div style='color:#C9A84C;font-size:0.65rem;padding:2px 0 4px 4px;'>▸ {category.split()[1]} {_opts.index(menu)+1}/{len(_opts)}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#2D2D2D;margin:0.8rem 0;'>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Device", use_container_width=True, help="Scan ulang koneksi device"):
        st.rerun()
    st.markdown("<p style='color:#4B5563;font-size:0.7rem;padding:0 1.2rem;'>© 2026 Smart Service HP<br>AI-Powered Cross-Platform</p>", unsafe_allow_html=True)

def _auto_detect_device():
    """Deteksi device otomatis — ADB, Fastboot, EDL, DFU."""
    adb = adb_devices()
    fb = fastboot_devices()
    usb = detect_usb_devices_linux() if os.name != "nt" else detect_usb_devices_windows()
    edl = [d for d in usb if "EDL" in d["mode"] or d["pid"] in ["9008", "900e", "ff90", "f004"]]
    dfu = [d for d in usb if "DFU" in d["mode"] or d["pid"] in ["1227"]]
    ios = idevice_devices() if check_idevice_installed() else []
    return {"adb": adb, "fastboot": fb, "edl": edl, "dfu": dfu, "ios": ios}

if menu == "Dashboard":
    st.title("Dashboard")
    with st.container():
        dev = _auto_detect_device()
        _dash_amp = auto_detect_ampere()
        status_cols = st.columns([1, 1, 1, 1, 1, 1], vertical_alignment="center")
        status_cols[0].markdown(f"<div class='card' style='text-align:center;padding:0.4rem'><span style='font-size:1.2rem;'>{'📱' if dev['adb'] else '📵'}</span><br><small>{'ADB: ' + str(len(dev['adb'])) if dev['adb'] else 'ADB: -'}</small></div>", unsafe_allow_html=True)
        status_cols[1].markdown(f"<div class='card' style='text-align:center;padding:0.4rem'><span style='font-size:1.2rem;'>{'⚡' if dev['fastboot'] else '⚫'}</span><br><small>{'Fastboot: ' + str(len(dev['fastboot'])) if dev['fastboot'] else 'Fastboot: -'}</small></div>", unsafe_allow_html=True)
        status_cols[2].markdown(f"<div class='card' style='text-align:center;padding:0.4rem'><span style='font-size:1.2rem;'>{'🛑' if dev['edl'] else '⚫'}</span><br><small>{'EDL: ' + str(len(dev['edl'])) if dev['edl'] else 'EDL: -'}</small></div>", unsafe_allow_html=True)
        status_cols[3].markdown(f"<div class='card' style='text-align:center;padding:0.4rem'><span style='font-size:1.2rem;'>{'🍎' if dev['ios'] else '⚫'}</span><br><small>{'iOS: ' + str(len(dev['ios'])) if dev['ios'] else 'iOS: -'}</small></div>", unsafe_allow_html=True)
        status_cols[4].markdown(f"<div class='card' style='text-align:center;padding:0.4rem'><span style='font-size:1.2rem;'>{'🔌' if dev['dfu'] else '⚫'}</span><br><small>{'DFU: ' + str(len(dev['dfu'])) if dev['dfu'] else 'DFU: -'}</small></div>", unsafe_allow_html=True)
        if _dash_amp["ampere"] > 0:
            status_cols[5].markdown(f"<div class='card' style='text-align:center;padding:0.4rem;background:#1A1A2E;color:#C9A84C;'><span style='font-size:1.2rem;'>⚡</span><br><small><strong>{_dash_amp['ampere']:.4f}A</strong></small></div>", unsafe_allow_html=True)
        else:
            status_cols[5].markdown(f"<div class='card' style='text-align:center;padding:0.4rem'><span style='font-size:1.2rem;'>⚫</span><br><small>Ampere: -</small></div>", unsafe_allow_html=True)

        if dev["adb"]:
            s = dev["adb"][0]
            model = adb_getprop(s, "ro.product.model")
            bat = adb_getprop(s, "ro.build.version.release")
            st.markdown(f"<div class='banner-success'>✅ **Device Terdeteksi:** {model or s} | Android: {bat or '?'} | Serial: {s}</div>", unsafe_allow_html=True)

    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT COUNT(*), COALESCE(SUM(biaya_jasa+biaya_sparepart),0) FROM log_service WHERE status='completed'")
    svc_count, svc_rev = c.fetchone()
    c.execute("SELECT COUNT(*) FROM pelanggan"); guest_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM inventory_sparepart WHERE stock <= min_stock"); low_stock = c.fetchone()[0]
    c.execute("SELECT SUM(stock*harga_jual) FROM inventory_sparepart"); inv_value = c.fetchone()[0] or 0
    conn.close()
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"<div class='card' style='text-align:center'><strong style='font-size:1.8rem;'>{guest_count}</strong><br>Total Check-In</div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='card' style='text-align:center'><strong style='font-size:1.8rem;'>{svc_count}</strong><br>Service Selesai</div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='card' style='text-align:center'><strong style='font-size:1.8rem;'>Rp {svc_rev:,.0f}</strong><br>Revenue</div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='card card-red' style='text-align:center'><strong style='font-size:1.8rem;'>{low_stock}</strong><br>Stok Menipis</div>" if low_stock else f"<div class='card' style='text-align:center'><strong style='font-size:1.8rem;'>{low_stock}</strong><br>Stok Menipis</div>", unsafe_allow_html=True)

    st.markdown("### Riwayat Aktivitas Terbaru")
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT nama, device_model, platform, severity, diagnosis, created_at FROM pelanggan ORDER BY created_at DESC LIMIT 8")
    recent = c.fetchall(); conn.close()
    if recent:
        for r in recent:
            pi = "Android" if r["platform"]=="android" else "iOS"
            st.markdown(f"<div class='card' style='padding:0.6rem 1rem'><div style='display:flex;justify-content:space-between;'><span><strong>{r['nama']}</strong> — {r['device_model']} ({pi})</span><span>{r['severity'].upper()} | {r['created_at'][:16]}</span></div><div style='color:#6B7280;font-size:0.85rem;'>{r['diagnosis'][:100]}{'...' if len(r['diagnosis'])>100 else ''}</div></div>", unsafe_allow_html=True)
    else: st.info("Belum ada data check-in.")

    st.markdown("### Status Tools Sistem")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='card'><strong>ADB:</strong> {'Terinstall' if check_adb_installed() else 'Tidak'}</div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='card'><strong>Fastboot:</strong> {'Terinstall' if check_fastboot_installed() else 'Tidak'}</div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='card'><strong>libimobiledevice:</strong> {'Terinstall' if check_idevice_installed() else 'Tidak'}</div>", unsafe_allow_html=True)
    missing = []
    if not check_adb_installed(): missing.append("ADB")
    if not check_fastboot_installed(): missing.append("Fastboot")
    if not check_idevice_installed(): missing.append("libimobiledevice")
    if missing:
        st.warning(f"Tools belum terinstall: {', '.join(missing)}")
        st.markdown("""
**Cara install di Windows:**
- **ADB & Fastboot:** `scoop install adb` atau download [Platform Tools](https://developer.android.com/studio/releases/platform-tools)
- **libimobiledevice:** Download dari [github.com/libimobiledevice-win32](https://github.com/libimobiledevice-win32/imobiledevice-net/releases)
        """)

elif menu == "Deep ADB Scanner (Android)":
    st.title("Deep ADB Scanner — Android")
    st.markdown("<p style='color:#6B7280;'>Memindai perangkat Android hingga ke inti: model, chipset, partisi, bootloader, baterai, CPU, MAC address.</p>", unsafe_allow_html=True)
    if not check_adb_installed():
        st.markdown("<div class='banner-critical'>❌ ADB tidak terinstall!</div>", unsafe_allow_html=True)
        st.markdown("Install ADB: `scoop install adb` (Windows) atau download [Platform Tools](https://developer.android.com/studio/releases/platform-tools)")
    else:
        auto_devs = adb_devices()
        if auto_devs:
            st.markdown(f"<div class='banner-success'>✅ {len(auto_devs)} device terdeteksi! Klik Scan untuk detail.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='banner-warning'>⚠️ Belum ada device. Pastikan: 1) USB Debugging ON 2) Kabel data sync 3) Authorized di popup HP</div>", unsafe_allow_html=True)

    if st.button("SCAN ADB DEVICES", type="primary", use_container_width=True):
        if not check_adb_installed():
            st.markdown("<div class='banner-critical'>ADB tidak terinstall. Install: scoop install adb (Windows) / download Platform Tools</div>", unsafe_allow_html=True)
        else:
            with st.spinner("Menjalankan adb devices..."):
                devices = adb_devices()
            if devices:
                st.markdown(f"<div class='banner-success'>{len(devices)} device terdeteksi!</div>", unsafe_allow_html=True)
                for serial in devices:
                    with st.spinner(f"Deep scanning {serial}..."):
                        try:
                            info = deep_scan_android(serial)
                        except Exception as e:
                            st.error(f"Scan gagal: {e}")
                            continue
                    st.markdown(f"""<div class='card card-gold'><h3>Device: {info['model'] or 'Unknown'}</h3>
                        <table style='width:100%;font-size:0.9rem;'>
                        <tr><td style='color:#6B7280;width:180px;'>Serial</td><td><strong>{info['serial']}</strong></td></tr>
                        <tr><td style='color:#6B7280;'>Manufacturer</td><td>{info['manufacturer'] or 'N/A'}</td></tr>
                        <tr><td style='color:#6B7280;'>Serial Number</td><td>{info['serialno'] or 'N/A'}</td></tr>
                        <tr><td style='color:#6B7280;'>Chipset</td><td><strong>{info['chipset'] or 'N/A'}</strong></td></tr>
                        <tr><td style='color:#6B7280;'>Android Version</td><td>{info['android'] or 'N/A'} (SDK {info['sdk'] or 'N/A'})</td></tr>
                        <tr><td style='color:#6B7280;'>Security Patch</td><td>{info['security_patch'] or 'N/A'}</td></tr>
                        <tr><td style='color:#6B7280;'>Bootloader</td><td><strong>{'LOCKED' if info['bootloader']=='locked' else 'UNLOCKED' if info['bootloader']=='unlocked' else info['bootloader'].upper()}</strong></td></tr>
                        <tr><td style='color:#6B7280;'>WiFi MAC</td><td>{info['wlan_mac'] or 'N/A'}</td></tr>
                        <tr><td style='color:#6B7280;'>Bluetooth MAC</td><td>{info['bt_mac'] or 'N/A'}</td></tr>
                        <tr><td style='color:#6B7280;'>USB Config</td><td>{info['usb_config'] or 'N/A'}</td></tr>
                        </table></div>""", unsafe_allow_html=True)
                    conn = get_conn(); c = conn.cursor()
                    c.execute("INSERT INTO adb_scan_log (serial,model,manufacturer,chipset,android_version,sdk,bootloader,security_patch,product_name) VALUES(?,?,?,?,?,?,?,?,?)", (info['serial'],info['model'],info['manufacturer'],info['chipset'],info['android'],info['sdk'],info['bootloader'],info['security_patch'],info['product']))
                    conn.commit(); conn.close()
                    if info["cpu_info"]:
                        with st.expander("CPU Info"): st.code(info["cpu_info"])
                    if info["mem_total"]:
                        with st.expander("Memory Info"): st.code(info["mem_total"])
                    bat = info["battery"]
                    st.markdown(f"""<div class='card card-blue'><h3>Baterai (Riil via dumpsys)</h3><table style='width:100%;font-size:0.9rem;'><tr><td style='color:#6B7280;width:180px;'>Level</td><td>{bat['level']}%</td></tr><tr><td>Voltage</td><td>{bat['voltage']}V</td></tr><tr><td>Temperature</td><td>{bat['temperature']}C</td></tr><tr><td>Current Now</td><td>{bat['current_now']} uA ({bat['current_now']/1000} mA)</td></tr><tr><td>Health</td><td>{bat['health'].upper()}</td></tr><tr><td>Status</td><td>{bat['status'].upper()}</td></tr></table></div>""", unsafe_allow_html=True)
                    sto = info["storage"]
                    if sto["total_gb"] > 0: st.markdown(f"""<div class='card'><h3>Penyimpanan</h3><table style='width:100%;font-size:0.9rem;'><tr><td style='color:#6B7280;width:180px;'>Total</td><td>{sto['total_gb']} GB</td></tr><tr><td>Terpakai</td><td>{sto['used_gb']} GB</td></tr><tr><td>Sisa</td><td><strong>{sto['free_gb']} GB ({sto['free_percent']}%)</strong></td></tr></table></div>""", unsafe_allow_html=True)
                    st.markdown(f"### Link Firmware untuk {info['model']}")
                    for src, url in firmware_urls(info['model'], info['chipset']): st.markdown(f"- [{src}]({url})")
                    if info["partitions"]:
                        with st.expander("Partisi Sistem"): st.code("\n".join(info["partitions"]), language="text")
                    parts_detail = android_partitions_detail(serial)
                    if parts_detail:
                        with st.expander("Partisi by-name"): st.code("\n".join(parts_detail), language="text")
            else: st.markdown("<div class='banner-warning'>ADB berjalan, tidak ada device. Cek USB Debugging.</div>", unsafe_allow_html=True)
    if st.button("SCAN FASTBOOT", use_container_width=True):
        if not check_fastboot_installed(): st.markdown("<div class='banner-critical'>Fastboot tidak terinstall.</div>", unsafe_allow_html=True)
        else:
            with st.spinner("fastboot devices..."):
                fb_devices = fastboot_devices()
            if fb_devices:
                for s in fb_devices:
                    bl = fastboot_getvar(s, "unlocked")
                    st.markdown(f"""<div class='card card-blue'><strong>FASTBOOT DEVICE</strong><br>Serial: {s}<br>Bootloader: {'UNLOCKED' if bl in ['yes','1'] else 'LOCKED' if bl in ['no','0'] else bl if bl else 'unknown'}</div>""", unsafe_allow_html=True)
            else: st.markdown("<div class='banner-warning'>Tidak ada device di fastboot mode.</div>", unsafe_allow_html=True)

elif menu == "iOS Scanner (iPhone)":
    st.title("iOS Scanner — iPhone/iPad")
    st.markdown("<p style='color:#6B7280;'>Memindai perangkat iOS via libimobiledevice. Data riil: model, iOS version, serial, activation lock, UDID.</p>", unsafe_allow_html=True)
    if not check_idevice_installed():
        st.markdown("<div class='banner-critical'>libimobiledevice tidak terinstall.</div>", unsafe_allow_html=True)
        st.markdown("Download dari [github.com/libimobiledevice-win32](https://github.com/libimobiledevice-win32/imobiledevice-net/releases)")
    else:
        if st.button("SCAN iOS DEVICES", type="primary", use_container_width=True):
            with st.spinner("Mendeteksi perangkat iOS..."):
                udids = idevice_devices()
            if udids:
                st.markdown(f"<div class='banner-success'>{len(udids)} perangkat iOS terdeteksi!</div>", unsafe_allow_html=True)
                for udid in udids:
                    with st.spinner(f"Mengambil data..."):
                        info = idevice_get_info(udid)
                    st.markdown(f"""<div class='card card-gold'><h3>{info['device_name'] or 'iPhone'}</h3>
                        <table style='width:100%;font-size:0.9rem;'><tr><td style='color:#6B7280;width:180px;'>UDID</td><td><strong>{info['udid']}</strong></td></tr>
                        <tr><td>Model</td><td>{info['product_type'] or 'N/A'}</td></tr>
                        <tr><td>iOS Version</td><td>{info['ios_version'] or 'N/A'}</td></tr>
                        <tr><td>Serial Number</td><td>{info['serial_number'] or 'N/A'}</td></tr>
                        <tr><td>Device Name</td><td>{info['device_name'] or 'N/A'}</td></tr>
                        <tr><td>Activation Status</td><td><strong>{info['activation_status'] or 'N/A'}</strong></td></tr>
                        <tr><td>WiFi MAC</td><td>{info['wifi_mac'] or 'N/A'}</td></tr>
                        <tr><td>Bluetooth MAC</td><td>{info['bt_mac'] or 'N/A'}</td></tr></table></div>""", unsafe_allow_html=True)
                    bat = idevice_battery_info(udid)
                    if bat["health_pct"] > 0 or bat["design_capacity"] > 0:
                        st.markdown(f"""<div class='card card-blue'><h3>Baterai iPhone</h3><table style='width:100%;font-size:0.9rem;'><tr><td style='color:#6B7280;width:180px;'>Kapasitas Aktual</td><td>{bat['current_capacity']} mAh</td></tr><tr><td>Kapasitas Pabrik</td><td>{bat['design_capacity']} mAh</td></tr><tr><td>Health</td><td><strong>{bat['health_pct']}%</strong></td></tr><tr><td>Cycle Count</td><td>{bat['cycle_count']}</td></tr><tr><td>Voltage</td><td>{bat['voltage']}V</td></tr><tr><td>Temperature</td><td>{bat['temperature']}C</td></tr></table></div>""", unsafe_allow_html=True)
                        if bat["health_pct"] > 0: st.info(generate_battery_status_text(bat["health_pct"], bat["cycle_count"], "ios"))
                    lock = idevice_activation_lock(udid)
                    if lock["find_my_iphone"] or lock["activation_lock"]:
                        st.markdown("<div class='banner-critical'>FIND MY iPHONE AKTIF — Activation Lock TERKUNCI!</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='banner-success'>Find My iPhone TIDAK aktif — aman.</div>", unsafe_allow_html=True)
                    conn = get_conn(); c = conn.cursor()
                    c.execute("INSERT INTO ios_scan_log (udid,model,ios_version,serial_number,activation_status,battery_health,cycle_count) VALUES(?,?,?,?,?,?,?)", (info['udid'], info['product_type'], info['ios_version'], info['serial_number'], info['activation_status'], bat['health_pct'], bat['cycle_count']))
                    conn.commit(); conn.close()
                    st.markdown("### Link Firmware")
                    for src, url in firmware_urls(info['product_type'], "", "ios"): st.markdown(f"- [{src}]({url})")
            else: st.markdown("<div class='banner-warning'>Tidak ada perangkat iOS. Jalankan idevicepair pair dulu.</div>", unsafe_allow_html=True)

elif menu == "Network Scan (PC/Laptop)":
    st.title("Network Scan — Windows/Linux PC")
    st.markdown("<p style='color:#6B7280;'>Memindai jaringan lokal untuk mendeteksi PC/laptop. Berguna untuk sinkronisasi data kasir dengan komputer toko.</p>", unsafe_allow_html=True)
    subnet = st.text_input("Subnet (opsional)", placeholder="192.168.1.0")
    if st.button("SCAN JARINGAN", type="primary", use_container_width=True):
        with st.spinner("Memindai jaringan... (254 host)"):
            results = network_scan(subnet)
        if results:
            st.markdown(f"<div class='banner-success'>{len(results)} perangkat ditemukan!</div>", unsafe_allow_html=True)
            for r in results:
                st.markdown(f"<div class='card' style='padding:0.6rem 1rem;'><div style='display:flex;justify-content:space-between;'><span><strong>{r['ip']}</strong></span></div><div style='color:#6B7280;font-size:0.85rem;'>Hostname: {r['hostname'] or 'N/A'} | OS: {r['os_type'][:80]}</div></div>", unsafe_allow_html=True)
        else: st.markdown("<div class='banner-warning'>Tidak ada perangkat ditemukan.</div>", unsafe_allow_html=True)

elif menu == "Check-In & Diagnosis":
    st.title("Smart Check-In & Diagnosis")
    # Auto-detect device
    _detected_model = ""
    _detected_platform = "android"
    _adb_devs = adb_devices()
    if _adb_devs:
        _detected_model = adb_getprop(_adb_devs[0], "ro.product.model")
        st.markdown(f"<div class='banner-success'>✅ Device terdeteksi: {_detected_model or _adb_devs[0]}</div>", unsafe_allow_html=True)
    elif check_idevice_installed() and idevice_devices():
        _detected_platform = "ios"
        st.markdown(f"<div class='banner-success'>✅ iOS device terdeteksi</div>", unsafe_allow_html=True)

    # Auto-detect ampere
    _auto_amp = auto_detect_ampere()
    _default_amp = _auto_amp["ampere"]
    if _auto_amp["ampere"] > 0:
        st.markdown(f"<div class='banner-info'>⚡ Ampere terdeteksi otomatis: **{_auto_amp['ampere']:.4f}A** ({_auto_amp['source']})</div>", unsafe_allow_html=True)
    elif _auto_amp["detail"] != "Tidak terdeteksi otomatis — isi manual":
        st.markdown(f"<div class='card' style='padding:0.4rem 0.8rem;font-size:0.85rem;'>{_auto_amp['detail']}</div>", unsafe_allow_html=True)

    with st.form("checkin"):
        col1, col2 = st.columns(2)
        with col1:
            nama = st.text_input("Nama Pelanggan *")
            device_model = st.text_input("Model HP *", value=_detected_model or "", placeholder="Redmi Note 13 / iPhone 11")
            keluhan = st.text_area("Gejala Kerusakan *", placeholder="HP mati total setelah jatuh...")
            platform = st.selectbox("Platform", ["android", "ios"], index=0 if _detected_platform=="android" else 1)
        with col2:
            no_hp = st.text_input("No. HP", placeholder="081234567890")
            imei = st.text_input("IMEI / Serial")
            ampere = st.number_input("Arus Ampere (Power Supply)", 0.0, 10.0, _default_amp, 0.01, format="%.4f", help=f"Auto-detect: {_auto_amp['detail']}. Ketik manual jika perlu koreksi.")
            kondisi = st.selectbox("Kondisi HP", ["mati_total — Mati total, belum tekan power", "tekan_power — Sudah tekan tombol power"])
        submitted = st.form_submit_button("DIAGNOSIS SEKARANG", type="primary", use_container_width=True)
    if submitted:
        if not nama or not device_model or not keluhan: st.markdown("<div class='banner-critical'>Nama, Model HP, dan Gejala wajib!</div>", unsafe_allow_html=True)
        else:
            kond = kondisi.split(" — ")[0]; chipset = ""; serial_device = ""
            if platform == "android":
                devs = adb_devices()
                if devs: chipset = adb_getprop(devs[0], "ro.board.platform"); serial_device = devs[0]
            elif platform == "ios" and check_idevice_installed():
                udids = idevice_devices()
                if udids: chipset = "apple"; serial_device = idevice_get_info(udids[0]).get("serial_number","")
            diagnosis, severity, rekomendasi = diagnose_ampere(ampere, kond, platform)
            symp = analyze_symptoms(keluhan)
            if symp: diagnosis += f"\n\nAnalisis Gejala: {symp}"
            conn = get_conn(); c = conn.cursor()
            c.execute("INSERT INTO pelanggan (nama,no_hp,device_model,chipset,platform,imei,serial_device,keluhan,ampere_reading,kondisi,severity,diagnosis,rekomendasi) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (nama,no_hp,device_model,chipset,platform,imei,serial_device,keluhan,ampere,kond,severity,diagnosis,rekomendasi))
            pid = c.lastrowid; conn.commit(); conn.close()
            bc = {"low":"banner-success","medium":"banner-warning","high":"banner-warning","critical":"banner-critical"}.get(severity,"banner-info")
            st.markdown(f"<div class='{bc}'>SEVERITY: {severity.upper()} | ID Tiket: #{pid} | Platform: {platform.upper()}</div>", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1: st.markdown(f"<div class='card'><h3>Data Input</h3><table style='width:100%;font-size:0.9rem;'><tr><td style='color:#6B7280;'>Pelanggan</td><td><strong>{nama}</strong></td></tr><tr><td>Model</td><td><strong>{device_model}</strong></td></tr><tr><td>Platform</td><td>{platform.upper()}</td></tr><tr><td>Arus</td><td>{ampere:.3f}A</td></tr></table></div>", unsafe_allow_html=True)
            with col2: st.markdown(f"<div class='card card-gold'><h3>Diagnosis AI</h3><p style='white-space:pre-wrap;'>{diagnosis}</p></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='card'><h3>Rekomendasi</h3><p style='white-space:pre-wrap;'>{rekomendasi}</p></div>", unsafe_allow_html=True)
            st.markdown("### Link Firmware")
            for src, url in firmware_urls(device_model, chipset, platform): st.markdown(f"- [{src}]({url})")

elif menu == "Ampere & Baterai":
    st.title("Diagnosis Ampere & Battery Health Multi-OS")
    tab1, tab2, tab3, tab4 = st.tabs(["Diagnosis Ampere (Android)", "Battery Health Android", "Diagnosis Ampere (iOS)", "Battery Health iOS"])

    with tab1:
        st.markdown("Masukkan nilai arus untuk diagnosis Android.")
        _amp_auto = auto_detect_ampere()
        _amp_default = _amp_auto["ampere"] if _amp_auto["ampere"] > 0 else 0.02
        if _amp_auto["ampere"] > 0:
            st.markdown(f"<div class='banner-info' style='font-size:0.85rem;padding:0.4rem 1rem;'>⚡ Auto: {_amp_auto['ampere']:.4f}A ({_amp_auto['source']})</div>", unsafe_allow_html=True)
        with st.form("amp_form"):
            amp = st.number_input("Arus (A)", 0.0, 10.0, _amp_default, 0.001, format="%.4f", help=f"Auto-detect: {_amp_auto['detail']}")
            kond = st.selectbox("Kondisi", ["mati_total", "tekan_power"])
            if st.form_submit_button("Analisis", type="primary"):
                d, s, r = diagnose_ampere(amp, kond, "android")
                st.markdown(f"<div class='card card-red' style='text-align:center'><strong>SEVERITY: {s.upper()}</strong></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='card card-gold'><p style='white-space:pre-wrap;'>{d}</p></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='card'><p style='white-space:pre-wrap;'>{r}</p></div>", unsafe_allow_html=True)

    with tab2:
        st.markdown("### Ambil Data Baterai Riil dari HP Android via ADB")
        devs = adb_devices()
        if not devs: st.markdown("<div class='banner-warning'>Tidak ada device via ADB.</div>", unsafe_allow_html=True)
        elif st.button("SCAN BATERAI VIA ADB", type="primary"):
            for serial in devs:
                with st.spinner(f"Mengambil data dari {serial}..."):
                    bat_raw = android_battery_raw(serial)
                    bat_cap = android_battery_capacity(serial)
                col1, col2, col3 = st.columns(3)
                col1.metric("Level", f"{bat_raw['level']}%")
                col2.metric("Voltage", f"{bat_raw['voltage']}V")
                col3.metric("Temperature", f"{bat_raw['temperature']}C")
                col1, col2, col3 = st.columns(3)
                col1.metric("Current", f"{bat_raw['current_now']} uA")
                col2.metric("Health", bat_raw['health'].upper())
                col3.metric("Status", bat_raw['status'].upper())
                if bat_cap["design_mah"] > 0:
                    st.markdown(f"<table style='font-size:0.9rem;'><tr><td style='color:#6B7280;width:180px;'>Kapasitas Aktual</td><td><strong>{bat_cap['current_mah']} mAh</strong></td></tr><tr><td>Kapasitas Pabrik</td><td>{bat_cap['design_mah']} mAh</td></tr><tr><td>Kesehatan</td><td><strong>{bat_cap['health_pct']}%</strong></td></tr><tr><td>Cycle Count</td><td>{bat_cap['cycle_count']}</td></tr></table>", unsafe_allow_html=True)
                    if bat_cap["health_pct"] < 50: st.markdown("<div class='banner-critical'>BATERAI KRITIS — Segera ganti!</div>", unsafe_allow_html=True)
                    elif bat_cap["health_pct"] < 70: st.markdown("<div class='banner-warning'>Baterai mulai menurun.</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='banner-success'>Baterai masih sehat.</div>", unsafe_allow_html=True)
                    st.info(generate_battery_status_text(bat_cap["health_pct"], bat_cap["cycle_count"]))
                    conn = get_conn(); c = conn.cursor()
                    c.execute("INSERT INTO battery_log (platform,level,current_mah,design_mah,health_pct,voltage,temperature,cycle_count,current_ua) VALUES('android',?,?,?,?,?,?,?,?)", (bat_raw['level'],bat_cap['current_mah'],bat_cap['design_mah'],bat_cap['health_pct'],bat_raw['voltage'],bat_raw['temperature'],bat_cap['cycle_count'],bat_raw['current_now']))
                    conn.commit(); conn.close(); st.success("Data baterai tersimpan.")

    with tab3:
        st.markdown("### Diagnosis Ampere untuk iPhone/iPad")
        _amp_ios = auto_detect_ampere()
        _amp_ios_def = _amp_ios["ampere"] if _amp_ios["ampere"] > 0 else 0.02
        if _amp_ios["ampere"] > 0:
            st.markdown(f"<div class='banner-info' style='font-size:0.85rem;padding:0.4rem 1rem;'>⚡ Auto: {_amp_ios['ampere']:.4f}A ({_amp_ios['source']})</div>", unsafe_allow_html=True)
        with st.form("ios_amp_form"):
            amp_ios = st.number_input("Arus iPhone (A)", 0.0, 10.0, _amp_ios_def, 0.001, format="%.4f", key="ios_amp", help=f"Auto: {_amp_ios['detail']}")
            kond_ios = st.selectbox("Kondisi iPhone", ["mati_total", "tekan_power"], key="ios_kond")
            if st.form_submit_button("Analisis iPhone", type="primary"):
                d, s, r = diagnose_ampere(amp_ios, kond_ios, "ios")
                st.markdown(f"<div style='text-align:center'><strong>SEVERITY: {s.upper()}</strong></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='card card-gold'><p style='white-space:pre-wrap;'>{d}</p></div>", unsafe_allow_html=True)
                st.markdown(f"<div class='card'><p style='white-space:pre-wrap;'>{r}</p></div>", unsafe_allow_html=True)

    with tab4:
        st.markdown("### Ambil Data Baterai iPhone via libimobiledevice")
        if not check_idevice_installed(): st.markdown("<div class='banner-critical'>libimobiledevice tidak terinstall.</div>", unsafe_allow_html=True)
        elif st.button("SCAN BATERAI iPHONE", type="primary"):
            udids = idevice_devices()
            if udids:
                for udid in udids:
                    with st.spinner(f"Mengambil data..."):
                        bat = idevice_battery_info(udid)
                    st.markdown(f"<div class='card card-blue'><h3>Baterai iPhone</h3><table style='width:100%;font-size:0.9rem;'><tr><td style='color:#6B7280;width:200px;'>Kapasitas Aktual</td><td>{bat['current_capacity']} mAh</td></tr><tr><td>Kapasitas Pabrik</td><td>{bat['design_capacity']} mAh</td></tr><tr><td>Health</td><td><strong>{bat['health_pct']}%</strong></td></tr><tr><td>Cycle Count</td><td>{bat['cycle_count']}</td></tr><tr><td>Voltage</td><td>{bat['voltage']}V</td></tr><tr><td>Temperature</td><td>{bat['temperature']}C</td></tr></table></div>", unsafe_allow_html=True)
                    if bat["health_pct"] > 0:
                        if bat["health_pct"] < 80: st.markdown("<div class='banner-warning'>Health < 80% — iPhone throttle. Rekomendasi ganti.</div>", unsafe_allow_html=True)
                        else: st.markdown("<div class='banner-success'>Baterai masih baik.</div>", unsafe_allow_html=True)
                        st.info(generate_battery_status_text(bat["health_pct"], bat["cycle_count"], "ios"))
                        conn = get_conn(); c = conn.cursor()
                        c.execute("INSERT INTO battery_log (platform,level,current_mah,design_mah,health_pct,voltage,temperature,cycle_count) VALUES('ios',0,?,?,?,?,?,?)", (bat['current_capacity'],bat['design_capacity'],bat['health_pct'],bat['voltage'],bat['temperature'],bat['cycle_count']))
                        conn.commit(); conn.close(); st.success("Data tersimpan.")
                        if HAS_PLOTLY:
                            fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=bat["health_pct"], number={'suffix':"%"}, delta={'reference':80}, gauge={'axis':{'range':[0,100]},'bar':{'color':"#059669" if bat['health_pct']>80 else "#D97706"},'steps':[{'range':[0,50],'color':"#FEE2E2"},{'range':[50,80],'color':"#FEF3C7"},{'range':[80,100],'color':"#D1FAE5"}]}))
                            fig.update_layout(height=280, paper_bgcolor="rgba(0,0,0,0)")
                            st.plotly_chart(fig, use_container_width=True)
            else: st.markdown("<div class='banner-warning'>Tidak ada perangkat iOS.</div>", unsafe_allow_html=True)

elif menu == "Pre-Flashing Security":
    st.title("Pre-Flashing Security & Safe-Guard Multi-OS")
    tab1, tab2 = st.tabs(["Android (FRP/ARB)", "iPhone (Activation Lock)"])

    with tab1:
        st.markdown("<div class='banner-critical'>PERINGATAN — Flashing tanpa persiapan dapat menyebabkan HARDBRICK! Centang semua item.</div>", unsafe_allow_html=True)
        with st.form("security_form"):
            model_check = st.text_input("Model HP yang akan di-flash")
            frp = st.checkbox("Google Account (FRP) sudah di-logout?", value=False)
            mi_cloud = st.checkbox("Mi Cloud / Find My Device dimatikan?", value=False)
            samsung = st.checkbox("Samsung Account di-logout?", value=False)
            backup = st.checkbox("Data pelanggan sudah di-backup?", value=False)
            battery_ok = st.checkbox("Baterai > 50%?", value=False)
            usb_ok = st.checkbox("Kabel USB baik?", value=False)
            teknisi_note = st.text_area("Catatan Teknisi")
            if st.form_submit_button("VALIDASI & SIMPAN LOG", type="primary"):
                frp_ok = 1 if (frp or not any(x in model_check.lower() for x in ["xiaomi","redmi","samsung","oppo","vivo","realme","poco"])) else 0
                all_checked = all([frp, backup, battery_ok, usb_ok])
                arb = get_arb_level(model_check) if model_check else {"level":0,"min_ver":"N/A","note":""}
                conn = get_conn(); c = conn.cursor()
                c.execute("INSERT INTO security_log (device_model,platform,frp_checked,backup_checked,arb_level,arb_warning,is_safe,teknisi_note) VALUES(?,?,?,?,?,?,?,?)", (model_check,'android',frp_ok,1 if backup else 0,arb["level"],arb["note"],1 if all_checked else 0,teknisi_note))
                conn.commit(); conn.close()
                if all_checked: st.markdown("<div class='banner-success'>SEMUA AMAN — Log tersimpan. Siap flashing!</div>", unsafe_allow_html=True); st.balloons()
                else: st.markdown("<div class='banner-warning'>Belum semua item tercentang.</div>", unsafe_allow_html=True)
                st.info(f"FRP={'OK' if frp_ok else 'X'}, Backup={'OK' if backup else 'X'}, ARB Level={arb['level']}")

        with st.expander("ARB Check"):
            if model_check:
                arb = get_arb_level(model_check)
                if arb["level"] >= 7: st.markdown(f"<div class='banner-critical'>ARB LEVEL {arb['level']} — DOWNGRADE AKAN HARDBRICK!</div>", unsafe_allow_html=True)
                elif arb["level"] >= 4: st.markdown(f"<div class='banner-warning'>ARB LEVEL {arb['level']} — Hati-hati downgrade!</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='banner-success'>ARB LEVEL {arb['level']} — Aman.</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='card'><strong>Info:</strong> {arb['note']}<br><strong>Min versi aman:</strong> {arb['min_ver']}</div>", unsafe_allow_html=True)
                devs = adb_devices()
                if devs and st.button("Cek FRP via ADB"):
                    with st.spinner("Membaca..."):
                        frp_status = check_frp_android(devs[0])
                    if frp_status["frp_locked"]: st.markdown("<div class='banner-critical'>FRP TERKUNCI!</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='banner-success'>Tidak terdeteksi akun terkunci.</div>", unsafe_allow_html=True)
                    if frp_status["details"]: st.code(frp_status["details"])

    with tab2:
        st.markdown("### iPhone Activation Lock Check")
        if not check_idevice_installed(): st.markdown("<div class='banner-critical'>libimobiledevice tidak terinstall.</div>", unsafe_allow_html=True); st.markdown("Download: [github.com/libimobiledevice-win32](https://github.com/libimobiledevice-win32/imobiledevice-net/releases)")
        elif st.button("CEK ACTIVATION LOCK", type="primary"):
            udids = idevice_devices()
            if udids:
                for udid in udids:
                    with st.spinner("Memeriksa..."):
                        info = idevice_get_info(udid)
                        lock = idevice_activation_lock(udid)
                    st.markdown(f"<div class='card card-gold'><h3>{info['device_name']}</h3><table><tr><td>Model</td><td>{info['product_type']}</td></tr><tr><td>iOS</td><td>{info['ios_version']}</td></tr><tr><td>Serial</td><td>{info['serial_number']}</td></tr><tr><td>Activation</td><td>{info['activation_status']}</td></tr></table></div>", unsafe_allow_html=True)
                    if lock["find_my_iphone"] or lock["activation_lock"]:
                        st.markdown("<div class='banner-critical'>FIND MY iPHONE AKTIF! Perangkat TIDAK aman diservice tanpa bukti kepemilikan!</div>", unsafe_allow_html=True)
                    else: st.markdown("<div class='banner-success'>Find My iPhone TIDAK aktif — aman diservice.</div>", unsafe_allow_html=True)
            else: st.markdown("<div class='banner-warning'>Tidak ada perangkat iOS.</div>", unsafe_allow_html=True)

elif menu == "Recovery & Testpoint Guide":
    st.title("Recovery, DFU Mode & Testpoint Guide")
    st.markdown("<div class='card card-blue'>Panduan interaktif testpoint EDL 9008 Android, DFU/Recovery iPhone berdasarkan tipe perangkat terdeteksi.</div>", unsafe_allow_html=True)

    detected_chipset = ""; detected_model = ""; detected_platform = "android"
    devs = adb_devices()
    if devs:
        detected_chipset = adb_getprop(devs[0], "ro.board.platform")
        detected_model = adb_getprop(devs[0], "ro.product.model")
        if detected_chipset: st.markdown(f"<div class='banner-success'>Android: <strong>{detected_model}</strong> — Chipset: {detected_chipset}</div>", unsafe_allow_html=True)
    if not detected_chipset and check_idevice_installed():
        udids = idevice_devices()
        if udids:
            iinfo = idevice_get_info(udids[0])
            detected_model = iinfo.get("product_type","")
            detected_chipset = "apple"
            detected_platform = "ios"
            st.markdown(f"<div class='banner-success'>iOS: <strong>{iinfo.get('device_name','')}</strong></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if detected_chipset:
            guide = get_testpoint_guide(detected_chipset, detected_platform)
            if guide: st.markdown(f"<div class='card card-gold'><h3>{guide['mode_type'].upper()}</h3><p style='white-space:pre-wrap;'>{guide['description']}</p><p><strong>Kesulitan:</strong> {guide['difficulty'].upper()}</p></div>", unsafe_allow_html=True)
            else: st.markdown("<div class='card card-red'><h3>Panduan untuk perangkat ini belum ada</h3></div>", unsafe_allow_html=True)
        else: st.markdown("<div class='card'>Tidak ada perangkat terdeteksi.</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("### Pencarian Manual")
        mc = st.selectbox("Chipset/Brand", ["qualcomm","mediatek","exynos","huawei_kirin","apple","apple_faceid"])
        mm = st.selectbox("Mode", ["edl_9008","dfu_mode","recovery_mode"])
        pm = "ios" if mc in ["apple","apple_faceid"] else "android"
        g2 = get_testpoint_guide(mc, pm, mm)
        if g2: st.markdown(f"<div class='card card-gold'><h3>{g2['mode_type'].upper()} — {mc.upper()}</h3><p style='white-space:pre-wrap;'>{g2['description']}</p><p><strong>Kesulitan:</strong> {g2['difficulty'].upper()}</p></div>", unsafe_allow_html=True)
        else: st.info("Panduan belum tersedia.")

    st.markdown("### Semua Panduan Tersedia")
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM testpoint_guides ORDER BY platform, chipset_brand")
    for g in c.fetchall():
        pi = "iOS" if g["platform"]=="ios" else "Android"
        with st.expander(f"{pi} {g['chipset_brand'].upper()} — {g['mode_type']} ({g['difficulty']})"):
            st.markdown(f"<p style='white-space:pre-wrap;'>{g['description']}</p>", unsafe_allow_html=True)
            if g["koordinat"]: st.markdown(f"**Koordinat:** `{g['koordinat']}`")
    conn.close()

elif menu == "Deep Cache Cleaner":
    st.title("Deep Cache & Trash Cleaner (Multi-OS)")
    st.markdown("<div class='banner-critical'>Membersihkan sampah sistem hingga ke akar. Android via ADB, iPhone via libimobiledevice.</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Android Cleaner", "iPhone Cleaner"])

    with tab1:
        devs = adb_devices()
        if not devs:
            st.markdown("<div class='banner-warning'>Tidak ada device via ADB.</div>", unsafe_allow_html=True)
            if not check_adb_installed(): st.markdown("Install: `scoop install adb` (Windows) / [Platform Tools](https://developer.android.com/studio/releases/platform-tools)")
        else:
            serial = devs[0]
            st.markdown(f"<div class='banner-success'>Device: {serial}</div>", unsafe_allow_html=True)
            sto = android_storage_info(serial)
            if sto["total_gb"] > 0: st.markdown(f"<div class='card'><h3>Penyimpanan Sebelum</h3>Total: {sto['total_gb']} GB | Terpakai: {sto['used_gb']} GB | Sisa: <strong>{sto['free_gb']} GB ({sto['free_percent']}%)</strong></div>", unsafe_allow_html=True)

            clean_confirm = st.text_input("Ketik 'CLEAN' lalu tekan CLEAN ALL untuk konfirmasi:", placeholder="CLEAN", key="clean_confirm")
            if st.button("CLEAN ALL (Deep)", type="primary", use_container_width=True, disabled=(clean_confirm != "CLEAN")):
                with st.spinner("Membersihkan..."):
                    res = android_clean_cache(serial)
                st.markdown(f"<div class='card card-green'><h3>Pembersihan Selesai!</h3><strong>Ruang diselamatkan: {res['total_saved_mb']} MB</strong><br>Tindakan: {len(res['actions'])} berhasil | {len(res['errors'])} error</div>", unsafe_allow_html=True)
                for a in res["actions"]: st.markdown(f"`{a['cmd']}`")
                sto2 = res["after"]
                if sto2["total_gb"] > 0: st.markdown(f"<div class='card'><h3>Penyimpanan Sesudah</h3>Sisa: <strong>{sto2['free_gb']} GB ({sto2['free_percent']}%)</strong></div>", unsafe_allow_html=True)
                conn = get_conn(); c = conn.cursor()
                c.execute("INSERT INTO cleaning_log (device_serial,platform,action_type,space_saved_mb,result) VALUES(?,?,'deep_clean',?,?)", (serial,'android',res['total_saved_mb'],f"OK: {len(res['actions'])} actions"))
                conn.commit(); conn.close()

            if st.button("CLEAN CACHE ONLY (Cepat)", use_container_width=True):
                with st.spinner("Trim caches..."):
                    ok, out, err = adb_shell(serial, "pm trim-caches 999G")
                    st.markdown(f"<div class='card'><h3>Trim Caches</h3><code>pm trim-caches 999G</code><br>{out[:200]}</div>", unsafe_allow_html=True)
                conn = get_conn(); c = conn.cursor()
                c.execute("INSERT INTO cleaning_log (device_serial,platform,action_type,result) VALUES(?,?,'trim_caches',?)", (serial,'android',out[:300] if ok else err[:300]))
                conn.commit(); conn.close()

    with tab2:
        st.markdown("### iPhone Cache Cleaner")
        st.markdown("iOS memiliki akses terbatas via libimobiledevice.")
        if check_idevice_installed():
            udids = idevice_devices()
            if udids and st.button("TEST iOS CONNECTION", type="primary"):
                res = ios_clean_cache(udids[0] if udids else "")
                if res["actions"]: st.markdown(f"<div class='banner-success'>Koneksi OK</div>", unsafe_allow_html=True)
                st.info(res["note"])
        else: st.markdown("<div class='card'>Install libimobiledevice untuk akses iOS.</div>", unsafe_allow_html=True)

    with st.expander("Riwayat Pembersihan"):
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM cleaning_log ORDER BY created_at DESC LIMIT 10")
        for lg in c.fetchall(): st.markdown(f"<div class='card' style='padding:0.5rem;font-size:0.85rem;'>{lg['device_serial']} | {lg['action_type']} | {lg['space_saved_mb']} MB | {lg['created_at'][:16]}</div>", unsafe_allow_html=True)
        conn.close()

elif menu == "Inventory & Financial":
    st.title("Inventory & Executive Financial Report")
    tab1, tab2, tab3, tab4 = st.tabs(["Stok Sparepart", "Tambah Sparepart", "Kasir Service", "Financial Narrative"])

    with tab1:
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT * FROM inventory_sparepart ORDER BY kategori, nama")
        items = c.fetchall(); conn.close()
        if items:
            cf = st.selectbox("Filter Kategori", ["Semua"] + sorted(set(i["kategori"] for i in items)))
            for i in items:
                if cf != "Semua" and i["kategori"] != cf: continue
                low = i["stock"] <= i["min_stock"]
                margin = ((i["harga_jual"]-i["harga_beli"])/i["harga_beli"])*100 if i["harga_beli"] else 0
                st.markdown(f"<div class='card {'card-red' if low else ''}' style='padding:0.6rem 1rem;'><div style='display:flex;justify-content:space-between;'><div><strong>{i['nama'][:30]}</strong><br><span style='color:#6B7280;font-size:0.8rem;'>{i['kategori'].upper()} | {i['sku']}</span></div><div style='text-align:right;'><strong>{'⚠️' if low else ''} {i['stock']} pcs</strong><br><span style='font-size:0.8rem;'>Margin: {margin:.0f}% | Terjual: {i['terjual_bulan_ini']}x</span></div></div></div>", unsafe_allow_html=True)
                with st.expander("Restock"):
                    qty = st.number_input("Tambah stok", 1, 100, 5, key=f"q_{i['id']}")
                    if st.button(f"Tambah +{qty}", key=f"r_{i['id']}"):
                        conn = get_conn(); c = conn.cursor()
                        c.execute("UPDATE inventory_sparepart SET stock=stock+?, updated_at=datetime('now','localtime') WHERE id=?", (qty, i['id']))
                        conn.commit(); conn.close(); st.rerun()
        else: st.info("Belum ada sparepart.")

    with tab2:
        with st.form("add_sp"):
            col1, col2 = st.columns(2)
            with col1:
                nama_sp = st.text_input("Nama Sparepart *")
                kategori_sp = st.selectbox("Kategori", ["lcd","battery","ic_power","flex_cable","camera","speaker","mic","button","housing","software","other"])
                sku_sp = st.text_input("SKU *")
            with col2:
                stock_sp = st.number_input("Stok Awal", 0, 9999, 5)
                harga_beli_sp = st.number_input("Harga Beli (Rp)", 0, 99999999, 0, 1000)
                harga_jual_sp = st.number_input("Harga Jual (Rp)", 0, 99999999, 0, 1000)
                kompatibel_sp = st.text_input("Kompatibel dengan")
                min_stock_sp = st.number_input("Min Stok", 1, 999, 5)
            if st.form_submit_button("SIMPAN", type="primary"):
                if not nama_sp or not sku_sp: st.error("Nama dan SKU wajib!")
                else:
                    conn = get_conn(); c = conn.cursor()
                    try:
                        c.execute("INSERT INTO inventory_sparepart (nama,kategori,sku,stock,harga_beli,harga_jual,kompatibel,min_stock) VALUES(?,?,?,?,?,?,?,?)", (nama_sp,kategori_sp,sku_sp,stock_sp,harga_beli_sp,harga_jual_sp,kompatibel_sp,min_stock_sp))
                        conn.commit(); st.success(f"{nama_sp} ditambahkan!")
                    except sqlite3.IntegrityError: st.error(f"SKU '{sku_sp}' sudah ada!")
                    conn.close()

    with tab3:
        st.markdown("### Form Kasir Service")
        conn = get_conn(); c = conn.cursor()
        c.execute("SELECT id, nama, device_model FROM pelanggan ORDER BY created_at DESC LIMIT 20")
        pel_list = c.fetchall()
        c.execute("SELECT id, nama, harga_jual, stock FROM inventory_sparepart WHERE stock > 0")
        sp_list = c.fetchall(); conn.close()
        with st.form("kasir"):
            col1, col2 = st.columns(2)
            with col1:
                pel_id = st.selectbox("Pelanggan", [(p["id"], f"#{p['id']} {p['nama']} ({p['device_model']})") for p in pel_list], format_func=lambda x: x[1])
                tipe = st.selectbox("Tipe Service", ["software","hardware","flashing","ganti_sparepart"])
                biaya_jasa = st.number_input("Biaya Jasa (Rp)", 0, 99999999, 50000, 10000)
            with col2:
                sp_id = st.selectbox("Sparepart", [(0, "- Tidak pakai -")] + [(s["id"], f"{s['nama'][:25]} — Rp {s['harga_jual']:,} (stok: {s['stock']})") for s in sp_list], format_func=lambda x: x[1])
                qty_sp = st.number_input("Jumlah", 0, 100, 1)
                teknisi_note = st.text_area("Catatan")
            if st.form_submit_button("SIMPAN TRANSAKSI", type="primary"):
                biaya_sp = 0; inv_id = None
                if sp_id[0] > 0 and qty_sp > 0:
                    conn = get_conn(); c = conn.cursor()
                    c.execute("SELECT harga_jual, stock FROM inventory_sparepart WHERE id=?", (sp_id[0],))
                    sp = c.fetchone(); conn.close()
                    if sp and sp["stock"] >= qty_sp:
                        biaya_sp = sp["harga_jual"] * qty_sp; inv_id = sp_id[0]
                        conn = get_conn(); c = conn.cursor()
                        c.execute("UPDATE inventory_sparepart SET stock=stock-?, terjual_bulan_ini=terjual_bulan_ini+?, updated_at=datetime('now','localtime') WHERE id=?", (qty_sp, qty_sp, sp_id[0]))
                        conn.commit(); conn.close()
                    else: st.error("Stok tidak mencukupi!")
                total = biaya_jasa + biaya_sp
                conn = get_conn(); c = conn.cursor()
                c.execute("INSERT INTO log_service (pelanggan_id,inventory_id,tipe_service,status,biaya_jasa,biaya_sparepart,total_biaya,teknisi_note,completed_at) VALUES(?,?,?,'completed',?,?,?,?,datetime('now','localtime'))", (pel_id[0], inv_id, tipe, biaya_jasa, biaya_sp, total, teknisi_note))
                conn.commit(); conn.close()
                st.markdown(f"<div class='banner-success'>TRANSAKSI SELESAI! Total: Rp {total:,}</div>", unsafe_allow_html=True)
                st.balloons()

    with tab4:
        st.markdown("### Analisis Keuangan & Narrative Otomatis")
        narrative = financial_narrative()
        st.markdown(f"<div class='card card-gold'><pre style='white-space:pre-wrap;font-family:Inter;font-size:0.9rem;'>{narrative}</pre></div>", unsafe_allow_html=True)
        conn = get_conn(); c = conn.cursor()
        c.execute("""SELECT strftime('%Y-%m-%d', created_at) as day, SUM(total_biaya) as revenue
            FROM log_service WHERE status='completed' AND created_at >= datetime('now','-30 days')
            GROUP BY day ORDER BY day""")
        daily = c.fetchall(); conn.close()
        if daily and HAS_PLOTLY:
            days = [r["day"] for r in daily]; revs = [r["revenue"] for r in daily]
            fig = go.Figure(data=go.Scatter(x=days, y=revs, mode='lines+markers', line=dict(color='#2563EB', width=2)))
            fig.update_layout(title="Revenue 30 Hari", height=300, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

elif menu == "Cari Firmware":
    st.title("Pencarian Link Firmware & Tools")
    col1, col2 = st.columns([1, 1])
    with col1: model_fw = st.text_input("Model HP", placeholder="Redmi Note 13 / iPhone 11")
    with col2: chipset_fw = st.text_input("Chipset (opsional)", placeholder="Snapdragon 685")
    if model_fw:
        st.markdown(f"### Hasil untuk: {model_fw}")
        for src, url in firmware_urls(model_fw, chipset_fw):
            st.markdown(f"<div class='card' style='padding:0.6rem 1rem;'><strong style='color:#2563EB;'>{src}</strong><br><a href='{url}' target='_blank' style='color:#6B7280;word-break:break-all;'>{url}</a></div>", unsafe_allow_html=True)
        arb = get_arb_level(model_fw)
        if arb["level"] >= 7: st.markdown(f"<div class='banner-critical'>ARB LEVEL {arb['level']} — DILARANG DOWNGRADE!</div>", unsafe_allow_html=True)
        elif arb["level"] >= 4: st.markdown(f"<div class='banner-warning'>ARB LEVEL {arb['level']} — Hati-hati downgrade.</div>", unsafe_allow_html=True)
        else: st.markdown(f"<div class='banner-success'>ARB LEVEL {arb['level']} — Aman.</div>", unsafe_allow_html=True)
        st.info(f"{arb['note']}")
    else:
        st.markdown("""<div class='card card-gold'><h3>Sumber Firmware Terpercaya</h3>
        <ul><li><strong>Google Search</strong> — Cari "Stock ROM [model]"</li><li><strong>Firmware27.com</strong> — Firmware Indonesia</li>
        <li><strong>XDA Developers</strong> — Forum global</li><li><strong>SamMobile</strong> — Samsung</li>
        <li><strong>MIUI ROM</strong> — Xiaomi/Redmi</li><li><strong>IPSW.me</strong> — iOS</li>
        <li><strong>SP Flash Tool</strong> — MediaTek</li><li><strong>QPST/QFIL</strong> — Qualcomm</li></ul></div>""", unsafe_allow_html=True)

elif menu == "Dead Phone Scanner":
    st.title("Dead Phone Scanner — Deteksi Tanpa USB Debugging")
    st.markdown("<div class='banner-info'>Memindai device mati/brick melalui Fastboot, EDL 9008, DFU, atau Recovery — tanpa perlu USB Debugging.</div>", unsafe_allow_html=True)
    if st.button("SCAN NOW", type="primary", use_container_width=True):
        with st.spinner("Memindai semua port USB..."):
            scan = dead_phone_scan()
        st.markdown(f"<div class='card card-gold'><strong style='font-size:1.2rem;'>{scan['summary']}</strong></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            if scan["fastboot_devices"]:
                st.markdown("<h3>Fastboot Mode</h3>", unsafe_allow_html=True)
                for s in scan["fastboot_devices"]:
                    var = fastboot_getvar(s, "product") or "unknown"
                    st.markdown(f"<div class='card card-blue' style='padding:0.6rem 1rem;'><code>{s}</code> — {var}</div>", unsafe_allow_html=True)
            if scan["edl_devices"]:
                st.markdown("<h3>EDL / Preloader Mode</h3>", unsafe_allow_html=True)
                for d in scan["edl_devices"]:
                    st.markdown(f"<div class='card card-red' style='padding:0.6rem 1rem;'><strong>{d['vendor']}</strong> — {d['mode']}<br><code>{d['vid']}:{d['pid']}</code></div>", unsafe_allow_html=True)
            if scan["dfu_devices"]:
                st.markdown("<h3>Apple DFU Mode</h3>", unsafe_allow_html=True)
                for d in scan["dfu_devices"]:
                    st.markdown(f"<div class='card' style='padding:0.6rem 1rem;'><strong>Apple iPhone</strong> — DFU Mode terdeteksi!<br><code>{d['vid']}:{d['pid']}</code></div>", unsafe_allow_html=True)
        with col2:
            if scan["adb_devices"]:
                st.markdown("<h3>ADB (Android Normal)</h3>", unsafe_allow_html=True)
                for s in scan["adb_devices"]:
                    ok, out, _ = adb_shell(s, "getprop ro.bootmode")
                    mode = out.strip() if ok else "unknown"
                    st.markdown(f"<div class='card card-green' style='padding:0.6rem 1rem;'><code>{s}</code> — mode: {mode}</div>", unsafe_allow_html=True)
            if scan["recovery_adb"]:
                st.markdown("<h3>Recovery Mode (via ADB)</h3>", unsafe_allow_html=True)
                for s in scan["recovery_adb"]:
                    st.markdown(f"<div class='card card-blue' style='padding:0.6rem 1rem;'><code>{s}</code> dalam Recovery Mode</div>", unsafe_allow_html=True)
            if not scan["fastboot_devices"] and not scan["edl_devices"] and not scan["dfu_devices"] and not scan["adb_devices"]:
                st.markdown("<div class='card card-red'><strong>Tidak ada device terdeteksi.</strong><br>Pastikan HP terhubung via USB cabel (data sync). Untuk HP matot, coba:<br>1. Tekan & tahan Vol Down + Power (Fastboot)<br>2. Cari testpoint EDL (Qualcomm/MTK)<br>3. Untuk iPhone DFU: Vol Up + Vol Down + Side 10 detik</div>", unsafe_allow_html=True)
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM dead_phone_log ORDER BY detected_at DESC LIMIT 10")
        logs = c.fetchall()
        conn.close()
        if logs:
            with st.expander("Riwayat Deteksi"):
                for lg in logs:
                    st.markdown(f"<div style='font-size:0.8rem;color:#6B7280;'>{lg['detected_at'][:19]} | {lg['detected_mode'].upper()} | {lg['vendor'] or lg['serial'] or '-'} | {lg['vid_pid'] or '-'}</div>", unsafe_allow_html=True)
    else:
        st.info("Tekan 'SCAN NOW' untuk mendeteksi device dalam kondisi mati/brick.")

elif menu == "Auto Backup & Restore":
    st.title("Auto Backup & Restore Partisi")
    st.markdown("<div class='banner-critical'>Backup penuh partisi penting sebelum flashing/oprek. SHA256 diverifikasi untuk deteksi korupsi.</div>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Auto Backup Partisi", "Riwayat Backup"])
    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            platform_bk = st.selectbox("Platform", ["android", "ios"])
            fb_devs_bk = fastboot_devices()
            adb_devs_bk = adb_devices()
            serial_bk = ""
            if fb_devs_bk:
                serial_bk = st.selectbox("Pilih Device (Fastboot)", fb_devs_bk, key="fb_sel")
            elif adb_devs_bk:
                serial_bk = st.selectbox("Pilih Device (ADB)", adb_devs_bk, key="adb_sel")
            else:
                st.warning("Tidak ada device terdeteksi (ADB / Fastboot).")
            partitions_default = "persist,efs,nvram,modem,boot,recovery,misc,fsg"
            partitions_bk = st.text_input("Partisi (pisahkan koma)", partitions_default)
        with col2:
            st.markdown("<div class='card card-blue'><h4>Partisi yang akan di-backup:</h4><div style='font-size:0.85rem;'><strong>persist</strong> — IMEI/WiFi/BT calibration<br><strong>efs</strong> — IMEI & network (Qualcomm)<br><strong>nvram</strong> — NVRAM data<br><strong>modem</strong> — Firmware modem<br><strong>boot</strong> — Kernel<br><strong>recovery</strong> — Recovery image<br><strong>misc</strong> — Bootloader flags<br><strong>fsg</strong> — FSG partition</div></div>", unsafe_allow_html=True)
        if serial_bk and st.button("MULAI BACKUP", type="primary", use_container_width=True):
            pl = platform_bk
            if serial_bk in fb_devs_bk:
                pl = "android"
                custom_parts = [p.strip() for p in partitions_bk.split(",") if p.strip()]
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_dir = str(BASE_DIR / "backups" / f"{serial_bk}_{ts}")
                os.makedirs(out_dir, exist_ok=True)
                bar = st.progress(0)
                results = []
                for i, p in enumerate(custom_parts):
                    st.markdown(f"Backup `{p}`...")
                    r = backup_partition_fastboot(serial_bk, p, out_dir)
                    results.append(r)
                    bar.progress((i + 1) / len(custom_parts))
                    if r["status"] == "ok":
                        st.markdown(f"<span style='color:#059669;'>✓ {p}: {r['size_bytes']} bytes  SHA256: {r['sha256'][:16]}...</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span style='color:#DC2626;'>✗ {p}: {r['error'][:50]}</span>", unsafe_allow_html=True)
                ok_count = len([r for r in results if r["status"] == "ok"])
                st.markdown(f"<div class='card card-green'><h3>Backup Selesai</h3><strong>{ok_count}/{len(results)}</strong> partisi berhasil disimpan di:<br><code>{out_dir}</code></div>", unsafe_allow_html=True)
                sha_summary = "\n".join([f"{r['sha256']}  {r['partition']}.img" for r in results if r['sha256']])
                if sha_summary:
                    with open(os.path.join(out_dir, "backup_summary.sha256"), "w") as sf:
                        sf.write(sha_summary)
                    st.markdown(f"<div class='card'>SHA256 checksum disimpan:<br><code>{out_dir}/backup_summary.sha256</code></div>", unsafe_allow_html=True)
            else:
                res = auto_backup(serial_bk, pl)
                st.markdown(f"<div class='card'><h3>Hasil Backup {pl}</h3>{res['summary']}</div>", unsafe_allow_html=True)
    with tab2:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM backup_log ORDER BY created_at DESC LIMIT 20")
        logs = c.fetchall()
        conn.close()
        if logs:
            for lg in logs:
                chk = "✓" if lg["status"] == "completed" else "✗"
                st.markdown(f"<div class='card' style='padding:0.5rem 1rem;font-size:0.85rem;'>{chk} <strong>{lg['partition_name']}</strong> — {lg['device_serial']} ({lg['mode']}) | {lg['file_size_bytes']:,} bytes | {lg['created_at'][:16]}<br><span style='color:#6B7280;font-size:0.75rem;'>SHA256: {lg['sha256_before'][:24] or '-'}...</span></div>", unsafe_allow_html=True)
        else:
            st.info("Belum ada riwayat backup.")

elif menu == "Flash Wizard":
    st.title("Flash Wizard — Safety First, No Mistakes")
    st.markdown("<div class='banner-critical'>⚠️ SISTEM PENGAMANAN KETAT — Setiap langkah diverifikasi. Jika ada risiko hardbrick, sistem akan MEMBLOKIR operasi.</div>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["Safety Checklist", "Deteksi & Firmware", "Verifikasi File", "Flash Eksekusi"])

    if "safety_checks" not in st.session_state:
        st.session_state["safety_checks"] = None
    if "flash_serial" not in st.session_state:
        st.session_state["flash_serial"] = ""
    if "flash_device" not in st.session_state:
        st.session_state["flash_device"] = {}
    if "verified_firmware" not in st.session_state:
        st.session_state["verified_firmware"] = ""
    if "backup_done" not in st.session_state:
        st.session_state["backup_done"] = False
    if "dry_run" not in st.session_state:
        st.session_state["dry_run"] = False

    with tab1:
        st.markdown("### ⛑️ Safety Checklist — WAJIB LULIS SEMUA sebelum flash")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("<div class='card card-red'><strong>PERINGATAN:</strong> Melewati safety check = resiko hardbrick. Sistem akan memblokir flash jika tidak lulus.</div>", unsafe_allow_html=True)
        with col2:
            use_dry_run = st.checkbox("DRY RUN MODE (simulasi — tidak ada flash beneran)", value=True, help="Aman untuk testing. Matikan centang ini saat benar-benar mau flash.")

        serial_sc = adb_devices() + fastboot_devices()
        if not serial_sc:
            st.warning("Tidak ada device terdeteksi. Scan di tab Deteksi & Firmware dulu.")
        else:
            mode_sc = "fastboot" if any(s in fastboot_devices() for s in serial_sc) else "adb"
            serial_sc = serial_sc[0]
            st.markdown(f"Device: <code>{serial_sc}</code> ({mode_sc.upper()})", unsafe_allow_html=True)
            if st.button("JALANKAN SAFETY CHECK", type="primary", use_container_width=True):
                with st.spinner("Memeriksa semua aspek keamanan..."):
                    check = pre_flash_safety_check(serial_sc, mode_sc)
                    st.session_state["safety_checks"] = check
                    st.session_state["flash_serial"] = serial_sc
                    st.session_state["dry_run"] = use_dry_run
            if st.session_state.get("safety_checks"):
                check = st.session_state["safety_checks"]
                for c in check["checks"]:
                    icon = "✅" if c["pass"] else "❌"
                    st.markdown(f"{icon} **{c['name']}**: {c['detail']}", unsafe_allow_html=True)
                if check["all_pass"]:
                    st.markdown(f"<div class='banner-success'>✅ SEMUA CHECK LULUS ({check['summary']})</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='banner-critical'>❌ SAFETY CHECK GAGAL ({check['summary']}) — Perbaiki masalah sebelum lanjut!</div>", unsafe_allow_html=True)
                    st.warning("Flash akan diblokir sampai semua check lulus.")
                with st.expander("10 Aturan Emas Safety Flash"):
                    for i, (k, v) in enumerate(SAFETY_RULES.items(), 1):
                        st.markdown(f"{i}. **{k.replace('_', ' ').title()}**: {v['desc']}")

    with tab2:
        st.markdown("### Deteksi Device & Cari Firmware")
        st.info("Setelah safety check lulus, scan device untuk cari firmware yang cocok.")
        if st.button("SCAN DEVICE", type="primary", use_container_width=True):
            with st.spinner("Mendeteksi device via ADB, Fastboot, EDL..."):
                dev_info = detect_device_for_flash()
                st.session_state["flash_device"] = dev_info
            if dev_info["detected"]:
                st.markdown(f"<div class='card card-green'><h3>Device Terdeteksi</h3><table><tr><td>Mode</td><td><strong>{dev_info['mode'].upper()}</strong></td></tr><tr><td>Serial</td><td><code>{dev_info['serial']}</code></td></tr><tr><td>Model</td><td>{dev_info['model']}</td></tr><tr><td>Chipset</td><td>{dev_info['chipset'] or '-'}</td></tr><tr><td>Android</td><td>{dev_info['android'] or '-'}</td></tr></table></div>", unsafe_allow_html=True)
                if dev_info["model"]:
                    arb = get_arb_level(dev_info["model"])
                    if arb["level"] >= 7:
                        st.markdown(f"<div class='banner-critical'>⚠️ ARB LEVEL {arb['level']} — DEVICE INI DILARANG DOWNGRADE! Flash hanya firmware dengan ARB ≥ {arb['level']}.</div>", unsafe_allow_html=True)
                    elif arb["level"] >= 4:
                        st.markdown(f"<div class='banner-warning'>⚠️ ARB LEVEL {arb['level']} — Hati-hati, jangan downgrade!</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='banner-success'>✅ ARB LEVEL {arb['level']} — Aman.</div>", unsafe_allow_html=True)
                    st.info(arb["note"])
                with st.expander("Link Firmware Recomendation"):
                    if dev_info.get("firmware_urls"):
                        st.markdown("Download firmware dari link berikut. Pastikan varian device SAMA PERSIS (Global/CN/IN/EU).")
                        for src, url in dev_info["firmware_urls"]:
                            st.markdown(f"- [{src}]({url})")
                    else:
                        st.info("Tidak ada link ditemukan. Coba: 'Stock ROM {model}' di Google.")
                if dev_info["mode"] in ("adb", "fastboot"):
                    st.session_state["flash_serial"] = dev_info["serial"]
            else:
                st.markdown(f"<div class='card card-red'><h3>Tidak Ada Device</h3>Colok HP via USB dan pastikan:<br>• Android: USB Debugging ON (ADB) atau Vol Down + Power (Fastboot)<br>• iPhone: DFU Mode (Vol Up + Vol Down + Side 10 detik)<br>• HP Matot: short testpoint EDL</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown("### 🔬 Verifikasi File Firmware")
        st.markdown("Pilih file firmware yang sudah di-download. Sistem akan memeriksa kecocokan dengan device.")
        fw_path = st.text_input("Path file firmware (.zip / .img / .bin)", placeholder="/home/user/Downloads/firmware.zip")
        if fw_path and st.button("VERIFIKASI FILE", type="primary"):
            dev_info = st.session_state.get("flash_device", {})
            if not dev_info.get("detected"):
                st.warning("Scan device dulu di tab 'Deteksi & Firmware'.")
            else:
                with st.spinner("Memeriksa file..."):
                    v = verify_firmware_file(fw_path, dev_info)
                if v["match_score"] >= 60:
                    cls = "card-green"
                elif v["match_score"] >= 30:
                    cls = "card-gold"
                else:
                    cls = "card-red"
                st.markdown(f"<div class='card {cls}'><h3>Hasil Verifikasi</h3><table>", unsafe_allow_html=True)
                st.markdown(f"<tr><td>Ukuran</td><td>{v['file_size_mb']} MB</td></tr><tr><td>ZIP Valid</td><td>{'✅' if v['is_zip'] else '❌'}</td></tr><tr><td>Skor Kecocokan</td><td><strong style='font-size:1.3rem;'>{v['match_score']}%</strong></td></tr><tr><td>Status</td><td><strong>{'✅ COCOK — Siap flash' if v['valid'] else '❌ TIDAK COCOK — Cari file lain'}</strong></td></tr><tr><td>Alasan</td><td>{v['reason']}</td></tr></table></div>", unsafe_allow_html=True)
                if v["checks"]:
                    with st.expander("Detail Pemeriksaan"):
                        for chk in v["checks"]:
                            st.markdown(f"- {chk}")
                if v["valid"]:
                    st.session_state["verified_firmware"] = fw_path
                    st.success("✅ Firmware terverifikasi! Lanjut ke tab Flash Eksekusi.")
                else:
                    st.warning("❌ Firmware tidak cocok! Jangan flash file ini ke device.")
                    st.info("Coba download firmware lain dari link di tab Deteksi & Firmware. Pastikan model dan varian SAMA PERSIS.")

    with tab4:
        st.markdown("### ⚡ Eksekusi Flash — Semi-Auto")
        serial = st.session_state.get("flash_serial", "")
        fw_path = st.session_state.get("verified_firmware", "")
        safety = st.session_state.get("safety_checks")
        dry_run = st.session_state.get("dry_run", True)

        if not serial:
            st.info("Step 1: Safety Check dulu di tab Safety Checklist.")
        elif not safety or not safety.get("all_pass"):
            st.error("⚠️ SAFETY CHECK BELUM LULUS! Kembali ke tab Safety Checklist.")
        elif not fw_path:
            st.info("Step 2-3: Scan device & verifikasi firmware dulu.")
        else:
            with st.expander("Ringkasan Sebelum Flash", expanded=True):
                md = ""
                md += f"**Device:** `{serial}`\n\n"
                dev_info = st.session_state.get("flash_device", {})
                if dev_info:
                    md += f"**Model:** {dev_info.get('model', '-')}\n\n"
                    md += f"**Chipset:** {dev_info.get('chipset', '-')}\n\n"
                    md += f"**Mode:** {dev_info.get('mode', '-').upper()}\n\n"
                md += f"**Firmware:** `{os.path.basename(fw_path)}`\n\n"
                md += f"**Safety Check:** ✅ LULUS\n\n"
                if dry_run:
                    md += f"**Mode:** 🔄 DRY RUN (simulasi — aman)\n\n"
                else:
                    md += f"**Mode:** ⚡ LIVE FLASH (nyata!)\n\n"
                st.markdown(md, unsafe_allow_html=True)

            st.markdown("---")
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.markdown("### Step 4a: Backup Otomatis")
                st.markdown("Backup 7 partisi penting: persist, efs, nvram, modem, boot, recovery, misc.")
                if st.button("MULAI BACKUP", type="primary", use_container_width=True):
                    with st.spinner("Backup partisi penting..."):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        out_dir = str(BASE_DIR / "backups" / f"preflash_{serial}_{timestamp}")
                        os.makedirs(out_dir, exist_ok=True)
                        partitions = ["persist", "efs", "nvram", "modem", "boot", "recovery", "misc"]
                        bar = st.progress(0)
                        backup_ok = 0
                        for i, p in enumerate(partitions):
                            r = backup_partition_fastboot(serial, p, out_dir) if serial in fastboot_devices() else backup_partition_adb(serial, p, out_dir)
                            if r["status"] == "ok":
                                backup_ok += 1
                            bar.progress((i + 1) / len(partitions))
                        if backup_ok == len(partitions):
                            st.markdown(f"<div class='banner-success'>✅ Backup {backup_ok}/{len(partitions)} partisi SELESAI → <code>{out_dir}</code></div>", unsafe_allow_html=True)
                            st.session_state["backup_done"] = True
                            st.session_state["backup_dir"] = out_dir
                        else:
                            st.markdown(f"<div class='banner-warning'>⚠️ Backup {backup_ok}/{len(partitions)} — sebagian gagal. Periksa log.</div>", unsafe_allow_html=True)
            with col_b:
                st.markdown("### Step 4b: Restore (Jika Gagal)")
                if st.session_state.get("backup_dir"):
                    st.info(f"Backup tersimpan di:\n`{st.session_state['backup_dir']}`")
                    st.markdown("Jika flash gagal, restore dengan perintah:")
                    st.code("fastboot flash partition_name backup_file.img")

            st.markdown("---")
            st.markdown("### Step 5: Flash Partisi")
            parts_to_flash = st.multiselect("Pilih partisi untuk di-flash",
                ["boot", "recovery", "system", "vendor", "dtbo", "vbmeta", "super"],
                default=["boot", "recovery"],
                help="⚠️ Jangan centang 'vbmeta' jika bootloader tidak terbuka! Bisa hardbrick.")
            wipe_data = st.checkbox("Wipe data/factory reset setelah flash", value=False,
                help="Hapus semua data pengguna setelah flash berhasil.")

            if "vbmeta" in parts_to_flash:
                bl_status = fastboot_getvar(serial, "unlocked") if serial in fastboot_devices() else ""
                bl_unlocked = bl_status in ["yes", "1"]
                if not bl_unlocked:
                    st.markdown("<div class='banner-critical'>🚫 VBMETA DIPILIH TAPI BOOTLOADER TERKUNCI! Flashing vbmeta pada bootloader LOCKED akan menyebabkan HARDBRICK! Hapus centangan vbmeta.</div>", unsafe_allow_html=True)
                    parts_to_flash = [p for p in parts_to_flash if p != "vbmeta"]
                else:
                    st.markdown("<div class='banner-warning'>⚠️ VBMETA terpilih — bootloader UNLOCKED, aman.</div>", unsafe_allow_html=True)
            if "super" in parts_to_flash:
                st.markdown("<div class='banner-critical'>⚠️ 'super' partition mengandung system/vendor/product. Pastikan firmware cocok 100%! Kesalahan bisa menyebabkan hardbrick!</div>", unsafe_allow_html=True)

            if not st.session_state.get("backup_done"):
                st.warning("Backup dulu sebelum flash!")
            elif serial not in fastboot_devices():
                st.error("Device tidak dalam mode Fastboot! Reboot ke bootloader dulu. Cara: `adb reboot bootloader`")
            else:
                if dry_run:
                    st.markdown("<div class='card card-blue'><strong>🔄 DRY RUN MODE AKTIF</strong> — Tidak ada flash beneran. Matikan centang 'Dry Run' di Safety Checklist untuk flash nyata.</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='card card-red'><strong>⚠️ LIVE MODE — Flash nyata akan dijalankan!</strong></div>", unsafe_allow_html=True)

                confirm_text = "Saya paham resiko dan ingin melanjutkan"
                user_confirm = st.text_input("Ketik persis: '{}' untuk konfirmasi".format(confirm_text))
                can_proceed = user_confirm.strip() == confirm_text

                if can_proceed and st.button("EKSEKUSI FLASH", type="primary", use_container_width=True):
                    if dry_run:
                        st.markdown(f"<div class='card card-green'><h3>🔄 DRY RUN — Simulasi Berhasil</h3>Partisi yang akan di-flash: {', '.join(parts_to_flash)}<br>Wipe data: {'Ya' if wipe_data else 'Tidak'}<br>Perintah yang akan dijalankan:<br>", unsafe_allow_html=True)
                        for p in parts_to_flash:
                            st.code(f"fastboot -s {serial} flash {p} {fw_path}")
                        if wipe_data:
                            st.code(f"fastboot -s {serial} -w")
                        st.success("Dry run selesai. Matikan centang 'Dry Run' di Safety Checklist untuk flash nyata.")
                    else:
                        if fw_path.endswith(".zip"):
                            st.markdown(f"Flashing firmware `{os.path.basename(fw_path)}`...")
                            ok, out, err = _run(["fastboot", "-s", serial, "update", fw_path], timeout=120)
                            log_flash_transaction(serial, dev_info.get("model", ""), "full_zip", fw_path, True, "ok" if ok else "failed", err)
                            if ok:
                                st.markdown(f"<span style='color:#059669;font-size:1.1rem;'>✅ FIRMWARE FLASH BERHASIL</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<span style='color:#DC2626;font-size:1.1rem;'>❌ FLASH GAGAL — {err[:100]}</span>", unsafe_allow_html=True)
                                st.error("Flash firmware gagal! Jangan reboot! Cek log.")
                        else:
                            for p in parts_to_flash:
                                st.markdown(f"Flashing `{p}`...")
                                ok, out, err = _run(["fastboot", "-s", serial, "flash", p, fw_path], timeout=120)
                                log_flash_transaction(serial, dev_info.get("model", ""), p, fw_path, True, "ok" if ok else "failed", err)
                                if ok:
                                    st.markdown(f"<span style='color:#059669;font-size:1.1rem;'>✅ {p}: FLASH BERHASIL</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<span style='color:#DC2626;font-size:1.1rem;'>❌ {p}: GAGAL — {err[:100]}</span>", unsafe_allow_html=True)
                                    st.error(f"Flash {p} gagal! Jangan reboot! Cek log dan ulangi.")
                        if wipe_data:
                            ok, out, err = _run(["fastboot", "-s", serial, "-w"], timeout=30)
                            st.markdown(f"{'✅ Wipe data berhasil' if ok else '❌ Wipe gagal: ' + err[:60]}")

                        st.markdown("<div class='banner-success'><h3>✅ FLASH SELESAI!</h3>Periksa device sebelum reboot. Pastikan tidak ada error di atas.</div>", unsafe_allow_html=True)
                        st.info("Jika semua OK, reboot device atau keluar dari fastboot.")
                        r1, r2 = st.columns(2)
                        with r1:
                            if st.button("REBOOT DEVICE", use_container_width=True):
                                _run(["fastboot", "-s", serial, "reboot"], timeout=10)
                                st.success("Device reboot!")
                        with r2:
                            st.download_button("DOWNLOAD LOG FLASH", str(st.session_state.get("safety_checks", "")), file_name="flash_log.txt")


elif menu == "Emergency Recovery Guide":
    st.title("🚨 Emergency Recovery Guide — Jangan Panik!")
    st.markdown("<div class='banner-critical'>Panduan langkah demi langkah untuk mengatasi HP brick, bootloop, matot, atau error flash. Pilih situasi yang sesuai.</div>", unsafe_allow_html=True)
    guides = emergency_recovery_guide()
    situasi = st.selectbox("Pilih Situasi Device", list(guides.keys()), format_func=lambda x: {
        "edl_9008": "🔴 Qualcomm EDL 9008 — Device mati total (tidak ada respon)",
        "mtk_preloader": "🟠 MediaTek Preloader — Device mati total (MTK)",
        "fastboot_unbrick": "🔵 Fastboot Mode — Stuck di logo / bootloop / error flash",
        "dfu_recovery": "⚪ iPhone DFU/Recovery — iTunes logo, restore gagal",
        "black_screen": "⚫ Layar Hitam — Hidup tapi tidak tampil",
        "bootloop": "🔄 Bootloop — Restart terus menerus",
        "no_download_mode": "❓ Tidak bisa masuk Download Mode / EDL",
    }.get(x, x))
    guide_content = guides.get(situasi, [])
    if guide_content:
        st.markdown(f"<div class='card card-gold'><h3>{situasi.replace('_', ' ').upper()}</h3>", unsafe_allow_html=True)
        for i, step in enumerate(guide_content, 1):
            cls = "banner-success" if i == 1 else ("banner-warning" if "jangan" in step.lower() or "hati" in step.lower() else "card")
            if step.startswith(tuple("0123456789.")):
                st.markdown(f"<div class='card'><strong>Step {step}</strong></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='{cls}' style='padding:0.7rem 1rem;margin:0.3rem 0;'>{step}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔍 Deteksi Otomatis — Biarkan sistem mendeteksi kondisi device")
    if st.button("SCAN & SARANKAN RECOVERY", type="primary", use_container_width=True):
        scan_result = dead_phone_scan()
        fb = scan_result["fastboot_devices"]
        edl = scan_result["edl_devices"]
        dfu = scan_result["dfu_devices"]
        adb = scan_result["adb_devices"]
        if edl:
            st.markdown("<div class='banner-critical'>🔴 EDL 9008 terdeteksi! Gunakan panduan Qualcomm EDL di atas.</div>", unsafe_allow_html=True)
        if dfu:
            st.markdown("<div class='banner-critical'>⚪ iPhone DFU terdeteksi! Gunakan panduan DFU/Recovery di atas.</div>", unsafe_allow_html=True)
        if fb:
            st.markdown(f"<div class='banner-info'>🔵 Fastboot device terdeteksi ({fb[0]}). Gunakan panduan Fastboot Unbrick di atas.</div>", unsafe_allow_html=True)
        if adb and not fb:
            st.markdown("<div class='banner-success'>✅ Device normal via ADB. Jika ada masalah, coba panduan Bootloop atau Black Screen.</div>", unsafe_allow_html=True)
        if not any([fb, edl, dfu, adb]):
            st.markdown("<div class='card card-red'><h3>Tidak ada device terdeteksi</h3>"
                        "Kemungkinan:<br>1. Kabel USB tidak sync (hanya charge)<br>"
                        "2. Driver tidak terinstall<br>"
                        "3. Device benar-benar mati total (hardbrick) — butuh EDL/SP Flash Tool<br>"
                        "4. Baterai habis — coba charge dulu 30 menit</div>", unsafe_allow_html=True)

    with st.expander("📋 Flash Log — Riwayat Semua Operasi Flash"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM flash_log ORDER BY created_at DESC LIMIT 20")
        logs = c.fetchall()
        conn.close()
        if logs:
            for lg in logs:
                st.markdown(f"<div class='card' style='padding:0.5rem 1rem;font-size:0.82rem;'>{'✅' if lg['status']=='ok' else '❌'} <strong>{lg['device_model'] or lg['device_serial']}</strong> — {lg['partition_name']} | {lg['created_at'][:16]}<br><span style='color:#6B7280;'>{lg['error_log'][:60] or 'OK'}</span></div>", unsafe_allow_html=True)
        else:
            st.info("Belum ada riwayat flash.")

elif menu == "Hardware Diagnosis (Windows)":
    if not HAS_HW_DIAG:
        st.error("Modul hardware_diagnosis tidak tersedia. Periksa file core/hardware_diagnosis.py")
        st.stop()
    st.title("Hardware Diagnosis — Windows Detection")
    st.markdown("""
    <p style='color:#6B7280;'>
    Mendeteksi kerusakan hardware HP melalui koneksi Windows — tanpa membuka perangkat.
    Diagnosis berdasarkan USB handshake, log flashing, BROM error, dan Kernel log.
    </p>
    """, unsafe_allow_html=True)

    tab_hw1, tab_hw2, tab_hw3, tab_hw4, tab_hw5 = st.tabs([
        "🔌 IC Charger", "💾 eMMC/UFS", "🧠 RAM", "📶 Wi-Fi/BT", "📡 Baseband"
    ])

    with tab_hw1:
        st.markdown("<h3>🔌 IC Charger & Jalur Pengisian Daya</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div class='card card-blue'>
        <strong>Prinsip:</strong> Windows mendeteksi koneksi perangkat yang flapping (connect/disconnect) setiap 1-2 detik.
        <br><strong>Indikasi:</strong> IC Charger (SMB/PMI) rusak, thermal resistor putus, atau konektor USB longgar.
        </div>
        """, unsafe_allow_html=True)
        col_c1, col_c2 = st.columns([2, 1])
        with col_c1:
            usb_input = st.text_area(
                "Tempel log USB/device manager di sini (satu baris per event):",
                height=120, placeholder="USB Device Connected\nUSB Device Disconnected\nUSB Device Connected...",
                key="hw_usb_log"
            )
        with col_c2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Diagnosis Charging", type="primary", use_container_width=True, key="diag_charging"):
                if usb_input.strip():
                    events = [l.strip() for l in usb_input.strip().split("\n") if l.strip()]
                    res = diagnose_usb_flapping(events)
                    if res.status == "faulty":
                        st.markdown(f"<div class='banner-critical'>🔴 {res.component}<br>{res.diagnosis}</div>", unsafe_allow_html=True)
                        st.markdown(f"**Confidence:** {res.confidence}%")
                        st.markdown(f"**Tindakan:**<br>{res.recommended_action}")
                    elif res.status == "suspect":
                        st.markdown(f"<div class='banner-warning'>🟡 {res.component}<br>{res.diagnosis}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='banner-success'>✅ {res.component} — Tidak terdeteksi flapping</div>", unsafe_allow_html=True)
                else:
                    st.warning("Masukkan log USB terlebih dahulu.")

    with tab_hw2:
        st.markdown("<h3>💾 eMMC / UFS (Memori Internal)</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div class='card card-blue'>
        <strong>Prinsip:</strong> HP terbaca sebagai Qualcomm 9008 / MediaTek USB Port, tapi flash/transfer file gagal (timeout/write error).
        <br><strong>Indikasi:</strong> IC eMMC/UFS rusak total. CPU dan IC Power sehat.
        </div>
        """, unsafe_allow_html=True)
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            flash_log_input = st.text_area(
                "Tempel log flashing di sini:",
                height=120, placeholder="[ERROR] Flash timeout at sector 0x1234\nWrite error: EIO\nSahara protocol error...",
                key="hw_emmc_log"
            )
        with col_m2:
            edl_detected = st.checkbox("Device terdeteksi di EDL 9008 / Preloader Mode", key="hw_edl")
            if st.button("Diagnosis eMMC", type="primary", use_container_width=True, key="diag_emmc"):
                if flash_log_input.strip():
                    lines = [l.strip() for l in flash_log_input.strip().split("\n") if l.strip()]
                    res = diagnose_emmc(lines)
                    if res.status == "faulty":
                        st.markdown(f"<div class='banner-critical'>🔴 {res.component}<br>{res.diagnosis}</div>", unsafe_allow_html=True)
                        st.markdown(f"**Confidence:** {res.confidence}%")
                        st.markdown(f"**Tindakan:**<br>{res.recommended_action}")
                    elif res.status == "suspect":
                        st.markdown(f"<div class='banner-warning'>🟡 {res.component}<br>{res.diagnosis}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div class='banner-success'>✅ {res.component} — Tidak terdeteksi error flash</div>", unsafe_allow_html=True)
                elif edl_detected:
                    st.markdown(f"<div class='banner-warning'>🟡 eMMC mencurigakan — device dalam mode EDL</div>", unsafe_allow_html=True)
                else:
                    st.warning("Masukkan log flashing atau centang EDL detected.")

    with tab_hw3:
        st.markdown("<h3>🧠 RAM (Random Access Memory)</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div class='card card-blue'>
        <strong>Prinsip:</strong> CPU terdeteksi oleh PC, tapi log BROM mencatat RAM_INIT_FAILED atau S_FT_ENABLE_DRAM_FAIL.
        <br><strong>Indikasi:</strong> Solderan RAM retak (double decker) — perlu reball.
        </div>
        """, unsafe_allow_html=True)
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            brom_input = st.text_area(
                "Tempel BROM / SP Flash Tool log di sini:",
                height=120,
                placeholder="BROM_ERROR: S_FT_ENABLE_DRAM_FAIL\n[ERROR] RAM init failed at step 3\nDRAM initialization error code: 0xC005",
                key="hw_ram_log"
            )
        with col_r2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Diagnosis RAM", type="primary", use_container_width=True, key="diag_ram"):
                if brom_input.strip():
                    lines = [l.strip() for l in brom_input.strip().split("\n") if l.strip()]
                    res = diagnose_ram(lines)
                    if res.status == "faulty":
                        st.markdown(f"<div class='banner-critical'>🔴 {res.component}<br>{res.diagnosis}</div>", unsafe_allow_html=True)
                        st.markdown(f"**Confidence:** {res.confidence}%")
                        st.markdown(f"**Tindakan:**<br>{res.recommended_action}")
                    else:
                        st.markdown(f"<div class='banner-success'>✅ {res.component} — Tidak terdeteksi error RAM</div>", unsafe_allow_html=True)
                else:
                    st.warning("Masukkan BROM log.")

    with tab_hw4:
        st.markdown("<h3>📶 IC Wi-Fi / Bluetooth</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div class='card card-blue'>
        <strong>Prinsip:</strong> HP bootloop (stuck di logo). Kernel UART log mencatat wlan_init_failed atau wcnss: chip initialization failed.
        <br><strong>Indikasi:</strong> IC Wi-Fi/BT rusak atau short. CPU stop boot karena komponen tidak responsif.
        </div>
        """, unsafe_allow_html=True)
        col_w1, col_w2 = st.columns([2, 1])
        with col_w1:
            kernel_input = st.text_area(
                "Tempel Kernel UART log di sini:",
                height=150,
                placeholder="[    3.456] wlan: wlan_init_failed: chip not responding\n[    3.789] wcnss: WCNSS chip initialization failed\n[    4.012] wl: failed to probe wlan driver",
                key="hw_wifi_log"
            )
        with col_w2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Diagnosis Wi-Fi/BT", type="primary", use_container_width=True, key="diag_wifi"):
                if kernel_input.strip():
                    res = diagnose_wifi_bt(kernel_input)
                    if res.status == "faulty":
                        st.markdown(f"<div class='banner-critical'>🔴 {res.component}<br>{res.diagnosis}</div>", unsafe_allow_html=True)
                        st.markdown(f"**Confidence:** {res.confidence}%")
                        st.markdown(f"**Tindakan:**<br>{res.recommended_action}")
                        with st.expander("Bukti log"):
                            st.code(res.evidence)
                    else:
                        st.markdown(f"<div class='banner-success'>✅ Tidak terdeteksi error Wi-Fi/BT</div>", unsafe_allow_html=True)
                else:
                    st.warning("Masukkan Kernel log.")

    with tab_hw5:
        st.markdown("<h3>📡 IC Baseband / IC Sinyal</h3>", unsafe_allow_html=True)
        st.markdown("""
        <div class='card card-blue'>
        <strong>Prinsip:</strong> Log sistem mencatat modem_silent_reset, subsys-restart: RAFT, atau modem init failure.
        <br><strong>Indikasi:</strong> Tegangan suplai IC Baseband pincang atau IC sinyal rusak.
        </div>
        """, unsafe_allow_html=True)
        col_b1, col_b2 = st.columns([2, 1])
        with col_b1:
            modem_input = st.text_area(
                "Tempel log modem/baseband di sini:",
                height=120,
                placeholder="modem_silent_reset: triggered\nsubsys-restart: RAFT subsystem crash\n[ERROR] Modem initialization failed",
                key="hw_modem_log"
            )
        with col_b2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Diagnosis Baseband", type="primary", use_container_width=True, key="diag_baseband"):
                if modem_input.strip():
                    lines = [l.strip() for l in modem_input.strip().split("\n") if l.strip()]
                    res = diagnose_baseband(lines)
                    if res.status == "faulty":
                        st.markdown(f"<div class='banner-critical'>🔴 {res.component}<br>{res.diagnosis}</div>", unsafe_allow_html=True)
                        st.markdown(f"**Confidence:** {res.confidence}%")
                        st.markdown(f"**Tindakan:**<br>{res.recommended_action}")
                    else:
                        st.markdown(f"<div class='banner-success'>✅ Tidak terdeteksi error baseband</div>", unsafe_allow_html=True)
                else:
                    st.warning("Masukkan log modem.")

elif menu == "Manajemen Tiket Service":
    st.title("Manajemen Tiket Service")
    st.markdown("<p style='color:#6B7280;'>Kelola siklus hidup tiket service: Check-In → Diagnosed → Repair → QC → Ready → Delivered</p>", unsafe_allow_html=True)

    # Filter & Search
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        filter_status = st.selectbox("Filter Status", [
            "Semua", "check_in", "diagnosed", "repair", "qc", "ready", "delivered"
        ])
    with col_f2:
        limit_count = st.selectbox("Tampilkan", [20, 50, 100, 999])
    with col_f3:
        search_q = st.text_input("Cari (nama/IMEI/model/no.HP)", placeholder="Ketik keyword...")

    conn = get_conn()
    c = conn.cursor()
    query = "SELECT * FROM pelanggan WHERE 1=1"
    params = []
    if filter_status != "Semua":
        query += " AND service_status = ?"
        params.append(filter_status)
    if search_q:
        like = f"%{search_q}%"
        query += " AND (nama LIKE ? OR imei LIKE ? OR device_model LIKE ? OR no_hp LIKE ?)"
        params += [like, like, like, like]
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit_count)
    c.execute(query, params)
    records = c.fetchall()
    conn.close()

    if not records:
        st.info("Belum ada data tiket service.")
    else:
        st.markdown(f"<div style='margin-bottom:0.5rem;color:#9CA3AF;'>Menampilkan {len(records)} tiket</div>", unsafe_allow_html=True)
        status_emoji = {"check_in": "📥", "diagnosed": "🔍", "repair": "🔧", "qc": "✅", "ready": "📦", "delivered": "🎯"}
        status_colors = {
            "check_in": "#3B82F6", "diagnosed": "#8B5CF6", "repair": "#F59E0B",
            "qc": "#10B981", "ready": "#6366F1", "delivered": "#6B7280"
        }
        next_status = {
            "check_in": "diagnosed", "diagnosed": "repair", "repair": "qc",
            "qc": "ready", "ready": "delivered", "delivered": None
        }

        for rec in records:
            s = rec["service_status"] or "check_in"
            emoji = status_emoji.get(s, "📋")
            color = status_colors.get(s, "#6B7280")
            next_s = next_status.get(s)
            with st.container():
                cols = st.columns([3, 1, 1, 1, 1, 1])
                with cols[0]:
                    st.markdown(f"<div style='border-left:4px solid {color};padding-left:0.5rem;'><strong>{rec['nama']}</strong> — {rec['device_model']}<br><span style='color:#6B7280;font-size:0.82rem;'>IMEI: {rec['imei'] or '-'} | Tgl: {rec['created_at'][:16]}</span></div>", unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(f"<div style='background:{color}20;color:{color};padding:0.2rem 0.6rem;border-radius:12px;text-align:center;font-weight:bold;font-size:0.8rem;'>{emoji} {s.upper()}</div>", unsafe_allow_html=True)
                with cols[2]:
                    if next_s:
                        if st.button(f"→ {next_s.title()}", key=f"next_{rec['id']}", use_container_width=True):
                            conn = get_conn()
                            c = conn.cursor()
                            c.execute("UPDATE pelanggan SET service_status = ? WHERE id = ?", (next_s, rec["id"]))
                            conn.commit()
                            conn.close()
                            st.rerun()
                with cols[3]:
                    with st.popover("Detail", use_container_width=True):
                        st.markdown(f"**ID:** {rec['id']}")
                        st.markdown(f"**Nama:** {rec['nama']}")
                        st.markdown(f"**No.HP:** {rec['no_hp'] or '-'}")
                        st.markdown(f"**Model:** {rec['device_model']}")
                        st.markdown(f"**IMEI:** {rec['imei'] or '-'}")
                        st.markdown(f"**Keluhan:** {rec['keluhan']}")
                        st.markdown(f"**Arus:** {rec['ampere_reading']}A / {rec['voltage_reading']}V")
                        st.markdown(f"**Diagnosis:** {rec['diagnosis'] or '-'}")
                        st.markdown(f"**Status:** {s.upper()}")
                        st.markdown(f"**Teknisi:** {rec.get('teknisi','') or '-'}")
                        st.markdown(f"**Tgl:** {rec['created_at']}")
                with cols[4]:
                    with st.popover("Edit", use_container_width=True):
                        new_nama = st.text_input("Nama", value=rec["nama"], key=f"en_{rec['id']}")
                        new_hp = st.text_input("No.HP", value=rec["no_hp"] or "", key=f"eh_{rec['id']}")
                        new_model = st.text_input("Model", value=rec["device_model"], key=f"em_{rec['id']}")
                        new_imei = st.text_input("IMEI", value=rec["imei"] or "", key=f"ei_{rec['id']}")
                        new_keluhan = st.text_area("Keluhan", value=rec["keluhan"], key=f"ek_{rec['id']}")
                        new_teknisi = st.text_input("Teknisi", value=rec.get("teknisi","") or "", key=f"et_{rec['id']}")
                        if st.button("Simpan", key=f"save_{rec['id']}", use_container_width=True):
                            conn = get_conn()
                            c = conn.cursor()
                            c.execute("UPDATE pelanggan SET nama=?, no_hp=?, device_model=?, imei=?, keluhan=?, teknisi=? WHERE id=?",
                                      (new_nama, new_hp, new_model, new_imei, new_keluhan, new_teknisi, rec["id"]))
                            conn.commit()
                            conn.close()
                            st.rerun()
                with cols[5]:
                    with st.popover("Hapus", use_container_width=True):
                        st.error("⚠️ Data akan dihapus PERMANEN!")
                        st.caption(f"Tiket #{rec['id']}: {rec['nama']} — {rec['device_model']}")
                        confirm = st.checkbox("Saya yakin ingin menghapus", key=f"conf_{rec['id']}")
                        if confirm and st.button("Ya, Hapus!", key=f"del_{rec['id']}", use_container_width=True):
                            conn = get_conn()
                            c = conn.cursor()
                            c.execute("DELETE FROM pelanggan WHERE id=?", (rec["id"],))
                            conn.commit()
                            conn.close()
                            st.rerun()
            st.markdown("<hr style='margin:0.3rem 0;border-color:#2D2D2D;'>", unsafe_allow_html=True)

    with st.expander("📊 Statistik Tiket"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("""SELECT service_status, COUNT(*) as cnt FROM pelanggan GROUP BY service_status ORDER BY cnt DESC""")
        stats = c.fetchall()
        conn.close()
        if stats:
            stat_map = {r["service_status"]: r["cnt"] for r in stats}
            for idx, (s_name, emoji) in enumerate(status_emoji.items()):
                cnt = stat_map.get(s_name, 0)
                clr = status_colors.get(s_name, "#6B7280")
                [col_s1, col_s2, col_s3, col_s4, col_s5, col_s6][idx].markdown(
                    f"<div style='background:{clr}15;border:1px solid {clr};border-radius:8px;padding:0.5rem;text-align:center;'>"
                    f"<div style='font-size:1.5rem;'>{emoji}</div>"
                    f"<div style='font-size:1.2rem;font-weight:bold;color:{clr};'>{cnt}</div>"
                    f"<div style='font-size:0.7rem;color:#9CA3AF;'>{s_name.replace('_',' ').title()}</div></div>",
                    unsafe_allow_html=True
                )

    with st.expander("🖨️ Invoice / Nota Service — Cetak PDF"):
        inv_id = st.text_input("ID Tiket untuk cetak nota", placeholder="Masukkan ID...")
        if inv_id and inv_id.isdigit():
            conn = get_conn()
            c = conn.cursor()
            c.execute("SELECT * FROM pelanggan WHERE id=?", (int(inv_id),))
            inv = c.fetchone()
            conn.close()
            if inv:
                st.markdown(f"""
                <div style='background:white;color:black;padding:2rem;border-radius:8px;max-width:400px;margin:auto;font-family:monospace;'>
                <h2 style='text-align:center;'>NOTA SERVICE</h2>
                <hr>
                <p><strong>No:</strong> INV-{inv['id']:04d}</p>
                <p><strong>Tgl:</strong> {inv['created_at'][:16]}</p>
                <p><strong>Pelanggan:</strong> {inv['nama']}</p>
                <p><strong>No.HP:</strong> {inv.get('no_hp','') or '-'}</p>
                <p><strong>Device:</strong> {inv['device_model']}</p>
                <p><strong>IMEI:</strong> {inv['imei'] or '-'}</p>
                <p><strong>Keluhan:</strong> {inv['keluhan']}</p>
                <p><strong>Diagnosis:</strong> {inv['diagnosis'] or '-'}</p>
                <p><strong>Status:</strong> {inv.get('service_status','check_in').replace('_',' ').title()}</p>
                <hr>
                <p style='text-align:center;font-size:0.8rem;'>Terima kasih telah menggunakan layanan kami</p>
                </div>
                """, unsafe_allow_html=True)
                inv_html = f"""
                <div style='background:white;color:black;padding:2rem;border-radius:8px;max-width:400px;margin:auto;font-family:monospace;'>
                <h2 style='text-align:center;'>NOTA SERVICE</h2>
                <hr>
                <p><strong>No:</strong> INV-{inv['id']:04d}</p>
                <p><strong>Tgl:</strong> {inv['created_at'][:16]}</p>
                <p><strong>Pelanggan:</strong> {inv['nama']}</p>
                <p><strong>No.HP:</strong> {inv.get('no_hp','') or '-'}</p>
                <p><strong>Device:</strong> {inv['device_model']}</p>
                <p><strong>IMEI:</strong> {inv['imei'] or '-'}</p>
                <p><strong>Keluhan:</strong> {inv['keluhan']}</p>
                <p><strong>Diagnosis:</strong> {inv['diagnosis'] or '-'}</p>
                <p><strong>Status:</strong> {inv.get('service_status','check_in').replace('_',' ').title()}</p>
                <hr>
                <p style='text-align:center;font-size:0.8rem;'>Terima kasih telah menggunakan layanan kami</p>
                </div>
                """
                st.download_button("📥 Download HTML Nota", data=inv_html, file_name=f"nota_{inv['id']:04d}.html", mime="text/html", use_container_width=True)
            else:
                st.error("Tiket tidak ditemukan")

# Auto ZIP & Transfer — hanya sekali per session
st.markdown("---", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;color:#9CA3AF;font-size:0.75rem;'>Smart Service HP Workstation v4.0 | Cross-Platform Multi-OS | 2026</div>", unsafe_allow_html=True)

if "_zip_notified" not in st.session_state:
    st.session_state._zip_notified = True
    _zip_ok, _zip_msg = create_zip()
    _copy_ok = False; _copy_msg = ""
    if _zip_ok:
        _copy_ok, _copy_msg = copy_to_sdcard()
    if _zip_ok: st.toast(f"{ZIP_NAME} berhasil dibuat!", icon="check")
    if _copy_ok: st.toast(f"{_copy_msg}", icon="phone")
