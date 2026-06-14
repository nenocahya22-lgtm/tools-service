"""
main.py — Entry point utama untuk Smart Service HP Workstation.

Mode CLI:   python main.py
Mode Web:   python main.py --web   (buka app.py versi lengkap)
Atau:       python main.py --web

Aplikasi berjalan di Windows/Linux/macOS.
"""

import sys
import os
import subprocess
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="🔧 Smart Service HP Workstation — Sistem Diagnosa & Manajemen Service HP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python main.py              # Mode CLI (Rich jika terinstall)
  python main.py --web        # Mode Streamlit (web)
  python main.py --checkin -n "Budi" -m "Redmi Note 13" -s "Mati total" -a 0.02
  python main.py --adb-scan   # Langsung scan ADB
        """
    )

    parser.add_argument("--web", action="store_true", help="Jalankan dalam mode Streamlit web UI")
    parser.add_argument("--checkin", action="store_true", help="Mode check-in cepat via CLI argument")
    parser.add_argument("-n", "--name", default="Walk-in Customer", help="Nama pelanggan")
    parser.add_argument("-m", "--model", default="Unknown", help="Model HP")
    parser.add_argument("-s", "--symptoms", default="", help="Gejala kerusakan")
    parser.add_argument("-a", "--ampere", type=float, default=0.0, help="Arus dalam Ampere")
    parser.add_argument("--adb-scan", action="store_true", help="Langsung scan perangkat ADB")

    args = parser.parse_args()

    # Mode Web (Streamlit) — jalankan app.py VERSI LENGKAP
    if args.web:
        try:
            import streamlit
        except ImportError:
            print("Streamlit belum terinstall. Install: pip install streamlit")
            sys.exit(1)

        print("🚀 Menjalankan Smart Service HP Workstation (Full Version)...")
        subprocess.run(["streamlit", "run", os.path.join(os.path.dirname(__file__), "app.py")])
        return

    # Mode ADB scan langsung
    if args.adb_scan:
        from core.adb_handler import scan_device, generate_firmware_links
        from core.database import init_database
        init_database()

        device = scan_device()
        print(f"\n📱 ADB SCAN RESULT")
        print("=" * 40)
        if device.adb_connected:
            print(f"✅ ADB Connected: {device.serial}")
            print(f"   Model: {device.model}")
            print(f"   Android: {device.android_version}")
            print(f"   Bootloader: {device.bootloader_status}")
            print(f"   Battery: {device.battery_level}%")
        elif device.fastboot_connected:
            print(f"✅ Fastboot: {device.serial}")
            print(f"   Bootloader: {device.bootloader_status}")
        else:
            print("❌ No device detected")

        if device.model:
            print(f"\n📥 Firmware links for {device.model}:")
            links = generate_firmware_links(device.model)
            for url, src in zip(links.search_urls, links.sources):
                print(f"   • [{src}] {url}")
        return

    # Mode check-in cepat via CLI
    if args.checkin:
        from core.models import CheckInRecord
        from core.database import init_database, save_check_in
        from core.diagnosis_engine import diagnose

        init_database()

        record = CheckInRecord(
            customer_name=args.name,
            device_model=args.model,
            symptoms=args.symptoms,
            ampere_reading=args.ampere,
        )

        print("🔍 Mendiagnosis...")
        result = diagnose(record)
        record_id = save_check_in(result)

        print(f"\n✅ Diagnosis selesai! ID: #{record_id}")
        print(f"   Severity: {result.severity.upper()}")
        print(f"   Diagnosis: {result.diagnosis_result[:100]}...")
        print(f"   Rekomendasi: {result.recommendation[:100]}...")
        return

    # Default: Mode CLI interaktif
    from cli.interface import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
