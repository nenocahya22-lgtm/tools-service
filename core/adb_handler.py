"""
adb_handler.py — Modul deteksi perangkat via ADB & Fastboot.
Menggunakan subprocess untuk menjalankan perintah adb/fastboot.
Semua fungsi memiliki error handling agar tidak crash jika ADB tidak terinstall.
"""

import subprocess
import re
import shutil
from typing import Tuple, List, Optional
from core.models import DeviceInfo, FirmwareLink


def _run_cmd(cmd: List[str], timeout: int = 10) -> Tuple[bool, str]:
    """Menjalankan perintah shell dan mengembalikan (success, output).
    
    Args:
        cmd: List perintah, misal ['adb', 'devices']
        timeout: Timeout dalam detik
    
    Returns:
        Tuple (berhasil_tidak, stdout/stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except FileNotFoundError:
        return False, f"ERROR: Perintah '{cmd[0]}' tidak ditemukan. Install ADB dulu."
    except subprocess.TimeoutExpired:
        return False, f"ERROR: Perintah '{' '.join(cmd)}' timeout ({timeout}s)."
    except Exception as e:
        return False, f"ERROR: {str(e)}"


def check_adb_installed() -> bool:
    """Cek apakah ADB terinstall di sistem."""
    return shutil.which("adb") is not None


def check_fastboot_installed() -> bool:
    """Cek apakah Fastboot terinstall di sistem."""
    return shutil.which("fastboot") is not None


def get_adb_devices() -> List[str]:
    """Mendapatkan daftar device yang terdeteksi via 'adb devices'.
    
    Returns:
        List serial number device yang terhubung.
    """
    success, output = _run_cmd(["adb", "devices"])
    if not success:
        return []

    devices = []
    for line in output.splitlines():
        # Format: "0123456789ABCDEF\tdevice"
        if "\tdevice" in line and "List of devices" not in line:
            serial = line.split("\t")[0].strip()
            if serial:
                devices.append(serial)
    return devices


def get_fastboot_devices() -> List[str]:
    """Mendapatkan daftar device di mode fastboot via 'fastboot devices'.
    
    Returns:
        List serial number device di fastboot.
    """
    success, output = _run_cmd(["fastboot", "devices"])
    if not success:
        return []

    devices = []
    for line in output.splitlines():
        # Format: "0123456789ABCDEF\tfastboot"
        if line.strip():
            parts = line.split()
            if len(parts) >= 2 and "fastboot" in line:
                devices.append(parts[0])
    return devices


def get_device_info_adb(serial: str) -> DeviceInfo:
    """Menarik informasi detail dari device via ADB.
    
    Args:
        serial: Serial number perangkat.
    
    Returns:
        DeviceInfo dengan data yang berhasil didapat.
    """
    info = DeviceInfo(serial=serial, adb_connected=True)

    # Model HP
    success, output = _run_cmd(["adb", "-s", serial, "shell", "getprop", "ro.product.model"])
    if success and output:
        info.model = output.strip()

    # Versi Android
    success, output = _run_cmd(["adb", "-s", serial, "shell", "getprop", "ro.build.version.release"])
    if success and output:
        info.android_version = output.strip()

    # Bootloader status → via 'adb shell getprop ro.oem.unlock_supported'
    success, output = _run_cmd(["adb", "-s", serial, "shell", "getprop", "ro.boot.flash.locked"])
    if success:
        val = output.strip()
        if val == "1":
            info.bootloader_status = "locked"
        elif val == "0":
            info.bootloader_status = "unlocked"
        else:
            # Fallback: cek lewat fastboot nanti
            pass

    # Baterai
    success, output = _run_cmd(["adb", "-s", serial, "shell", "dumpsys", "battery"])
    if success:
        match = re.search(r'level:\s*(\d+)', output)
        if match:
            info.battery_level = int(match.group(1))

    return info


def get_bootloader_status_fastboot(serial: str) -> str:
    """Cek status bootloader via fastboot.
    
    Returns:
        'locked', 'unlocked', atau 'unknown'.
    """
    success, output = _run_cmd(["fastboot", "-s", serial, "getvar", "unlocked"])
    if success:
        match = re.search(r'unlocked:\s*(\S+)', output)
        if match:
            val = match.group(1).lower()
            if val == "yes" or val == "1":
                return "unlocked"
            elif val == "no" or val == "0":
                return "locked"
    return "unknown"


def scan_device() -> DeviceInfo:
    """Full scan: deteksi device di ADB dan/atau Fastboot.
    Mengembalikan DeviceInfo lengkap dari sumber mana pun yang tersedia.
    """
    info = DeviceInfo()

    # Cek apakah ADB terinstall
    if not check_adb_installed():
        info.model = "ADB tidak terinstall"
        return info

    # 1. Cek ADB
    adb_devices = get_adb_devices()
    if adb_devices:
        serial = adb_devices[0]
        info = get_device_info_adb(serial)
        info.serial = serial
        info.adb_connected = True

        # Dapatkan SDK version — simpan terpisah, jangan timpa android_version
        success, output = _run_cmd(["adb", "-s", serial, "shell", "getprop", "ro.build.version.sdk"])
        if success:
            pass  # android_version already set correctly above

    # 2. Cek Fastboot (jika device tidak terdeteksi ADB)
    if not info.adb_connected and check_fastboot_installed():
        fb_devices = get_fastboot_devices()
        if fb_devices:
            info.serial = fb_devices[0]
            info.fastboot_connected = True
            info.bootloader_status = get_bootloader_status_fastboot(fb_devices[0])

    # 3. Jika di ADB, cek bootloader via fastboot juga
    if info.adb_connected and info.bootloader_status == "unknown" and check_fastboot_installed():
        # Reboot ke fastboot untuk cek, tapi hati-hati — kita lewati dulu
        pass

    return info


def get_battery_health_adb(serial: str) -> dict:
    """Menarik data kesehatan baterai via ADB.
    
    Menggunakan perintah:
      - adb shell dumpsys battery
      - adb shell cat /sys/class/power_supply/battery/charge_full
      - adb shell cat /sys/class/power_supply/battery/charge_full_design
      - adb shell cat /sys/class/power_supply/battery/cycle_count
    
    Returns:
        Dict dengan keys: current_capacity_mah, design_capacity_mah,
                          health_percent, cycle_count, voltage, temperature
    """
    result = {
        "current_capacity_mah": 0,
        "design_capacity_mah": 0,
        "health_percent": 0,
        "cycle_count": 0,
        "voltage": 0,
        "temperature": 0,
    }

    if not serial:
        return result

    # Dumpsys battery — dapatkan voltage & temperature
    success, output = _run_cmd(["adb", "-s", serial, "shell", "dumpsys", "battery"])
    if success:
        match = re.search(r'voltage:\s*(\d+)', output)
        if match:
            result["voltage"] = round(int(match.group(1)) / 1000, 3)  # mV → V

        match = re.search(r'temperature:\s*(\d+)', output)
        if match:
            result["temperature"] = round(int(match.group(1)) / 10, 1)  # tenth °C → °C

    # charge_full (kapasitas aktual)
    success1, cap_now = _run_cmd(["adb", "-s", serial, "shell", "cat",
                                   "/sys/class/power_supply/battery/charge_full"])

    # charge_full_design (kapasitas pabrik)
    success2, cap_design = _run_cmd(["adb", "-s", serial, "shell", "cat",
                                      "/sys/class/power_supply/battery/charge_full_design"])

    # cycle_count
    success3, cycles = _run_cmd(["adb", "-s", serial, "shell", "cat",
                                  "/sys/class/power_supply/battery/cycle_count"])

    if success1 and cap_now.strip().isdigit():
        result["current_capacity_mah"] = round(int(cap_now.strip()) / 1000, 2)

    if success2 and cap_design.strip().isdigit():
        result["design_capacity_mah"] = round(int(cap_design.strip()) / 1000, 2)

    if success3 and cycles.strip().isdigit():
        result["cycle_count"] = int(cycles.strip())

    # Hitung health %
    if result["design_capacity_mah"] > 0:
        result["health_percent"] = round(
            (result["current_capacity_mah"] / result["design_capacity_mah"]) * 100, 2
        )

    return result


def generate_firmware_links(model: str) -> FirmwareLink:
    """Menghasilkan rekomendasi link pencarian firmware berdasarkan model HP.
    
    Membuat URL pencarian ke berbagai sumber firmware:
    - Google Search (fallback universal)
    - Firmware27 (sumber firmware Indonesia)
    - XDA Developers Forum
    - SamMobile (khusus Samsung)
    - MIUI ROM (khusus Xiaomi)
    
    Args:
        model: Nama model HP (misal: 'Redmi Note 13', 'Samsung A54')
    
    Returns:
        FirmwareLink dengan daftar URL.
    """
    links = FirmwareLink(model=model)
    query = model.replace(" ", "+")

    # Google Search — universal fallback
    links.search_urls.append(f"https://www.google.com/search?q={query}+stock+rom+firmware+download")
    links.sources.append("Google Search")

    # Firmware27 — situs firmware Indonesia
    links.search_urls.append(f"https://firmware27.com/?s={query.replace('+', '-')}")
    links.sources.append("Firmware27")

    # XDA Developers
    links.search_urls.append(f"https://www.xda-developers.com/?s={query}")
    links.sources.append("XDA Developers")

    # Deteksi brand untuk link spesifik
    model_lower = model.lower()

    if "samsung" in model_lower or model_lower.startswith("a") or model_lower.startswith("s"):
        links.search_urls.append(f"https://www.sammobile.com/?s={query}")
        links.sources.append("SamMobile")

    if "xiaomi" in model_lower or "redmi" in model_lower or "poco" in model_lower or "mi " in model_lower:
        links.search_urls.append(f"https://miuirom.org/?s={query.replace('+', '-')}")
        links.sources.append("MIUI ROM")

    if "iphone" in model_lower or "ipad" in model_lower:
        links.search_urls.append("https://ipsw.me")
        links.sources.append("IPSW.me (Firmware iOS)")

    # Link spesifik flashing tool sesuai brand
    if any(x in model_lower for x in ["mediatek", "mt", "dimensity"]):
        links.search_urls.append("https://spflashtool.com/")
        links.sources.append("SP Flash Tool (MediaTek)")
    if any(x in model_lower for x in ["qualcomm", "snapdragon"]):
        links.search_urls.append("https://qpsttool.com/")
        links.sources.append("QPST (Qualcomm)")

    links.search_urls.append("https://developer.android.com/studio/releases/platform-tools")
    links.sources.append("Platform Tools (ADB/Fastboot)")

    return links
