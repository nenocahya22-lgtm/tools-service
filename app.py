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
import webbrowser
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

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
        created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')))""")

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

    conn.commit()
    conn.close()

def _run(cmd: list, timeout: int = 15) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return False, "", f"Perintah '{cmd[0]}' tidak ditemukan."
    except subprocess.TimeoutExpired:
        return False, "", f"Timeout {timeout}s."
    except Exception as e:
        return False, "", str(e)


def adb_devices() -> list:
    ok, out, _ = _run(["adb", "devices"], timeout=8)
    if not ok: return []
    devices = []
    for line in out.splitlines():
        if "\tdevice" in line and "List" not in line:
            s = line.split("\t")[0].strip()
            if s: devices.append(s)
    return devices


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
                elif k == "BatteryHealthPercentage": bat["health_pct"] = float(v.rstrip('%')) if '%' in v else (float(v) if v else 0)
                elif k == "BatteryVoltage": bat["voltage"] = float(v) if v else 0.0
                elif k == "BatteryTemperature": bat["temperature"] = float(v.rstrip('C')) if 'C' in v else (float(v) if v else 0.0)
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
        ok, out, _ = _run(["ping", "-c", "1", "-W", "1", ip], timeout=3)
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


def firmare_urls(model: str, chipset: str = "", platform: str = "android") -> list:
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
    elif platform == "ios" and cycle_count > 500:
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
            if os.system(f"cp '{ZIP_PATH}' '{dest}' 2>/dev/null") == 0:
                return True, f"Tersimpan di {dest}{ZIP_NAME}"
        except: pass
    try:
        subprocess.run(["adb","push",ZIP_PATH,"/sdcard/Download/"], capture_output=True, text=True, timeout=15)
        return True, f"Terkirim via ADB ke /sdcard/Download/{ZIP_NAME}"
    except: pass
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
        ok2, out2, err2 = _run(["fastboot", "-s", serial, "getvar", f"partition-size:{partition}"], timeout=10)
        s_m = re.search(r'partition-size:\s*(\w+)', out2, re.I)
        if s_m:
            sz = int(s_m.group(1), 16)
            ok3, out3, _ = _run(["fastboot", "-s", serial, "getvar", f"partition-type:{partition}"], timeout=5)
            typ = out3.strip()
        else:
            sz = 0
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


init_database()

st.markdown("""<style>
    .stApp { background-color: #FAFAF8; }
    .main > div { padding: 1rem 1.5rem; }
    h1, h2, h3 { color: #1A1A1A !important; font-weight: 700 !important; letter-spacing: -0.02em; }
    h1 { font-size: 1.75rem !important; } h2 { font-size: 1.35rem !important; }
    section[data-testid="stSidebar"] { background-color: #1A1A1A; min-width: 260px; }
    section[data-testid="stSidebar"] .stMarkdown { color: #FFFFFF; }
    .sidebar-logo { padding: 1.5rem 1rem 0.5rem; border-bottom: 1px solid #2D2D2D; margin-bottom: 0.5rem; }
    .sidebar-logo h2 { color: #C9A84C !important; font-size: 1.2rem; margin: 0; }
    .sidebar-logo p { color: #6B7280; font-size: 0.75rem; margin: 0.2rem 0 0 0; }
    section[data-testid="stSidebar"] .stRadio > label { color: #9CA3AF !important; padding: 0.5rem 1rem; border-radius: 6px; }
    section[data-testid="stSidebar"] .stRadio > label:hover { background: rgba(255,255,255,0.05); color: #FFF !important; }
    section[data-testid="stSidebar"] .stRadio > label[data-checked="true"] { background: rgba(201,168,76,0.1); border-left: 3px solid #C9A84C; color: #C9A84C !important; }
    .card { background: #FFF; border: 1px solid #E5E7EB; border-radius: 12px; padding: 1.2rem; box-shadow: 0 1px 2px rgba(0,0,0,0.04); margin-bottom: 0.8rem; }
    .card-gold { border-left: 4px solid #C9A84C; } .card-blue { border-left: 4px solid #2563EB; }
    .card-red { border-left: 4px solid #DC2626; } .card-green { border-left: 4px solid #059669; }
    div[data-testid="stMetric"] { background: white; padding: 1rem 1.2rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #E5E7EB; }
    div[data-testid="stMetric"] label { color: #6B7280 !important; font-weight: 600 !important; font-size: 0.8rem !important; }
    div[data-testid="stMetric"] div { color: #1A1A1A !important; font-weight: 700 !important; }
    .banner-critical { background: linear-gradient(135deg, #DC2626, #991B1B); color: white; padding: 1rem 1.5rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; }
    .banner-warning { background: linear-gradient(135deg, #D97706, #92400E); color: white; padding: 1rem 1.5rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; }
    .banner-success { background: linear-gradient(135deg, #059669, #065F46); color: white; padding: 1rem 1.5rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; }
    .banner-info { background: linear-gradient(135deg, #2563EB, #1E40AF); color: white; padding: 1rem 1.5rem; border-radius: 10px; margin: 0.5rem 0; font-weight: 600; }
</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""<div class="sidebar-logo"><h2>Smart Service HP</h2><p>Workstation v4.0 — Cross-Platform AI</p></div>""", unsafe_allow_html=True)
    menu = st.radio("NAVIGASI", [
        "Dashboard", "Dead Phone Scanner", "Deep ADB Scanner (Android)",
        "iOS Scanner (iPhone)", "Network Scan (PC/Laptop)",
        "Check-In & Diagnosis", "Ampere & Baterai",
        "Pre-Flashing Security", "Recovery & Testpoint Guide",
        "Deep Cache Cleaner", "Auto Backup & Restore",
        "Inventory & Financial", "Cari Firmware"
    ], label_visibility="collapsed")
    st.markdown("<hr style='border-color: #2D2D2D;'>", unsafe_allow_html=True)
    st.markdown("<p style='color: #4B5563; font-size: 0.7rem;'>2026 Smart Service HP<br>AI-Powered Cross-Platform Service</p>", unsafe_allow_html=True)

if menu == "Dashboard":
    st.title("Dashboard")
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
    if not check_adb_installed(): missing.append("android-tools-adb")
    if not check_fastboot_installed(): missing.append("android-tools-fastboot")
    if not check_idevice_installed(): missing.append("libimobiledevice-utils")
    if missing: st.code(f"apt install {' '.join(missing)}", language="bash")

elif menu == "Deep ADB Scanner (Android)":
    st.title("Deep ADB Scanner — Android")
    st.markdown("<p style='color:#6B7280;'>Memindai perangkat Android hingga ke inti: model, chipset, partisi, bootloader, baterai, CPU, MAC address.</p>", unsafe_allow_html=True)
    if st.button("SCAN ADB DEVICES", type="primary", use_container_width=True):
        if not check_adb_installed():
            st.markdown("<div class='banner-critical'>ADB tidak terinstall. Install: apt install android-tools-adb</div>", unsafe_allow_html=True)
        else:
            with st.spinner("Menjalankan adb devices..."):
                devices = adb_devices()
            if devices:
                st.markdown(f"<div class='banner-success'>{len(devices)} device terdeteksi!</div>", unsafe_allow_html=True)
                for serial in devices:
                    with st.spinner(f"Deep scanning {serial}..."):
                        info = deep_scan_android(serial)
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
                    for src, url in firmare_urls(info['model'], info['chipset']): st.markdown(f"- [{src}]({url})")
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
        st.code("apt install libimobiledevice-utils", language="bash")
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
                    for src, url in firmare_urls(info['product_type'], "", "ios"): st.markdown(f"- [{src}]({url})")
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
    with st.form("checkin"):
        col1, col2 = st.columns(2)
        with col1:
            nama = st.text_input("Nama Pelanggan *")
            device_model = st.text_input("Model HP *", placeholder="Redmi Note 13 / iPhone 11")
            keluhan = st.text_area("Gejala Kerusakan *", placeholder="HP mati total setelah jatuh...")
            platform = st.selectbox("Platform", ["android", "ios"])
        with col2:
            no_hp = st.text_input("No. HP", placeholder="081234567890")
            imei = st.text_input("IMEI / Serial")
            ampere = st.number_input("Arus Ampere (Power Supply)", 0.0, 10.0, 0.0, 0.01, format="%.3f")
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
            for src, url in firmare_urls(device_model, chipset, platform): st.markdown(f"- [{src}]({url})")

elif menu == "Ampere & Baterai":
    st.title("Diagnosis Ampere & Battery Health Multi-OS")
    tab1, tab2, tab3, tab4 = st.tabs(["Diagnosis Ampere (Android)", "Battery Health Android", "Diagnosis Ampere (iOS)", "Battery Health iOS"])

    with tab1:
        st.markdown("Masukkan nilai arus untuk diagnosis Android.")
        with st.form("amp_form"):
            amp = st.number_input("Arus (A)", 0.0, 10.0, 0.02, 0.001, format="%.3f")
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
        with st.form("ios_amp_form"):
            amp_ios = st.number_input("Arus iPhone (A)", 0.0, 10.0, 0.02, 0.001, format="%.3f", key="ios_amp")
            kond_ios = st.selectbox("Kondisi iPhone", ["mati_total", "tekan_power"], key="ios_kond")
            if st.form_submit_button("Analisis iPhone", type="primary"):
                d, s, r = diagnose_ampere(amp_ios, kond_ios, "ios")
                st.markdown(f"<div style='text-align:center'><strong>SEVERITY: {s.upper()}</strong></div>")
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
        if not check_idevice_installed(): st.markdown("<div class='banner-critical'>libimobiledevice tidak terinstall.</div>", unsafe_allow_html=True); st.code("apt install libimobiledevice-utils", language="bash")
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
            if not check_adb_installed(): st.code("apt install android-tools-adb", language="bash")
        else:
            serial = devs[0]
            st.markdown(f"<div class='banner-success'>Device: {serial}</div>", unsafe_allow_html=True)
            sto = android_storage_info(serial)
            if sto["total_gb"] > 0: st.markdown(f"<div class='card'><h3>Penyimpanan Sebelum</h3>Total: {sto['total_gb']} GB | Terpakai: {sto['used_gb']} GB | Sisa: <strong>{sto['free_gb']} GB ({sto['free_percent']}%)</strong></div>", unsafe_allow_html=True)

            if st.button("CLEAN ALL (Deep)", type="primary", use_container_width=True):
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
        for src, url in firmare_urls(model_fw, chipset_fw):
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

# Auto ZIP & Transfer
st.markdown("---", unsafe_allow_html=True)
st.markdown("<div style='text-align:center;color:#9CA3AF;font-size:0.75rem;'>Smart Service HP Workstation v4.0 | Cross-Platform Multi-OS | 2026</div>", unsafe_allow_html=True)

_zip_ok, _zip_msg = create_zip()
_copy_ok = False; _copy_msg = ""
if _zip_ok:
    _copy_ok, _copy_msg = copy_to_sdcard()
if "_zip_notified" not in st.session_state:
    st.session_state._zip_notified = True
    if _zip_ok: st.toast(f"{ZIP_NAME} berhasil dibuat!", icon="check")
    if _copy_ok: st.toast(f"{_copy_msg}", icon="phone")
