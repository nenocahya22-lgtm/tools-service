"""
hardware_diagnosis.py — Diagnosis kerusakan hardware HP berbasis deteksi Windows.

Mendeteksi 5 jenis kerusakan hardware utama tanpa membuka HP:
  1. IC Charger & Jalur Charging — USB Handshake VBUS flapping
  2. eMMC / UFS (Memori Internal) — EDL mode + flash timeout
  3. RAM — BROM error codes (RAM_INIT_FAILED, S_FT_ENABLE_DRAM_FAIL)
  4. IC Wi-Fi / Bluetooth — Kernel UART log saat bootloop
  5. IC Baseband / Sinyal — Modem init failure log
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class HardwareDiagnosis:
    component: str = ""
    category: str = ""  # charging, memory, ram, wifi, baseband
    status: str = "unknown"  # healthy, suspect, faulty
    confidence: int = 0  # 0-100
    symptoms: List[str] = field(default_factory=list)
    diagnosis: str = ""
    recommended_action: str = ""
    evidence: str = ""


CHARGING_FLAP_PATTERNS = [
    r"(?i)(disconnect|connect|removed|inserted).*(usb|device).*",
    r"(?i)device.*(flapping|bouncing|toggle)",
]

EMMC_FAILURE_PATTERNS = [
    r"(?i)flash.*(timeout|fail|error|write)",
    r"(?i)write.*(error|fail)",
    r"(?i)sahara.*fail",
    r"(?i)firehose.*(fail|error|timeout)",
    r"(?i)upload.*(fail|error)",
    r"(?i)edd.*(fail|error)",
]

RAM_FAILURE_PATTERNS = [
    r"(?i)ram_init_failed",
    r"(?i)s_ft_enable_dram_fail",
    r"(?i)dram.*(fail|error)",
    r"(?i)memory.*init.*(fail|error)",
    r"(?i)brom.*error",
]

WIFI_FAILURE_PATTERNS = [
    r"(?i)wlan.*init.*(fail|error)",
    r"(?i)wcnss.*(fail|error|init)",
    r"(?i)wl.*init.*fail",
    r"(?i)chip.*(wlan|wifi|bt|bluetooth).*(fail|error)",
]

BASEBAND_FAILURE_PATTERNS = [
    r"(?i)modem.*(fail|error|crash|reset)",
    r"(?i)subsys.*restart",
    r"(?i)modem_silent_reset",
    r"(?i)raft",
    r"(?i)baseband.*(fail|error)",
    r"(?i)cp_init.*(fail|error)",
]


def diagnose_usb_flapping(events: list) -> HardwareDiagnosis:
    result = HardwareDiagnosis(
        component="IC Charger & Jalur Charging",
        category="charging",
    )
    if not events:
        result.status = "healthy"
        return result

    flapping = 0
    prev_lower = None
    for e in events:
        e_lower = e.lower()
        if prev_lower and ("connect" in e_lower or "disconnect" in e_lower):
            if ("connect" in prev_lower and "disconnect" in e_lower) or ("disconnect" in prev_lower and "connect" in e_lower):
                flapping += 1
        prev_lower = e_lower

    if flapping >= 3:
        result.status = "faulty"
        result.confidence = 85
        result.symptoms = [f"USB flapping detected: {flapping} toggle cycles", "Device connect/disconnect looping 1-2 detik"]
        result.diagnosis = "Kerusakan pada IC Charger (SMB/PMI), thermal resistor (sensor suhu) putus, atau konektor fleksibel USB longgar"
        result.recommended_action = "1. Periksa konektor fleksibel USB — bersihkan dengan alkohol\n2. Ukur thermal resistor (sensor suhu) di sekitar IC charging — jika OL, ganti\n3. Periksa tegangan VBUS di konektor USB (5V normal)\n4. Jika semua normal, ganti IC Charger (SMB/PMI)"
        result.evidence = f"USB handshake flapping {flapping}x dalam scan window"
    elif flapping > 0:
        result.status = "suspect"
        result.confidence = 40
        result.symptoms = [f"USB flapping: {flapping} toggle cycles"]
        result.diagnosis = "Fluktuasi USB tidak stabil — kemungkinan awal kerusakan IC Charger"
        result.recommended_action = "Pantau kembali dengan interval lebih panjang"
        result.evidence = f"Minor flapping {flapping}x"
    else:
        result.status = "healthy"

    return result


def diagnose_emmc(log_lines: list) -> HardwareDiagnosis:
    result = HardwareDiagnosis(
        component="eMMC / UFS (Memori Internal)",
        category="memory",
    )
    if not log_lines:
        result.status = "healthy"
        return result

    matched = []
    for line in log_lines:
        for pat in EMMC_FAILURE_PATTERNS:
            if re.search(pat, line):
                matched.append(line.strip())

    if len(matched) >= 1:
        result.status = "faulty"
        result.confidence = 80
        result.symptoms = [f"Flash timeout/error: {len(matched)} occurrence(s)", "Device masuk EDL 9008 tapi flash gagal"]
        result.diagnosis = "IC eMMC / UFS Rusak Total (Dead/Corrupted). IC Power dan CPU sehat, tetapi CPU tidak bisa membaca data dari memori internal."
        result.recommended_action = "1. Coba gunakan firmware lain yang cocok\n2. Jika tetap gagal: ganti IC eMMC/UFS dengan reballing\n3. Alternatif: gunakan ISP (In-System Programming) untuk write langsung ke eMMC\n4. Sebagai jalan terakhir: ganti motherboard"
        result.evidence = "\n".join(matched[:5])
    elif any("9008" in l or "preloader" in l.lower() for l in log_lines):
        result.status = "suspect"
        result.confidence = 50
        result.diagnosis = "Device terdeteksi di EDL/Preloader — kemungkinan eMMC bermasalah"
        result.recommended_action = "Lakukan flashing test dengan firmware original"
        result.evidence = "EDL mode detected tanpa flash test"
    else:
        result.status = "healthy"

    return result


def diagnose_ram(log_lines: list) -> HardwareDiagnosis:
    result = HardwareDiagnosis(
        component="RAM (Random Access Memory)",
        category="ram",
    )
    if not log_lines:
        result.status = "healthy"
        return result

    matched = []
    for line in log_lines:
        for pat in RAM_FAILURE_PATTERNS:
            if re.search(pat, line):
                matched.append(line.strip())

    if len(matched) >= 1:
        result.status = "faulty"
        result.confidence = 90
        result.symptoms = [f"RAM init error: {len(matched)} occurrence(s)", "CPU terdeteksi tapi RAM tidak bisa diinisialisasi"]
        result.diagnosis = "Koneksi RAM Rusak / Solderan RAM Retak. RAM bertumpuk di atas CPU (double decker) — solderan BGA retak akibat panas atau benturan."
        result.recommended_action = "1. Lakukan reball RAM: lepaskan RAM, bersihkan pad, pasang ulang dengan solder ball baru\n2. Jika masih gagal: ganti IC RAM\n3. Pastikan tidak ada komponen short di jalur data RAM"
        result.evidence = "\n".join(matched[:5])
    elif any("dram" in l.lower() for l in log_lines):
        result.status = "suspect"
        result.confidence = 35
        result.diagnosis = "Ada error terkait DRAM di log — perlu investigasi lebih lanjut"
        result.recommended_action = "Baca full BROM log dan cari kode error spesifik"
        result.evidence = "DRAM-related log entries found"
    else:
        result.status = "healthy"

    return result


def diagnose_wifi_bt(kernel_log: str) -> HardwareDiagnosis:
    result = HardwareDiagnosis(
        component="IC Wi-Fi / Bluetooth",
        category="wifi",
    )
    if not kernel_log:
        result.status = "healthy"
        return result

    matched = []
    for pat in WIFI_FAILURE_PATTERNS:
        m = re.search(pat, kernel_log)
        if m:
            ctx_start = max(0, m.start() - 50)
            ctx_end = min(len(kernel_log), m.end() + 100)
            matched.append(kernel_log[ctx_start:ctx_end].strip())

    if len(matched) >= 1:
        result.status = "faulty"
        result.confidence = 85
        result.symptoms = [f"WiFi/BT init failure: {len(matched)} occurrence(s)", "HP stuck di logo (bootloop)"]
        result.diagnosis = "IC Wi-Fi / Bluetooth Rusak atau Short. CPU menghentikan proses booting karena komponen ini tidak merespons inisialisasi."
        result.recommended_action = "1. Cek tegangan suplai IC WiFi (biasanya 1.8V dan 3.3V)\n2. Thermal detection: cari komponen panas di area IC WiFi\n3. Jika short: lepas IC WiFi, coba boot tanpa IC WiFi\n4. Jika boot normal: ganti IC WiFi"
        result.evidence = "\n".join(matched[:3])
    else:
        result.status = "healthy"

    return result


def diagnose_baseband(log_lines: list) -> HardwareDiagnosis:
    result = HardwareDiagnosis(
        component="IC Baseband / IC Sinyal (Radio Frequency)",
        category="baseband",
    )
    if not log_lines:
        result.status = "healthy"
        return result

    matched = []
    for line in log_lines:
        for pat in BASEBAND_FAILURE_PATTERNS:
            if re.search(pat, line):
                matched.append(line.strip())

    if len(matched) >= 1:
        result.status = "faulty"
        result.confidence = 75
        result.symptoms = [f"Baseband init failure: {len(matched)} occurrence(s)", "HP mati total atau restart terus"]
        result.diagnosis = "Tegangan suplai ke IC Baseband Pincang atau IC Sinyal Rusak. Modem tidak bisa melakukan inisialisasi."
        result.recommended_action = "1. Ukur tegangan suplai IC Baseband (PMIC output)\n2. Periksa komponen filter di jalur RF\n3. Reflow/reball IC Baseband\n4. Jika tidak ada perubahan: ganti IC Baseband"
        result.evidence = "\n".join(matched[:5])
    else:
        result.status = "healthy"

    return result


def diagnose_all(usb_events: list = None, flash_log: list = None,
                 brom_log: list = None, kernel_log: str = "",
                 modem_log: list = None, edl_detected: bool = False) -> List[HardwareDiagnosis]:
    results = []
    results.append(diagnose_usb_flapping(usb_events or []))
    results.append(diagnose_emmc(flash_log or []))
    results.append(diagnose_ram(brom_log or []))
    results.append(diagnose_wifi_bt(kernel_log or ""))
    results.append(diagnose_baseband(modem_log or []))
    if edl_detected and results[1].status == "healthy":
        results[1].status = "suspect"
        results[1].confidence = 30
        results[1].diagnosis = "Device dalam EDL mode — kemungkinan kerusakan software atau eMMC"
        results[1].recommended_action = "Lakukan flashing firmware original untuk memastikan"
    return results


def generate_diagnosis_report(results: List[HardwareDiagnosis]) -> str:
    faulty = [r for r in results if r.status == "faulty"]
    suspect = [r for r in results if r.status == "suspect"]
    healthy = [r for r in results if r.status == "healthy"]

    lines = ["═══ LAPORAN DIAGNOSIS HARDWARE ═══", ""]
    if faulty or suspect:
        lines.append(f"🔴 BERMASALAH: {len(faulty)} komponen rusak, {len(suspect)} mencurigakan")
        lines.append("")
        for r in faulty + suspect:
            icon = "🔴" if r.status == "faulty" else "🟡"
            lines.append(f"{icon} {r.component}")
            lines.append(f"   Diagnosis: {r.diagnosis}")
            lines.append(f"   Confidence: {r.confidence}%")
            lines.append(f"   Tindakan: {r.recommended_action}")
            if r.evidence:
                lines.append(f"   Bukti: {r.evidence[:100]}...")
            lines.append("")
    if len(healthy) == len(results):
        lines.append("✅ Semua komponen terdeteksi sehat.")
    return "\n".join(lines)
