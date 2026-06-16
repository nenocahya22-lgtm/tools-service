# Smart Service HP Workstation

**AI-Powered Cross-Platform Service Management System**

Sistem manajemen service HP berbasis AI — dari check-in, diagnosis, flashing, hingga laporan keuangan. Berjalan di Windows/Linux/macOS.

## Fitur Utama

| Modul | Deskripsi |
|-------|-----------|
| **Dead Phone Scanner** | Deteksi device mati total via USB (EDL 9008, Fastboot, DFU, Preloader) |
| **Deep ADB Scanner** | Scan detail: model, chipset, CPU, memori, partisi, bootloader, MAC address |
| **iOS Scanner** | Scan iPhone/iPad: UDID, iOS version, activation lock, battery health |
| **Check-In & Diagnosis** | Input pelanggan + gejala → AI diagnosis otomatis berbasis aturan ampere |
| **Ampere & Baterai** | Ukur konsumsi arus via ADB atau USB Power Meter (FNIRSI, TC66C) |
| **Flashing Assistant** | Verifikasi firmware, flash partisi via Fastboot, safety checklist |
| **Pre-Flashing Security** | Cek FRP, ARB, bootloader, FRP lock, Find My iPhone |
| **Hardware Diagnosis** | Deteksi 5 kerusakan hardware via Windows: IC Charger, eMMC, RAM, Wi-Fi, Baseband |
| **Inventory & Financial** | Manajemen stok sparepart, laporan keuangan, AI narrative |
| **Emergency Recovery** | Panduan step-by-step untuk unbrick (EDL, MTK Preloader, DFU, Bootloop) |
| **Auto Backup & Restore** | Backup partisi (persist, efs, nvram, modem, boot, recovery) |
| **Network Scan** | Deteksi PC/laptop dalam jaringan lokal |

## Arsitektur

```
┌────────────────────────────────────┐
│         CLIENT LAYER               │
│  Streamlit Web UI / CLI (Rich)     │
└──────────┬─────────────────────────┘
           │
┌──────────▼─────────────────────────┐
│         CORE ENGINE                │
│  ┌──────────┐  ┌────────────────┐  │
│  │ ADB/FB   │  │ AI Diagnosis   │  │
│  │ Handler  │  │ Engine (Rules) │  │
│  └──────────┘  └────────────────┘  │
│  ┌──────────┐  ┌────────────────┐  │
│  │ Database │  │ Models/Schema  │  │
│  │ (SQLite) │  │ (Dataclasses)  │  │
│  └──────────┘  └────────────────┘  │
└──────────┬─────────────────────────┘
           │
┌──────────▼─────────────────────────┐
│         DATA LAYER                 │
│  service_hp.db (SQLite + WAL)      │
│  docs/arsitektur (blueprint)       │
└────────────────────────────────────┘
```

**Blueprint Arsitektur Enterprise** — Lihat `docs/ERP-Service-HP-Tech-Docs.md` untuk dokumentasi lengkap: PRD, SRS, System Design, UI/UX Design System, AI Agents, dan roadmap pengembangan.

## Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Frontend | Streamlit, Plotly |
| CLI | Python, Rich |
| Database | SQLite3 (WAL mode) |
| Device Communication | ADB, Fastboot (subprocess) |
| iOS | libimobiledevice |
| Power Meter | PySerial (FNIRSI, TC66C, ATORCH) |
| Diagnosis | Rule-Based AI Engine |

## Struktur Project

```
smart-service-hp/
├── app.py                   # Streamlit Web UI (full version)
├── main.py                  # Entry point CLI + Web
├── requirements.txt         # Python dependencies
├── service_hp.db            # Database SQLite
├── README.md                # Dokumentasi ini
├── .gitignore
├── docs/
│   └── ERP-Service-HP-Tech-Docs.md   # Blueprint enterprise
├── core/
│   ├── __init__.py
│   ├── adb_handler.py       # ADB/Fastboot device communication
│   ├── database.py          # Database operations
│   ├── diagnosis_engine.py  # Rule-based AI diagnosis
│   └── models.py            # Data classes
├── cli/
│   ├── __init__.py
│   └── interface.py         # Rich CLI interface
└── streamlit_app/
    ├── __init__.py
    └── app.py               # Legacy redirect
```

## Cara Install & Jalankan

### 1. Install Dependencies

```bash
cd smart-service-hp
pip install -r requirements.txt
```

### 2. Install Tools Eksternal

| Tool | Install |
|------|---------|
| **ADB & Fastboot** | `scoop install adb` (Windows), `apt install android-tools-adb android-tools-fastboot` (Linux), atau download [Platform Tools](https://developer.android.com/studio/releases/platform-tools) |
| **libimobiledevice** (iOS) | `brew install libimobiledevice` (macOS) atau download dari [imobiledevice-net](https://github.com/libimobiledevice-win32/imobiledevice-net/releases) (Windows) |

### 3. Jalankan

**Mode Web (Streamlit):**
```bash
python main.py --web
# atau langsung:
streamlit run app.py
```

**Mode CLI:**
```bash
python main.py                             # CLI interaktif
python main.py --checkin -n "Budi" -m "Redmi Note 13" -s "Mati total" -a 0.02
python main.py --adb-scan                  # Scan ADB langsung
```

### 4. Buka Browser

```
http://localhost:8501
```

## Development Roadmap (dari Blueprint)

| Fase | Target |
|------|--------|
| **Fase 1 (Saat Ini)** | Multi-outlet, tiket service, inventory FIFO, POS, AI diagnosis, AI repair copilot, predictive inventory, executive dashboard, WhatsApp notifikasi |
| **Post-MVP** | Marketplace HP bekas, e-commerce, HR & Payroll, full accounting |

Lihat `docs/ERP-Service-HP-Tech-Docs.md` untuk detail roadmap dan spesifikasi teknis.

## Lisensi

Proprietary — Internal Use
