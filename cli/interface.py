"""
interface.py — Antarmuka CLI (Command Line Interface) untuk Smart Service HP.
Menyediakan menu interaktif berbasis teks dengan output rapi dan profesional.
Menggunakan library 'rich' jika tersedia, fallback ke print biasa.
"""

import sys
import os
from datetime import datetime
from typing import Optional

# Coba import rich — jika tidak ada, fallback ke fungsi sederhana
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.layout import Layout
    from rich import box
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import modul internal
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.database import (
    init_database, save_check_in, get_all_check_ins,
    search_check_ins, update_check_in, delete_check_in
)
from core.adb_handler import (
    scan_device, get_battery_health_adb, generate_firmware_links,
    check_adb_installed, check_fastboot_installed
)
from core.diagnosis_engine import diagnose, generate_battery_status
from core.models import CheckInRecord, BatteryHealth


# ─── Rich Console (jika tersedia) ─────────────────────────────────

console = Console() if RICH_AVAILABLE else None


def print_header(text: str, char: str = "="):
    """Print header dengan formatting rapi."""
    width = 60
    if RICH_AVAILABLE:
        console.print(f"\n[bold cyan]{text}[/bold cyan]")
        console.print(char * width, style="dim")
    else:
        print(f"\n{text}")
        print(char * width)


def print_success(text: str):
    if RICH_AVAILABLE:
        console.print(f"[bold green]✅ {text}[/bold green]")
    else:
        print(f"[OK] {text}")


def print_warning(text: str):
    if RICH_AVAILABLE:
        console.print(f"[bold yellow]⚠️ {text}[/bold yellow]")
    else:
        print(f"[!] {text}")


def print_error(text: str):
    if RICH_AVAILABLE:
        console.print(f"[bold red]❌ {text}[/bold red]")
    else:
        print(f"[ERR] {text}")


def print_info(text: str):
    if RICH_AVAILABLE:
        console.print(f"[cyan]ℹ️  {text}[/cyan]")
    else:
        print(f"[i] {text}")


def print_table(title: str, columns: list, rows: list):
    """Print tabel dengan formatting rapi. Menggunakan rich jika tersedia."""
    if RICH_AVAILABLE:
        table = Table(title=title, box=box.ROUNDED, header_style="bold cyan")
        for col in columns:
            table.add_column(col)
        for row in rows:
            table.add_row(*[str(c) for c in row])
        console.print(table)
    else:
        # Fallback: tabel sederhana
        print(f"\n{title}")
        sep = "-" * 60
        print(sep)
        header = " | ".join(f"{c:<15}" for c in columns)
        print(header)
        print(sep)
        for row in rows:
            print(" | ".join(f"{str(c):<15}" for c in row))
        print(sep)


def print_panel(text: str, title: str = "", style: str = "cyan"):
    """Print panel informasi. Rich-only fallback ke print biasa."""
    if RICH_AVAILABLE:
        console.print(Panel(text, title=title, border_style=style))
    else:
        if title:
            print(f"\n--- {title} ---")
        print(text)
        print("-" * 40)


def input_text(prompt: str, default: str = "") -> str:
    """Input teks dari user."""
    if RICH_AVAILABLE:
        return Prompt.ask(f"[cyan]{prompt}[/cyan]", default=default)
    else:
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else default


def input_float(prompt: str, default: float = 0.0) -> float:
    """Input angka float dari user."""
    while True:
        try:
            if RICH_AVAILABLE:
                val = Prompt.ask(f"[cyan]{prompt}[/cyan]", default=str(default))
            else:
                val = input(f"{prompt} [{default}]: ").strip() or str(default)
            return float(val)
        except ValueError:
            print_error("Masukkan angka yang valid!")


# ─── Menu-Menu ────────────────────────────────────────────────────

def show_splash():
    """Menampilkan splash screen aplikasi."""
    splash = """
╔══════════════════════════════════════════════════════╗
║     🔧 SMART SERVICE HP WORKSTATION v4.0            ║
║     Sistem Diagnosa & Manajemen Service HP           ║
║     Enterprise Rule-Based AI Engine                  ║
╚══════════════════════════════════════════════════════╝
    """
    if RICH_AVAILABLE:
        console.print(Panel(splash.strip(), style="bold cyan", box=box.DOUBLE_EDGE))
    else:
        print(splash)


def menu_adb_scan():
    """Menu 1: Deteksi perangkat via ADB & Fastboot."""
    print_header("📱 DETEKSI ADB & FASTBOOT")

    # Cek instalasi
    adb_ok = check_adb_installed()
    fb_ok = check_fastboot_installed()

    print_info(f"ADB: {'✅ Terinstall' if adb_ok else '❌ Tidak ditemukan'}")
    print_info(f"Fastboot: {'✅ Terinstall' if fb_ok else '❌ Tidak ditemukan'}")

    if not adb_ok and not fb_ok:
        print_warning("Install ADB & Fastboot dulu:")
        print_info("Install ADB & Fastboot: scoop install adb (Windows) / apt install android-tools-adb (Linux)")
        input("\nTekan Enter untuk kembali...")
        return

    print_info("Memindai perangkat...")
    device = scan_device()

    if device.adb_connected:
        print_success(f"Device terdeteksi via ADB!")
        print_table(
            "INFORMASI PERANGKAT",
            ["Parameter", "Value"],
            [
                ["Serial", device.serial],
                ["Model", device.model or "Tidak terbaca"],
                ["Android", device.android_version or "Tidak terbaca"],
                ["Bootloader", device.bootloader_status.upper()],
                ["Baterai", f"{device.battery_level}%"],
            ]
        )

        # Tanya apakah mau scan baterai via ADB
        if RICH_AVAILABLE and Confirm.ask("\nScan kesehatan baterai via ADB?"):
            _scan_battery_adb(device.serial)

        # Tampilkan rekomendasi firmware
        if device.model:
            _show_firmware_links(device.model)

    elif device.fastboot_connected:
        print_success(f"Device terdeteksi di mode FASTBOOT!")
        print_info(f"Serial: {device.serial}")
        print_info(f"Bootloader: {device.bootloader_status.upper()}")

        if device.bootloader_status == "locked":
            print_warning("Bootloader terkunci. Flashing terbatas.")
        elif device.bootloader_status == "unlocked":
            print_success("Bootloader terbuka! Siap untuk flashing custom.")

    else:
        print_warning("Tidak ada device terdeteksi.")
        print_info("Pastikan:")
        print_info("  1. USB Debugging sudah diaktifkan di HP")
        print_info("  2. Kabel USB berfungsi dengan baik")
        print_info("  3. HP dalam keadaan hidup (untuk ADB) atau Fastboot mode")
        print_info("  4. Coba restart ADB server: adb kill-server && adb start-server")

    input("\nTekan Enter untuk kembali ke menu...")


def _scan_battery_adb(serial: str):
    """Scan kesehatan baterai via ADB."""
    print_info("Mengambil data baterai via ADB...")
    data = get_battery_health_adb(serial)

    if data["design_capacity_mah"] == 0:
        print_warning("Tidak dapat membaca data baterai. Mungkin file sys tidak tersedia.")
        return

    health = data["health_percent"]
    status = generate_battery_status(health, data["cycle_count"])

    print_table(
        "🔋 KESEHATAN BATERAI",
        ["Parameter", "Value"],
        [
            ["Kapasitas Aktual", f'{data["current_capacity_mah"]} mAh'],
            ["Kapasitas Pabrik", f'{data["design_capacity_mah"]} mAh'],
            ["Kesehatan", f'{health}%'],
            ["Siklus Charger", str(data["cycle_count"])],
            ["Voltase", f'{data["voltage"]}V'],
            ["Suhu", f'{data["temperature"]}°C'],
        ]
    )

    print_panel(status, title="Diagnosis Baterai", style="green" if health > 70 else "yellow")


def _show_firmware_links(model: str):
    """Tampilkan rekomendasi link firmware berdasarkan model."""
    print_info(f"Mencari link firmware untuk: {model}")
    links = generate_firmware_links(model)

    if RICH_AVAILABLE:
        table = Table(title=f"📥 REKOMENDASI LINK FIRMWARE — {model}",
                       box=box.ROUNDED, header_style="bold yellow")
        table.add_column("No", style="dim")
        table.add_column("Sumber")
        table.add_column("URL")
        for i, (url, src) in enumerate(zip(links.search_urls, links.sources), 1):
            table.add_row(str(i), src, url)
        console.print(table)
    else:
        print(f"\n📥 REKOMENDASI LINK FIRMWARE — {model}")
        print("-" * 60)
        for i, (url, src) in enumerate(zip(links.search_urls, links.sources), 1):
            print(f"{i}. [{src}] {url}")


def menu_check_in():
    """Menu 2: Smart Check-In & Diagnosis Hardware + Ampere."""
    print_header("📋 SMART CHECK-IN & DIAGNOSIS")

    # Input data pelanggan
    record = CheckInRecord()
    record.customer_name = input_text("Nama Pelanggan", default="Walk-in Customer")
    record.no_hp = input_text("No. HP Pelanggan (opsional)", default="")
    record.device_model = input_text("Model HP", default="Unknown")
    record.imei = input_text("IMEI (opsional)", default="-")
    record.symptoms = input_text("Gejala Kerusakan")

    # Input ampere
    print_info("\n--- MASUKAN PEMBACAAN ARUS (Ampere) ---")
    print_info("Colokkan HP ke Power Supply / USB Analyzer")
    print_info("Lalu masukkan angka yang tertera di alat:")
    record.ampere_reading = input_float("Arus (A) — contoh: 0.02, 0.5, 1.2", default=0.0)
    record.voltage_reading = input_float("Tegangan (V) — contoh: 3.7, 5.0", default=0.0)

    # Kondisi
    print_info("\nKondisi perangkat saat pengukuran:")
    print_info("  1. Mati total — tanpa tekan tombol power")
    print_info("  2. Mati total — sudah tekan tombol power")
    cond = input_text("Pilih kondisi [1/2]", default="1")
    record.condition_note = "mati_total_tanpa_power" if cond == "1" else "mati_total_tekan_power"

    # ── Proses Diagnosis ──
    print_info("\n🔍 Menjalankan diagnosis AI...")
    record = diagnose(record)

    # ── Tampilkan Hasil ──
    severity_colors = {
        "low": "green", "medium": "yellow",
        "high": "red", "critical": "bold red"
    }
    severity_icons = {
        "low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"
    }
    color = severity_colors.get(record.severity, "cyan")
    icon = severity_icons.get(record.severity, "❓")

    print_header("📊 HASIL DIAGNOSIS")

    if RICH_AVAILABLE:
        console.print(Panel(
            f"""[bold]Nama:[/bold] {record.customer_name}
[bold]Model:[/bold] {record.device_model}
[bold]Gejala:[/bold] {record.symptoms}
[bold]Arus:[/bold] {record.ampere_reading}A | {record.voltage_reading}V

[bold {color}]{icon} SEVERITY: {record.severity.upper()}[/bold {color}]

[bold]Diagnosis:[/bold]
{record.diagnosis_result}

[bold]Rekomendasi:[/bold]
{record.recommendation}""",
            title="🔬 AI DIAGNOSIS RESULT",
            border_style=color,
            box=box.ROUNDED
        ))
    else:
        print(f"""
--- HASIL DIAGNOSIS ---
Nama:       {record.customer_name}
Model:      {record.device_model}
Gejala:     {record.symptoms}
Arus:       {record.ampere_reading}A | {record.voltage_reading}V

{icon} SEVERITY: {record.severity.upper()}

Diagnosis:
{record.diagnosis_result}

Rekomendasi:
{record.recommendation}
------------------------""")

    # ── Tanya apakah mau input data baterai manual ──
    if RICH_AVAILABLE:
        if Confirm.ask("\nInput data baterai manual?"):
            _input_battery_manual()

    # ── Simpan ke database ──
    if RICH_AVAILABLE and Confirm.ask("\nSimpan hasil ke database?"):
        save_check_in(record)
        print_success("Data tersimpan di service_hp.db ✅")
    elif not RICH_AVAILABLE:
        save = input("\nSimpan ke database? (y/n): ").lower()
        if save == 'y':
            save_check_in(record)
            print("[OK] Data tersimpan di service_hp.db")

    # ── Tampilkan rekomendasi firmware ──
    if record.device_model and record.device_model != "Unknown":
        _show_firmware_links(record.device_model)

    input("\nTekan Enter untuk kembali ke menu...")


def _input_battery_manual():
    """Input data baterai secara manual."""
    print_info("\n--- INPUT DATA BATERAI MANUAL ---")
    capacity = input_float("Kapasitas Saat Ini (mAh)", default=0)
    design = input_float("Kapasitas Pabrik (mAh)", default=0)
    cycles = input_float("Cycle Count", default=0)
    voltage = input_float("Voltase (V)", default=0)

    if design > 0:
        health = (capacity / design) * 100
    else:
        health = 0

    status = generate_battery_status(health, int(cycles))

    print_table(
        "🔋 HASIL BATERAI",
        ["Parameter", "Value"],
        [
            ["Kapasitas", f"{capacity} mAh"],
            ["Pabrik", f"{design} mAh"],
            ["Kesehatan", f"{health:.1f}%"],
            ["Siklus", str(int(cycles))],
            ["Voltase", f"{voltage}V"],
        ]
    )
    print_panel(status, title="Diagnosis Baterai")


def menu_history():
    """Menu 3: Riwayat Check-In — Cari, Edit, Hapus."""
    limit = 20

    while True:
        print_header("📜 RIWAYAT CHECK-IN")

        if RICH_AVAILABLE:
            console.print(Panel("""[bold cyan]OPSI RIWAYAT[/bold cyan]

[1] 📋  Lihat semua (20 terbaru)
[2] 🔍  Cari berdasarkan nama/IMEI/model/no.HP
[3] ✏️   Edit status / data record
[4] 🗑️   Hapus record
[5] ↩️   Kembali""", title="Riwayat", border_style="blue"))
            sub = Prompt.ask("Pilih", choices=["1","2","3","4","5"])
        else:
            print("""
  [1] 📋  Lihat semua (20 terbaru)
  [2] 🔍  Cari
  [3] ✏️   Edit
  [4] 🗑️   Hapus
  [5] ↩️  Kembali
            """)
            sub = input("Pilih [1-5]: ").strip()

        if sub == "1":
            records = get_all_check_ins(limit=limit)
            _display_records(records)
        elif sub == "2":
            kw = input_text("Cari (nama/IMEI/model/no.HP)")
            records = search_check_ins(kw, limit=limit)
            _display_records(records)
        elif sub == "3":
            _edit_record()
        elif sub == "4":
            _delete_record()
        elif sub == "5":
            break
        else:
            print_error("Pilihan tidak valid.")


def _display_records(records: list):
    """Tampilkan daftar record dan detail."""
    if not records:
        print_info("Tidak ada data ditemukan.")
        input("\nTekan Enter...")
        return

    status_icons = {
        "check_in": "📥", "diagnosed": "🔍", "repair": "🔧",
        "qc": "✅", "ready": "📦", "delivered": "🎯"
    }

    rows = []
    for r in records:
        sev_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
        s_icon = status_icons.get(r.get("service_status","check_in"), "📋")
        icon = sev_icon.get(r["severity"], "⚪")
        status_label = r.get("service_status","check_in").replace("_"," ").title()
        rows.append([
            r["id"],
            r["customer_name"][:12],
            r["device_model"][:12],
            f'{r["ampere_reading"]}A',
            f'{icon} {r["severity"].upper()}',
            f'{s_icon} {status_label[:8]}',
            r["created_at"][:10],
        ])

    print_table(
        "DATA CHECK-IN",
        ["ID", "Pelanggan", "Model", "Arus", "Severity", "Status", "Tgl"],
        rows
    )

    show_id = input_text("\nLihat detail ID", default="0")
    if show_id != "0":
        for r in records:
            if str(r["id"]) == show_id:
                status_str = r.get("service_status","check_in").replace("_"," ").title()
                detail = (
                    f"ID: {r['id']}\n"
                    f"Pelanggan: {r['customer_name']}\n"
                    f"No.HP: {r.get('no_hp','-')}\n"
                    f"Model: {r['device_model']}\n"
                    f"IMEI: {r['imei'] or '-'}\n"
                    f"Gejala: {r['symptoms']}\n"
                    f"Arus: {r['ampere_reading']}A / {r['voltage_reading']}V\n\n"
                    f"Diagnosis:\n{r['diagnosis_result']}\n\n"
                    f"Severity: {r['severity'].upper()}\n"
                    f"Status: {status_str}\n"
                    f"Rekomendasi:\n{r['recommendation']}\n\n"
                    f"Tgl: {r['created_at']}"
                )
                if RICH_AVAILABLE:
                    console.print(Panel(detail, title=f"📋 DETAIL CHECK-IN #{r['id']}", border_style="cyan"))
                else:
                    print(f"\n--- DETAIL CHECK-IN #{r['id']} ---")
                    print(detail)
                break

    input("\nTekan Enter...")


def _edit_record():
    """Edit service_status atau data record."""
    record_id = input_text("ID record yang akan diedit")
    try:
        rid = int(record_id)
    except ValueError:
        print_error("ID harus angka")
        return

    field = input_text("Field (nama/no_hp/device_model/imei/keluhan/service_status/teknisi)")
    value = input_text(f"Nilai baru untuk {field}")

    ok = update_check_in(rid, **{field: value})
    if ok:
        print_success(f"Record #{rid} berhasil diupdate")
    else:
        print_error(f"Gagal update record #{rid}")


def _delete_record():
    """Hapus record."""
    record_id = input_text("ID record yang akan dihapus")
    try:
        rid = int(record_id)
    except ValueError:
        print_error("ID harus angka")
        return

    if RICH_AVAILABLE:
        sure = Confirm.ask(f"Yakin hapus record #{rid}?")
    else:
        sure = input(f"Yakin hapus record #{rid}? (y/n): ").lower() == 'y'

    if not sure:
        return

    ok = delete_check_in(rid)
    if ok:
        print_success(f"Record #{rid} berhasil dihapus")
    else:
        print_error(f"Record #{rid} tidak ditemukan")


def menu_status():
    """Menu 4: Status Sistem & Database."""
    print_header("📊 STATUS SISTEM")

    # Cek environment
    print_info(f"Python: {sys.version.split()[0]}")
    print_info(f"Working Dir: {os.getcwd()}")

    # Cek ADB
    adb_ok = check_adb_installed()
    fb_ok = check_fastboot_installed()
    print_info(f"ADB: {'✅' if adb_ok else '❌'} Fastboot: {'✅' if fb_ok else '❌'}")

    # Cek database
    try:
        records = get_all_check_ins(limit=999999)
        print_success(f"Database: service_hp.db ✅ ({len(records)} total records)")
    except Exception as e:
        print_error(f"Database error: {e}")

    # Cek Rich
    if RICH_AVAILABLE:
        print_success("Rich library: ✅ (Tampilan warna-warni)")
    else:
        print_warning("Rich library: ❌ (Install: pip install rich)")

    # Cek direktori database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "service_hp.db")
    print_info(f"Database: {db_path} ({'✅ exists' if os.path.exists(db_path) else '❌ missing'})")

    input("\nTekan Enter untuk kembali...")


# ─── Menu Utama ───────────────────────────────────────────────────

def main():
    """Entry point untuk CLI aplikasi."""
    # Inisialisasi database
    try:
        init_database()
    except Exception as e:
        print_error(f"Gagal inisialisasi database: {e}")
        sys.exit(1)

    while True:
        show_splash()

        if RICH_AVAILABLE:
            console.print(Panel("""[bold cyan]MENU UTAMA[/bold cyan]

[1] 📱  Deteksi ADB & Fastboot — Scan perangkat + firmware links
[2] 📋  Smart Check-In & Diagnosis — Input pelanggan + ampere analysis
[3] 📜  Riwayat Check-In — Cari, edit, hapus data tersimpan
[4] 📊  Status Sistem — Cek lingkungan & database
[5] ❌  Keluar""", title="Pilih Menu", border_style="blue"))
            choice = Prompt.ask("Pilih", choices=["1", "2", "3", "4", "5"])
        else:
            print("""
MENU UTAMA:
  [1] 📱  Deteksi ADB & Fastboot
  [2] 📋  Smart Check-In & Diagnosis
  [3] 📜  Riwayat Check-In (cari/edit/hapus)
  [4] 📊  Status Sistem
  [5] ❌  Keluar
            """)
            choice = input("Pilih [1-5]: ").strip()

        if choice == "1":
            menu_adb_scan()
        elif choice == "2":
            menu_check_in()
        elif choice == "3":
            menu_history()
        elif choice == "4":
            menu_status()
        elif choice == "5":
            print_success("Terima kasih! Sampai jumpa.")
            break
        else:
            print_error("Pilihan tidak valid.")


if __name__ == "__main__":
    main()
