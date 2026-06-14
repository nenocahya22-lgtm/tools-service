"""
diagnosis_engine.py — Mesin diagnosis berbasis aturan (Rule-Based AI).
Menganalisis gejala, konsumsi arus, dan kondisi perangkat untuk
menghasilkan diagnosis, tingkat keparahan, dan rekomendasi tindakan.
"""

from core.models import CheckInRecord
from core.database import get_ampere_rule


def diagnose(record: CheckInRecord) -> CheckInRecord:
    """Fungsi utama diagnosis: menganalisis data check-in dan
    menghasilkan diagnosis serta rekomendasi.

    Args:
        record: CheckInRecord yang sudah diisi data pelanggan,
                model, gejala, dan ampere reading.

    Returns:
        CheckInRecord yang sama dengan field diagnosis_result,
        severity, dan recommendation terisi.
    """
    # 1. Tentukan kondisi berdasarkan ampere + gejala
    condition = _detect_condition(record)

    # 2. Cari aturan yang cocok di database
    rule = get_ampere_rule(record.ampere_reading, condition)

    # 3. Isi hasil diagnosis
    record.diagnosis_result = rule.get("diagnosis", "Tidak terdeteksi")
    record.severity = rule.get("severity", "low")
    record.recommendation = rule.get("recommendation", "Periksa secara manual")

    # 4. Analisis tambahan berdasarkan gejala kerusakan (symptoms)
    symptom_insight = _analyze_symptoms(record.symptoms, record.device_model)
    if symptom_insight:
        record.diagnosis_result += f"\n📋 Analisis Gejala: {symptom_insight}"

    return record


def _detect_condition(record: CheckInRecord) -> str:
    """Mendeteksi kondisi perangkat berdasarkan ampere dan gejala.
    
    Returns:
        String kondisi: 'mati_total_tanpa_power' / 'mati_total_tekan_power'
    """
    symptoms_lower = record.symptoms.lower()

    # Deteksi apakah HP mati total
    is_dead = any(kw in symptoms_lower for kw in [
        "mati total", "matot", "tidak hidup", "meninggal",
        "brick", "tidak mau nyala", "black screen"
    ])

    # Deteksi apakah tombol power sudah ditekan
    power_pressed = any(kw in record.condition_note.lower() for kw in [
        "tekan", "power", "on", "ditekan"
    ])

    if is_dead:
        if power_pressed:
            return "mati_total_tekan_power"
        return "mati_total_tanpa_power"

    return "mati_total_tanpa_power"  # default


def _analyze_symptoms(symptoms: str, device_model: str) -> str:
    """Menganalisis teks gejala untuk insight tambahan.
    Menggunakan keyword matching sederhana.
    
    Args:
        symptoms: Teks gejala kerusakan dari pelanggan
        device_model: Model HP
    
    Returns:
        String insight atau string kosong jika tidak ada kecocokan.
    """
    insights = []
    s = symptoms.lower()

    # Pola gejala umum
    symptom_patterns = [
        (["jatuh", "terjatuh", "benturan", "terbentur", "jatuh dari"],
         "Terindikasi kerusakan fisik akibat benturan. Prioritaskan periksa LCD, konektor fleksibel, dan komponen BGA."),
        (["kena air", "air", "cairan", "tumpah", "kebasahan", "korosi"],
         "Terindikasi korosi akibat cairan. Segera lakukan pembersihan ultrasonic cleaning pada PCB."),
        (["panas", "overheat", "baterai cepat habis", "bocor", "kembung"],
         "Terindikasi kerusakan baterai atau IC Power. Periksa tegangan baterai dan konsumsi arus standby."),
        (["tidak bisa charge", "ngecas", "cas", "charging", "lambat"],
         "Terindikasi kerusakan di jalur charging. Periksa port USB, fleksibel charging, dan IC BQ/Charging."),
        (["tidak ada sinyal", "no signal", "tidak bisa telepon", "network"],
         "Terindikasi kerusakan di jalur RF/PA. Periksa IC PA, antenna switch, dan jalur sinyal."),
        (["layar pecah", "retak", "crack", "lcd rusak", "touch tidak berfungsi"],
         "Terindikasi kerusakan LCD/Touchscreen. Periksa konektor LCD dan fleksibel."),
        (["kamera", "tidak bisa foto", "blur", "buram"],
         "Terindikasi kerusakan modul kamera. Periksa konektor dan fleksibel kamera."),
        (["suara", "speaker", "tidak ada suara", "bunyi", "audio"],
         "Terindikasi kerusakan di jalur audio. Periksa IC audio, speaker, dan jack audio."),
        (["restart sendiri", "reboot", "hang", "macet", "ngehang"],
         "Terindikasi kerusakan software atau IC RAM/eMMC. Coba flashing ulang atau periksa tegangan IC RAM."),
        (["getar", "vibrator", "tidak bergetar"],
         "Terindikasi kerusakan motor vibrator atau IC getar. Periksa konektor motor vibrator."),
    ]

    for keywords, insight in symptom_patterns:
        if any(kw in s for kw in keywords):
            insights.append(insight)
            break  # Ambil satu insight paling relevan

    return "\n".join(insights)


def generate_battery_status(health_percent: float, cycle_count: int) -> str:
    """Menghasilkan status baterai berdasarkan health % dan cycle count.
    
    Args:
        health_percent: Persentase kesehatan baterai (0-100)
        cycle_count: Jumlah siklus pengisian
    
    Returns:
        String status dan rekomendasi.
    """
    lines = []

    if health_percent >= 85:
        lines.append("Status: ✅ BAIK — Baterai masih dalam kondisi prima")
    elif health_percent >= 70:
        lines.append("Status: ⚠️ CUKUP — Mulai terlihat degradasi, masih layak pakai")
    elif health_percent >= 50:
        lines.append("Status: 🔴 BURUK — Sangat disarankan untuk ganti baterai")
    else:
        lines.append("Status: 🚨 KRITIS — Baterai harus segera diganti!")

    if cycle_count > 800:
        lines.append(f"💡 Siklus {cycle_count} sudah >800, kapasitas turun signifikan.")
        lines.append("📌 Rekomendasi: Segera ganti baterai untuk performa optimal.")

    if health_percent < 70 and cycle_count < 300:
        lines.append("⚠️ Health rendah tapi cycle masih sedikit — kemungkinan baterai cacat pabrik.")

    return "\n".join(lines)
