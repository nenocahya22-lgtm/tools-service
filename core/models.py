"""
models.py — Data classes / schema untuk seluruh aplikasi.
Menyimpan struktur data yang digunakan antar modul.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime


@dataclass
class DeviceInfo:
    """Informasi perangkat yang terdeteksi via ADB/Fastboot."""
    serial: str = ""
    model: str = ""
    android_version: str = ""
    bootloader_status: str = "unknown"       # locked / unlocked / unknown
    adb_connected: bool = False
    fastboot_connected: bool = False
    battery_level: int = 0
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CheckInRecord:
    """Data check-in pelanggan dan hasil diagnosis."""
    id: int = 0
    customer_name: str = ""
    no_hp: str = ""
    device_model: str = ""
    imei: str = ""
    symptoms: str = ""
    ampere_reading: float = 0.0               # dalam Ampere (misal: 0.02)
    voltage_reading: float = 0.0              # dalam Volt
    condition_note: str = ""                  # "mati_total", "tekan_power", dll
    diagnosis_result: str = ""
    severity: str = "unknown"                 # low / medium / high / critical
    recommendation: str = ""
    service_status: str = "check_in"          # check_in / diagnosed / repair / qc / ready / delivered
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class BatteryHealth:
    """Data kesehatan baterai dari ADB atau input manual."""
    current_capacity_mah: float = 0.0
    design_capacity_mah: float = 0.0
    health_percent: float = 0.0
    cycle_count: int = 0
    voltage: float = 0.0
    temperature: float = 0.0
    status_text: str = ""


@dataclass
class FirmwareLink:
    """Rekomendasi link firmware berdasarkan model HP."""
    model: str = ""
    search_urls: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
