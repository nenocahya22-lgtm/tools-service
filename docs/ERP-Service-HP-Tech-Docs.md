
# Sistem ERP/SaaS Manajemen Service HP (Software & Hardware) — Enterprise Blueprint

> **Dokumen Teknis Komprehensif**
> Role: Software Architect, Senior Business Analyst, UI/UX Designer
> Tech Stack: Python (FastAPI) + Go (High-Performance Services) + Next.js + PostgreSQL 16 + Redis + RabbitMQ + LangChain/LangGraph

---

## Daftar Isi
1. [PRODUCT REQUIREMENT DOCUMENT (PRD)](#1-product-requirement-document-prd)
2. [SOFTWARE REQUIREMENTS SPECIFICATION (SRS)](#2-software-requirements-specification-srs)
3. [SYSTEM ARCHITECTURE & SYSTEM DESIGN (SSD)](#3-system-architecture--system-design-ssd)
4. [PANDUAN UI/UX DESIGN (MINIMALIST LUXURY)](#4-panduan-uiux-design-minimalist-luxury)
5. [FITUR & MENU CERDAS (AI AGENTS)](#5-fitur--menu-cerdas-ai-agents)
6. [TASK BREAKDOWN — ROADMAP](#6-task-breakdown--roadmap)

---

# 1. PRODUCT REQUIREMENT DOCUMENT (PRD)

## 1.1 Vision & Objectives

**Vision:** Menjadi sistem operasi standar industri untuk ribuan toko service HP di Indonesia — bukan sekadar pencatat transaksi, tetapi *co-pilot cerdas* yang mendiagnosis, memprediksi, dan mengoptimalkan setiap aspek bisnis.

**Objectives:**
| Objektif | Metrik Keberhasilan |
|---|---|
| Diagnosis kerusakan otomatis berbasis gejala | Akurasi rekomendasi >85% dalam 3 bulan pertama |
| Prediksi stok sparepart berbasis tren | Mengurangi dead stock 30%, zero out-of-stock untuk top-20 sparepart |
| Efisiensi waktu teknisi | Rata-rata turnaround time turun 25% |
| Transparansi biaya ke pelanggan | 100% estimasi biaya diberikan sebelum perbaikan disetujui |
| Insight finansial otomatis | Laporan naratif tersedia <5 detik setelah bulan tutup |

## 1.2 User Persona & Journey

### A. Pelanggan (End Customer)
- **Demografi:** 18–45 tahun, pengguna smartphone, tidak paham teknis hardware.
- **Pain Point:** Tidak tahu estimasi biaya, tidak bisa tracking progress, khawatir ditipu.
- **Journey:**
  1. Datang ke toko → Check-in oleh admin → Terima tiket (via WhatsApp/QR)
  2. Terima notifikasi WA: "HP Anda terdiagnosis: LCD retak (Rp350rb). Setujui? [Ya/Tidak]"
  3. Selama proses: Dapat update otomatis tiap perubahan status
  4. Selesai: Dapat notifikasi + invoice digital → Bayar via QRIS/transfer

### B. Teknisi (Technician)
- **Demografi:** Lulusan SMK/sertifikasi, usia 20–40 tahun.
- **Pain Point:** Tidak punya referensi skema, sering salah diagnosa, tidak teratur catat log.
- **Journey:**
  1. Buka dashboard → Lihat antrian task yang sudah didiagnosis AI
  2. Klik task → AI Copilot menampilkan kemungkinan kerusakan, skema (jika ada), dan step-by-step
  3. Catat log perbaikan (hardware/software) → Sistem validasi otomatis
  4. Jika part tidak cocok → AI beri warning incompatible part

### C. Owner / Admin
- **Demografi:** Pemilik toko (1–10 cabang), usia 30–55 tahun.
- **Pain Point:** Susah pantau performa, bocor stok, tidak punya laporan otomatis.
- **Journey:**
  1. Buka dashboard finansial → Lihat ringkasan real-time: omset, margin, profit per teknisi
  2. AI Insight muncul: "LCD iPhone 11 naik 300% — sarankan restok 50 unit"
  3. Cek inventory → Lihat slow-moving items → Buat promo langsung dari sistem
  4. Review laporan bulanan naratif dari AI

## 1.3 Scope & Exclusions

**In Scope (Fase 1):**
- Multi-outlet (satu database, filter by branch)
- Manajemen tiket service (check-in → diagnose → repair → QA → handover)
- Inventory sparepart dengan FIFO + auto-reorder
- POS/Kasir terintegrasi dengan multi-payment
- AI Diagnosis Engine, AI Repair Copilot, AI Flashing Assistant
- Predictive Inventory Analytics
- Executive Financial Dashboard + AI Narrative
- WhatsApp notification integration

**Exclusions (Post-MVP):**
- Marketplace jual-beli HP bekas
- E-commerce toko online
- Modul HR & Payroll
- Modul Akuntansi full (hanya laporan laba-rugi dasar)

---

# 2. SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## 2.1 Functional Requirements

### FR-01: Autentikasi & RBAC
| ID | Deskripsi |
|---|---|
| FR-01-01 | Login multi-role: Super Admin, Owner, Admin Kasir, Teknisi |
| FR-01-02 | RBAC: setiap role hanya bisa mengakses menu sesuai izin |
| FR-01-03 | Session management via JWT (access + refresh token) |
| FR-01-04 | Multi-tenant: satu instance melayani banyak toko (diisolasi per `branch_id`) |

### FR-02: Smart Check-In & Ticketing
| ID | Deskripsi |
|---|---|
| FR-02-01 | Admin input data pelanggan & device (IMEI, model, keluhan) |
| FR-02-02 | Auto Device Lookup via IMEI → deteksi otomatis brand, model, tahun rilis |
| FR-02-03 | AI Diagnosis: gejala → analisis kerusakan → estimasi biaya & waktu |
| FR-02-04 | Generate tiket dengan QR code + kirim link tracking ke WA |
| FR-02-05 | Status workflow: `pending` → `diagnosed` → `approved` → `in_progress` → `qa_check` → `completed` → `handed_over` |

### FR-03: Inventaris Sparepart
| ID | Deskripsi |
|---|---|
| FR-03-01 | CRUD sparepart dengan SKU unik, kategori, kompatibilitas device |
| FR-03-02 | Metode FIFO: barang masuk pertama adalah barang keluar pertama (cost basis) |
| FR-03-03 | Auto Reorder Point: jika stok ≤ threshold, sistem catat sebagai perlu restock |
| FR-03-04 | Stock mutation log: setiap pergerakan stok tercatat (masuk, keluar, opname, adjustment) |
| FR-03-05 | Multi-warehouse: tiap cabang punya stok sendiri |

### FR-04: Hardware Repair Copilot
| ID | Deskripsi |
|---|---|
| FR-04-01 | Menampilkan panduan perbaikan step-by-step berdasarkan model device |
| FR-04-02 | Teknisi bisa menandai setiap langkah selesai (checklist) |
| FR-04-03 | Validasi kompatibilitas: sparepart yang dipilih harus cocok dengan model device |
| FR-04-04 | Log gambar: teknisi bisa upload foto kerusakan sebelum & sesudah |

### FR-05: Software Flashing & Unlock Assistant
| ID | Deskripsi |
|---|---|
| FR-05-01 | Deteksi versi firmware terbaru yang stabil untuk device tertentu |
| FR-05-02 | Auto-Identify Link Download: tampilkan tautan file Firmware/ROM resmi, Recovery, Scatter/DA file, dan Fastboot Tool berdasarkan model HP dan chipset (MediaTek/Snapdragon/Exynos) |
| FR-05-03 | Cek status bootloader (locked/unlocked) dari input teknisi |
| FR-05-04 | Safe-Guard ARB (Anti-Rollback): deteksi level ARB perangkat, beri peringatan merah jika downgrade menyebabkan hardbrick permanen |
| FR-05-05 | Peringatan risiko hardbrick berdasarkan chipset & firmware version |
| FR-05-06 | Testpoint Guide: tampilkan gambar/diagram titik testpoint untuk masuk mode EDL (Emergency Download 9008) jika HP mati total |
| FR-05-07 | Pre-Flashing Checklist: pastikan akun Google (FRP), Mi Cloud, iCloud sudah di-logout sebelum flashing |
| FR-05-08 | Simpan log flashing: versi firmware, status, error code |

### FR-06: POS & Kasir
| ID | Deskripsi |
|---|---|
| FR-06-01 | Buat invoice dari tiket service (biaya jasa + sparepart) |
| FR-06-02 | Multi-payment: Tunai, QRIS, Transfer, Debit/Kredit |
| FR-06-03 | Cetak struk / kirim invoice digital via WA |
| FR-06-04 | History transaksi lengkap dengan filter tanggal, teknisi, cabang |

### FR-07: Predictive Inventory
| ID | Deskripsi |
|---|---|
| FR-07-01 | Analisis tren 90 hari untuk setiap sparepart |
| FR-07-02 | Deteksi dead stock: sparepart tidak terjual >60 hari |
| FR-07-03 | Rekomendasi restock otomatis dengan kuantitas yang dihitung dari tren |
| FR-07-04 | Rekomendasi promo untuk slow-moving items |

### FR-08: Executive Dashboard & AI Narrative
| ID | Deskripsi |
|---|---|
| FR-08-01 | Grafik omset harian/mingguan/bulanan (Plotly interaktif) |
| FR-08-02 | Profit margin per teknisi, per kategori service, per cabang |
| FR-08-03 | AI Narrative: teks insight otomatis setiap akhir bulan |
| FR-08-04 | Deteksi anomali: pengeluaran tidak wajar, stok anjlok drastis |

### FR-09: Notifikasi
| ID | Deskripsi |
|---|---|
| FR-09-01 | Kirim notifikasi WA: status tiket, estimasi biaya, butuh persetujuan |
| FR-09-02 | Notifikasi in-app: task baru untuk teknisi, reorder alert untuk admin |
| FR-09-03 | Konfirmasi via WA: pelanggan bisa reply "Ya" untuk setujui biaya |

### FR-10: Hardware Diagnostic — Ampere & Battery Health Analysis
| ID | Deskripsi |
|---|---|
| FR-10-01 | Input manual konsumsi arus (Ampere) dari USB Analyzer / Power Supply digital saat check-in |
| FR-10-02 | AI diagnosis berdasarkan angka ampere: 0.01–0.04A (soft brick/IC eMMC) vs >1A (short VCC_MAIN/VBAT) |
| FR-10-03 | Integrasi ADB (Android Debug Bridge) untuk menarik data baterai: kapasitas aktual (mAh), health (%), cycle count |
| FR-10-04 | Masukkan hasil diagnosis ampere & baterai otomatis ke dalam catatan service pelanggan |
| FR-10-05 | History battery health per perangkat untuk deteksi degradasi |

### FR-11: Pre-Flashing Security & FRP Checker
| ID | Deskripsi |
|---|---|
| FR-11-01 | Checklist sebelum flashing: pastikan Google Account (FRP), Mi Cloud, iCloud, Samsung Account sudah di-logout |
| FR-11-02 | Teknisi wajib menandai setiap item checklist sebelum flashing dimulai |
| FR-11-03 | Log hasil flashing: sukses/gagal, versi firmware final, durasi, error message |
| FR-11-04 | Statistik keberhasilan flashing per teknisi, per model device, per tipe firmware |

## 2.2 Non-Functional Requirements

| Kategori | Requirement | Target |
|---|---|---|
| **Security** | Enkripsi data at-rest (AES-256) & in-transit (TLS 1.3) | Seluruh data pelanggan & transaksi |
| **Security** | RBAC di level API (middleware scope check) | Setiap endpoint terproteksi |
| **Security** | Audit log: setiap perubahan status tiket, stok, dan transaksi tercatat | 100% mutation logged |
| **Security** | Hash password dengan bcrypt (cost factor 12) | Tidak ada plaintext |
| **Performance** | Response time API inventory search | <500ms (P99 <2s) |
| **Performance** | Page load dashboard | <2s (termasuk render grafik) |
| **Performance** | AI Diagnosis inference | <5s per request |
| **Availability** | Uptime | 99.5% (kecuali maintenance terjadwal) |
| **Scalability** | Arsitektur horizontal: API server stateless → scaling via replica | Support 10x traffic spike |
| **Scalability** | Database read replica untuk laporan | Query berat tidak ganggu transaksi |
| **Maintainability** | Modular monolith → siap dipecah ke microservices | Setiap modul dalam package terpisah |
| **Portability** | 100% containerized (Docker) | Satu command deploy di VPS/managed k8s |

---

# 3. SYSTEM ARCHITECTURE & SYSTEM DESIGN (SSD)

## 3.1 Arsitektur High-Level

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                                   │
│  [Next.js Web App]  [PWA Mobile]  [WhatsApp (via Gateway)]           │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ HTTPS (TLS 1.3)
┌────────────────────────────▼─────────────────────────────────────────┐
│                        API GATEWAY (Kong / NGINX)                     │
│                   Rate Limiting, Auth, Routing, Logging               │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                   ▼
┌──────────────────┐ ┌───────────────┐ ┌──────────────────┐
│  Service Layer   │ │  AI Engine    │ │  Event Bus       │
│  (Python FastAPI)│ │  (LangGraph)  │ │  (RabbitMQ)      │
│                  │ │               │ │                  │
│ • Auth Service   │ │ • Diagnosis   │ │ • Ticket Events  │
│ • Ticket Service │ │ • Copilot     │ │ • Stock Events   │
│ • Inventory Svc  │ │ • Inventory   │ │ • Notification   │
│ • POS Service    │ │   Predictor   │ │   Events         │
│ • Analytics Svc  │ │ • Finance AI  │ │                  │
│ • Notification   │ │ • Flashing    │ │                  │
│   Service        │ │   Assistant   │ │                  │
└──────┬───────────┘ └──────┬────────┘ └──────┬───────────┘
       │                    │                  │
       └────────────────────┼──────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│                        DATA LAYER                                    │
│  ┌──────────┐  ┌────────┐  ┌───────────┐  ┌──────────────────────┐  │
│  │PostgreSQL│  │ Redis  │  │Minio/S3   │  │TimescaleDB (Opsional)│  │
│  │(Primary) │  │(Cache) │  │(Image/FW) │  │(Time-series metrik)  │  │
│  └──────────┘  └────────┘  └───────────┘  └──────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## 3.2 Database Schema (PostgreSQL 16)

### Tabel-tabel Inti

#### `users` — Semua pengguna sistem
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       UUID NOT NULL REFERENCES branches(id),
    role            VARCHAR(20) NOT NULL CHECK (role IN ('super_admin','owner','admin','teknisi')),
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    phone           VARCHAR(20),
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_branch ON users(branch_id);
CREATE INDEX idx_users_role ON users(role);
```

#### `branches` — Multi-outlet / cabang
```sql
CREATE TABLE branches (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    address     TEXT,
    phone       VARCHAR(20),
    is_active   BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

#### `customers` — Data pelanggan
```sql
CREATE TABLE customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    phone           VARCHAR(20) NOT NULL,
    email           VARCHAR(255),
    address         TEXT,
    total_visits    INT DEFAULT 1,
    last_visit      TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_customers_phone ON customers(phone);
```

#### `devices` — Perangkat HP yang terdaftar
```sql
CREATE TABLE devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    imei            VARCHAR(15),  -- nullable (bisa tidak terbaca)
    brand           VARCHAR(50) NOT NULL,
    model           VARCHAR(100) NOT NULL,
    storage         VARCHAR(10),  -- 64/128/256 GB
    color           VARCHAR(30),
    os_version      VARCHAR(30),  -- iOS 17.4 / Android 14
    condition_note  TEXT,          -- kondisi fisik saat check-in
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_devices_imei ON devices(imei);
CREATE INDEX idx_devices_brand_model ON devices(brand, model);
```

#### `service_tickets` — Tiket service (core table)
```sql
CREATE TABLE service_tickets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_number       VARCHAR(20) UNIQUE NOT NULL,  -- format: SRV/YYYYMMDD/XXXX
    branch_id           UUID NOT NULL REFERENCES branches(id),
    customer_id         UUID NOT NULL REFERENCES customers(id),
    device_id           UUID NOT NULL REFERENCES devices(id),
    teknisi_id          UUID REFERENCES users(id),
    complaint           TEXT NOT NULL,                -- keluhan pelanggan mentah
    ai_diagnosis        JSONB,                       -- hasil diagnosis AI
    diagnosis_summary   TEXT,                         -- ringkasan untuk dikirim ke WA
    estimated_cost      NUMERIC(12,2),
    estimated_days      INT,
    customer_approved   BOOLEAN,                     -- apakah pelanggan setuju estimasi
    status              VARCHAR(20) DEFAULT 'pending'
                        CHECK (status IN ('pending','diagnosed','approved',
                                          'in_progress','qa_check','completed',
                                          'handed_over','cancelled')),
    total_cost          NUMERIC(12,2),               -- total biaya final
    qa_note             TEXT,
    completed_at        TIMESTAMPTZ,
    handed_over_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_tickets_branch ON service_tickets(branch_id);
CREATE INDEX idx_tickets_status ON service_tickets(status);
CREATE INDEX idx_tickets_teknisi ON service_tickets(teknisi_id);
CREATE INDEX idx_tickets_created ON service_tickets(created_at DESC);
```

#### `ticket_logs` — Audit log tiap perubahan status tiket
```sql
CREATE TABLE ticket_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id   UUID NOT NULL REFERENCES service_tickets(id) ON DELETE CASCADE,
    status_from VARCHAR(20),
    status_to   VARCHAR(20) NOT NULL,
    note        TEXT,
    changed_by  UUID NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ticket_logs_ticket ON ticket_logs(ticket_id);
```

#### `ticket_repair_details` — Detail perbaikan dari teknisi
```sql
CREATE TABLE ticket_repair_details (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id       UUID NOT NULL REFERENCES service_tickets(id) ON DELETE CASCADE,
    repair_type     VARCHAR(20) NOT NULL CHECK (repair_type IN ('hardware','software')),
    description     TEXT NOT NULL,
    sparepart_id    UUID REFERENCES spareparts(id),
    cost            NUMERIC(12,2),
    is_warranty     BOOLEAN DEFAULT false,
    teknisi_note    TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### `spareparts` — Master sparepart
```sql
CREATE TABLE spareparts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sku             VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(50) NOT NULL CHECK (category IN ('lcd','battery','charging_port',
                                'ic_power','flex_cable','camera','speaker','mic',
                                'button','housing','software','other')),
    brand           VARCHAR(50),
    compatible_models TEXT[] NOT NULL,  -- array model, mis: {"iPhone 11","iPhone 11 Pro"}
    purchase_price  NUMERIC(12,2) NOT NULL,
    selling_price   NUMERIC(12,2) NOT NULL,
    unit            VARCHAR(20) DEFAULT 'pcs',
    min_stock       INT DEFAULT 5,     -- threshold auto-reorder
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_spareparts_category ON spareparts(category);
CREATE INDEX idx_spareparts_sku ON spareparts(sku);
```

#### `inventory` — Stok sparepart per cabang (FIFO)
```sql
CREATE TABLE inventory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       UUID NOT NULL REFERENCES branches(id),
    sparepart_id    UUID NOT NULL REFERENCES spareparts(id),
    quantity        INT NOT NULL DEFAULT 0,
    batch_price     NUMERIC(12,2) NOT NULL,  -- harga beli per batch (FIFO)
    received_at     TIMESTAMPTZ NOT NULL,    -- tanggal masuk (untuk urutan FIFO)
    expired_at      TIMESTAMPTZ,             -- untuk part yang punya masa simpan
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_inventory_branch ON inventory(branch_id);
CREATE INDEX idx_inventory_sparepart ON inventory(sparepart_id);
-- Untuk FIFO: ambil batch paling lama yang masih punya stok
CREATE INDEX idx_inventory_fifo ON inventory(branch_id, sparepart_id, received_at);
```

#### `stock_mutations` — Log pergerakan stok
```sql
CREATE TABLE stock_mutations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       UUID NOT NULL REFERENCES branches(id),
    sparepart_id    UUID NOT NULL REFERENCES spareparts(id),
    type            VARCHAR(20) NOT NULL CHECK (type IN ('in','out','adjustment','opname')),
    quantity        INT NOT NULL,
    reference_type  VARCHAR(30),     -- 'purchase_order', 'service_ticket', 'opname'
    reference_id    UUID,            -- ID dari dokumen referensi
    note            TEXT,
    created_by      UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_stock_mutations_sparepart ON stock_mutations(sparepart_id);
CREATE INDEX idx_stock_mutations_created ON stock_mutations(created_at DESC);
```

#### `transactions` — Transaksi POS
```sql
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       UUID NOT NULL REFERENCES branches(id),
    ticket_id       UUID REFERENCES service_tickets(id),
    customer_id     UUID NOT NULL REFERENCES customers(id),
    invoice_number  VARCHAR(30) UNIQUE NOT NULL,
    subtotal        NUMERIC(12,2) NOT NULL,
    discount        NUMERIC(12,2) DEFAULT 0,
    tax             NUMERIC(12,2) DEFAULT 0,
    total           NUMERIC(12,2) NOT NULL,
    payment_method  VARCHAR(30) NOT NULL CHECK (payment_method IN ('cash','qris','transfer','debit','credit')),
    payment_status  VARCHAR(20) DEFAULT 'paid' CHECK (payment_status IN ('paid','partial','pending','refunded')),
    paid_at         TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_transactions_branch ON transactions(branch_id);
CREATE INDEX idx_transactions_created ON transactions(created_at DESC);
```

#### `transaction_items` — Line items transaksi
```sql
CREATE TABLE transaction_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    item_type       VARCHAR(20) CHECK (item_type IN ('service','sparepart')),
    description     TEXT NOT NULL,
    quantity        INT DEFAULT 1,
    unit_price      NUMERIC(12,2) NOT NULL,
    total_price     NUMERIC(12,2) NOT NULL,
    sparepart_id    UUID REFERENCES spareparts(id)
);
```

#### `ai_logs` — Log semua inferensi AI (audit & improvement)
```sql
CREATE TABLE ai_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type      VARCHAR(30) NOT NULL CHECK (agent_type IN ('diagnosis','copilot','flashing',
                                'inventory_predictive','finance_analytics')),
    input_data      JSONB NOT NULL,
    output_data     JSONB NOT NULL,
    confidence      NUMERIC(5,4),     -- 0.0000 - 1.0000
    latency_ms      INT,
    feedback        JSONB,            -- feedback teknisi untuk improvement
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

#### `ai_diagnosis_knowledge_base` — Basis pengetahuan diagnosis
```sql
CREATE TABLE ai_diagnosis_knowledge_base (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model    VARCHAR(100) NOT NULL,
    symptom_keywords TEXT[] NOT NULL,   -- array kata kunci gejala
    diagnosis       TEXT NOT NULL,      -- kemungkinan kerusakan
    probability     NUMERIC(5,4),      -- persentase probabilitas
    recommended_action TEXT,           -- tindakan yang disarankan
    source          VARCHAR(30) DEFAULT 'ai_generated' CHECK (source IN ('ai_generated','teknisi_input','verified')),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_kb_model ON ai_diagnosis_knowledge_base(device_model);
```

#### `device_firmware_db` — Database firmware
```sql
CREATE TABLE device_firmware_db (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model    VARCHAR(100) NOT NULL,
    firmware_version VARCHAR(50) NOT NULL,
    release_date    DATE,
    is_stable       BOOLEAN DEFAULT true,
    risk_level      VARCHAR(20) CHECK (risk_level IN ('low','medium','high')),
    risk_note       TEXT,
    download_url    TEXT,
    md5_hash        VARCHAR(32),
    file_size_mb    NUMERIC(8,2),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_firmware_model ON device_firmware_db(device_model);
```

#### `device_chipset_info` — Informasi chipset per model (untuk flashing & UBL)
```sql
CREATE TABLE device_chipset_info (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model    VARCHAR(100) NOT NULL,
    chipset_brand   VARCHAR(30) NOT NULL CHECK (chipset_brand IN ('qualcomm','mediatek','exynos','apple','huawei_kirin','google_tensor','unisoc')),
    chipset_model   VARCHAR(100),            -- misal: Snapdragon 685, Dimensity 1080
    flash_tool      VARCHAR(50),             -- misal: SP Flash Tool, Odin, EDL Tool, 3uTools
    scatter_file    VARCHAR(200),            -- nama file scatter/DA default
    edl_method      VARCHAR(50),             -- misal: testpoint, vol_up+vol_down, short_pin
    bootloader_unlock_method TEXT,           -- cara unlock bootloader
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_chipset_model ON device_chipset_info(device_model);
CREATE INDEX idx_chipset_brand ON device_chipset_info(chipset_brand);
```

#### `device_testpoints` — Diagram testpoint untuk EDL / Download Mode
```sql
CREATE TABLE device_testpoints (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model    VARCHAR(100) NOT NULL,
    chipset_brand   VARCHAR(30) NOT NULL,
    mode_type       VARCHAR(30) NOT NULL CHECK (mode_type IN ('edl_9008','download_mode','dfu_mode','recovery')),
    description     TEXT NOT NULL,            -- deskripsi langkah menemukan testpoint
    image_url       TEXT,                     -- URL gambar diagram testpoint (disimpan di Minio/S3)
    image_annotation JSONB,                   -- koordinat titik testpoint di gambar (x,y) untuk overlay
    video_url       TEXT,                     -- URL video tutorial (opsional)
    difficulty      VARCHAR(10) CHECK (difficulty IN ('easy','medium','hard')),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_testpoints_model ON device_testpoints(device_model);
CREATE INDEX idx_testpoints_mode ON device_testpoints(mode_type);
```

#### `device_arb_info` — Anti-Rollback protection levels
```sql
CREATE TABLE device_arb_info (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model        VARCHAR(100) NOT NULL,
    chipset_brand       VARCHAR(30) NOT NULL,
    firmware_version    VARCHAR(50) NOT NULL,
    arb_level           INT NOT NULL CHECK (arb_level BETWEEN 0 AND 10),
    min_allowed_version VARCHAR(50),          -- versi minimum yang bisa di-downgrade
    is_downgrade_safe   BOOLEAN DEFAULT false,
    risk_note           TEXT,                 -- penjelasan risiko
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(device_model, firmware_version)
);

CREATE INDEX idx_arb_model ON device_arb_info(device_model);
```

#### `device_firmware_links` — Tautan download firmware terverifikasi (crowdsourced + admin-verified)
```sql
CREATE TABLE device_firmware_links (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model        VARCHAR(100) NOT NULL,
    firmware_version    VARCHAR(50) NOT NULL,
    file_type           VARCHAR(30) NOT NULL CHECK (file_type IN ('firmware_rom','recovery','scatter_da','fastboot_tool','oem_unlock_tool','patch_file')),
    source              VARCHAR(100),         -- misal: miui.com, sammobile, 4pda, official
    download_url        TEXT NOT NULL,
    mirror_url          TEXT,                 -- mirror alternatif
    md5_hash            VARCHAR(32),
    file_size_mb        NUMERIC(8,2),
    is_verified         BOOLEAN DEFAULT false,
    verified_by         UUID REFERENCES users(id),
    download_count      INT DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_fwlinks_model ON device_firmware_links(device_model);
CREATE INDEX idx_fwlinks_type ON device_firmware_links(file_type);
```

#### `flashing_logs` — Log detail proses flashing
```sql
CREATE TABLE flashing_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id           UUID NOT NULL REFERENCES service_tickets(id) ON DELETE CASCADE,
    teknisi_id          UUID NOT NULL REFERENCES users(id),
    device_model        VARCHAR(100) NOT NULL,
    firmware_before     VARCHAR(50),
    firmware_after      VARCHAR(50),
    flash_tool_used     VARCHAR(50),
    bootloader_status   VARCHAR(20) CHECK (bootloader_status IN ('locked','unlocked','unknown')),
    arb_level           INT,
    result              VARCHAR(20) NOT NULL CHECK (result IN ('success','failed','partial','hardbricked')),
    error_code          VARCHAR(50),
    error_message       TEXT,
    duration_minutes    INT,
    teknisi_note        TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_flog_ticket ON flashing_logs(ticket_id);
CREATE INDEX idx_flog_teknisi ON flashing_logs(teknisi_id);
CREATE INDEX idx_flog_result ON flashing_logs(result);
```

#### `pre_flashing_checklist` — Checklist sebelum flashing
```sql
CREATE TABLE pre_flashing_checklist (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id           UUID NOT NULL REFERENCES service_tickets(id) ON DELETE CASCADE,
    account_type        VARCHAR(30) NOT NULL CHECK (account_type IN ('google_frp','mi_cloud','icloud','samsung_account','huawei_id','oppo_account','vivo_account')),
    is_logged_out       BOOLEAN DEFAULT false,
    confirmed_by        UUID REFERENCES users(id),
    note                TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_pfc_ticket ON pre_flashing_checklist(ticket_id);
```

#### `battery_health_logs` — Data kesehatan baterai dari ADB
```sql
CREATE TABLE battery_health_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id           UUID NOT NULL REFERENCES service_tickets(id) ON DELETE CASCADE,
    device_id           UUID NOT NULL REFERENCES devices(id),
    current_capacity    NUMERIC(8,2),         -- mAh terukur sekarang
    design_capacity     NUMERIC(8,2),         -- mAh pabrik
    health_percent      NUMERIC(5,2),         -- (current / design) * 100
    cycle_count         INT,                  -- siklus charge
    voltage             NUMERIC(5,3),         -- voltase saat pengukuran
    temperature_celsius NUMERIC(5,1),
    adb_command_raw     TEXT,                 -- raw output dari ADB
    measured_by         UUID NOT NULL REFERENCES users(id),
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_battery_ticket ON battery_health_logs(ticket_id);
CREATE INDEX idx_battery_device ON battery_health_logs(device_id);
```

#### `ampere_diagnosis_rules` — Aturan diagnosis dari konsumsi arus (ampere)
```sql
CREATE TABLE ampere_diagnosis_rules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    min_ampere          NUMERIC(6,3) NOT NULL,
    max_ampere          NUMERIC(6,3) NOT NULL,
    condition_note      TEXT NOT NULL,         -- misal: "HP matot, tidak ditekan power"
    diagnosis           TEXT NOT NULL,         -- misal: "Short besar di jalur VCC_MAIN"
    severity            VARCHAR(10) CHECK (severity IN ('low','medium','high','critical')),
    recommended_action  TEXT,
    priority            INT DEFAULT 0,         -- higher = lebih diutamakan jika overlap range
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Seed data
INSERT INTO ampere_diagnosis_rules (min_ampere, max_ampere, condition_note, diagnosis, severity, recommended_action, priority) VALUES
(0.000, 0.005, 'HP matot, dicolokkan ke power supply', 'Kebocoran arus minimal / tidak ada sirkuit aktif — kemungkinan putus total di jalur BATT+ atau konektor baterai rusak', 'high', 'Periksa konektor baterai, ukur tegangan di diode mode pada jalur BATT+, jika OL berarti putus total', 10),
(0.010, 0.040, 'HP matot, dicolokkan ke power supply', 'Software Brick atau kerusakan IC eMMC/UFS/CPU — arus hanya cukup untuk RTC, tidak cukup untuk boot', 'medium', 'Coba masuk EDL/Download Mode. Jika tidak bisa, indikasi eMMC/UFS korup atau IC CPU short rendah', 9),
(0.050, 0.200, 'HP matot, dicolokkan ke power supply', 'Arus rendah — kemungkinan short parsial di jalur sinyal atau IC power supply tidak bekerja optimal', 'medium', 'Periksa tegangan keluaran PMIC/PMU, ukur di inductor sekitar PMIC', 8),
(0.200, 0.500, 'HP matot, dicolokkan ke power supply', 'Arus sedang — boot loop / short di jalur peripheral (LCD, camera, speaker)', 'low', 'Lepaskan satu persatu fleksibel peripheral, lihat apakah arus turun drastis', 7),
(0.500, 1.000, 'HP matot, dicolokkan ke power supply', 'Arus tinggi — kemungkinan short di komponen pemakaian daya sedang (PA, RF, WiFi IC)', 'medium', 'Thermal imaging atau sentuh komponen satu per satu untuk cari yang panas', 6),
(1.000, 9.999, 'HP matot, dicolokkan ke power supply tanpa tekan power', 'SHORT BESAR — arus tembus di jalur utama VCC_MAIN atau VBAT (kemungkinan IC Power, Capasitor bocor, atau Mosfet short)', 'critical', 'MATIKAN SEGERA power supply. Cari komponen panas dengan thermal cam atau alkohol test. Ukur resistansi VCC_MAIN ke GND', 10);
```

#### `device_repair_guides` — Step-by-step repair guides (untuk copilot + testpoint)
```sql
CREATE TABLE device_repair_guides (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model    VARCHAR(100) NOT NULL,
    guide_type      VARCHAR(30) NOT NULL CHECK (guide_type IN ('hardware_repair','testpoint_edl','disassembly','reassembly','flashing_guide','ubl_guide')),
    step_order      INT NOT NULL,
    title           VARCHAR(200) NOT NULL,
    description     TEXT NOT NULL,
    image_url       TEXT,
    required_tools  TEXT[],
    risk_level      VARCHAR(10) CHECK (risk_level IN ('low','medium','high')),
    estimated_minutes INT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_guides_model ON device_repair_guides(device_model);
CREATE INDEX idx_guides_type ON device_repair_guides(guide_type);
```

### Entity Relationship Summary

```
branches ──┬── users
           ├── service_tickets
           ├── inventory
           ├── stock_mutations
           └── transactions

customers ──┬── service_tickets
            └── transactions

devices ──── service_tickets

service_tickets ──┬── ticket_logs
                  ├── ticket_repair_details
                  └── transactions

spareparts ──┬── inventory
             ├── stock_mutations
             └── ticket_repair_details

device_chipset_info ─── device_firmware_db
device_chipset_info ─── device_testpoints
device_chipset_info ─── device_firmware_links

service_tickets ──┬── flashing_logs
                  ├── pre_flashing_checklist
                  ├── battery_health_logs
                  ├── device_repair_guides (via device_model)
                  └── device_arb_info (via device_model)

devices ──── battery_health_logs
```

## 3.3 Data Flow Diagram (DFD Level 1)

```
┌─────────┐   1. Check-In & Gejala    ┌──────────────┐
│Pelanggan│ ──────────────────────────>│              │
│         │<────────────────────────── │   SISTEM     │
│         │   2. Estimasi Biaya + Link │   SERVICE    │
│         │      Tracking WA           │              │
│         │                           │   +----------│
│         │   8. Invoice Digital      │   │  AI      │
└─────────┘<──────────────────────────│   │  Engine  │
                                      │   +----------│
┌─────────┐   3. Diagnosa Awal (Auto) │              │
│ Admin   │ ──────────────────────────>│              │
│         │<────────────────────────── │              │
└─────────┘   3a. Hasil AI Diagnosis   │              │
                                      │              │
┌─────────┐   4. Ambil Task            │              │
│ Teknisi │ ──────────────────────────>│              │
│         │<────────────────────────── │              │
└─────────┘   4a. AI Copilot Guidance  │              │
       │                               │              │
       │ 5. Catat Repair Log + Part    │              │
       └──────────────────────────────>│              │
                                      │              │
┌─────────┐   6. Auto Restock Alert   │              │
│ Owner   │<──────────────────────────│              │
│         │<──────────────────────────│              │
└─────────┘   7. AI Narrative Report   └──────────────┘
                                              │
                                     ┌────────▼────────┐
                                     │  WhatsApp        │
                                     │  Gateway API     │
                                     │  (Notification)  │
                                     └─────────────────┘
```

**Alur Detail:**

1. **Input:** Pelanggan datang, admin input data (customer, device, complaint)
2. **Diagnosa:** Sistem kirim complaint ke AI Diagnosis Agent → dapat hasil prediksi kerusakan
3. **Estimasi:** Sistem generate estimasi biaya + waktu → kirim ke WA pelanggan
4. **Approval:** Pelanggan reply "Ya" → status tiket jadi `approved`
5. **Alokasi:** Task muncul di dashboard teknisi → AI Copilot siap
6. **Repair (Hardware):** Teknisi ikuti panduan Repair Copilot, catat log, sistem validasi sparepart
7. **Repair (Software/Flashing):**
   a. Teknisi buka Flashing Assistant → masukkan model + tipe request
   b. AI Auto-detect chipset → tampilkan firmware links + tool downloads
   c. **Ampere Analysis:** Jika HP matot, teknisi input arus → AI diagnosis short/soft brick
   d. **ARB Safe-Guard:** AI cek level ARB → warning jika downgrade berbahaya
   e. **Testpoint Guide:** Tampilkan gambar testpoint jika perlu EDL mode
   f. **Pre-Flash Checklist:** Teknisi centang FRP, Mi Cloud, backup → baru bisa flash
   g. Setelah selesai → input hasil (sukses/gagal/brick) → flashing_log tersimpan
8. **Battery Health:** Jika HP hidup, teknisi scan via ADB → AI hitung kesehatan baterai → otomatis ke nota
9. **QA → Selesai:** Tiket masuk QA → jika lolos → `completed` → pelanggan di-notifikasi
10. **Payment:** Admin buat invoice di POS → pelanggan bayar → barang diserahkan
11. **Backend:** Setiap tahap update inventory (FIFO deduction), log AI, update flashing log, dan trigger event

## 3.4 Integrasi API

### WhatsApp Gateway API
```
POST /api/v1/notifications/whatsapp/send
{
  "to": "62812xxxxxx",
  "template": "ticket_created",
  "variables": {
    "customer_name": "Budi",
    "ticket_number": "SRV/20260614/0001",
    "estimated_cost": "350000",
    "estimated_days": "2",
    "tracking_url": "https://app.example.com/track/xxx"
  }
}
```

- Provider: WATI / Twilio / Fonnte (pilih yang support template message + interactive reply)
- Webhook untuk menerima reply dari pelanggan:
```
POST /api/v1/webhooks/whatsapp/reply
{
  "from": "62812xxxxxx",
  "message": "Ya",
  "ticket_id": "uuid-ticket"
}
```

### Forecasting / AI Service (Internal)
```
POST /api/v1/ai/diagnosis
{
  "device_model": "iPhone 11",
  "symptoms": ["mati total", "terjatuh", "layar retak", "tidak bergetar saat dicharge"],
  "previous_repairs": []
}

Response:
{
  "diagnosis": [
    {"komponen": "IC Power", "probabilitas": 0.75, "estimasi_biaya": 250000, "estimasi_waktu": "2 hari"},
    {"komponen": "LCD Connector", "probabilitas": 0.45, "estimasi_biaya": 150000, "estimasi_waktu": "1 hari"}
  ],
  "severity": "high",
  "recommended_action": "Periksa tegangan pada jalur VCC_MAIN, jika 0V maka IC Power short"
}
```

---

# 4. PANDUAN UI/UX DESIGN (MINIMALIST LUXURY)

## 4.1 Filosofi Desain

**"Minimalist Luxury"** — Mewah dalam kesederhanaan. Setiap elemen memiliki tujuan. Tidak ada dekorasi berlebihan. Ruang adalah fitur, bukan kekosongan.

| Prinsip | Penerapan |
|---|---|
| **Whitespace as a feature** | Padding 24–40px antar card, margin 48px antar section |
| **Typographic hierarchy** | 3 level heading maksimal per halaman |
| **Functional clarity** | Setiap klik memiliki 1 outcome yang jelas |
| **Consistency** | Satu sistem grid, satu set spacing tokens |
| **Data-first** | Grafik & angka adalah hero, bukan ilustrasi |

## 4.2 Palet Warna (Token-based Design System)

```css
:root {
  /* Netral — dasar yang bersih & premium */
  --color-bg-primary:     #FAFAF8;    /* Off-white hangat */
  --color-bg-secondary:   #F3F2EF;    /* Light gray lembut */
  --color-bg-card:        #FFFFFF;
  --color-bg-sidebar:     #1A1A1A;    /* Rich Black untuk sidebar */

  /* Teks */
  --color-text-primary:   #1A1A1A;    /* Hampir hitam */
  --color-text-secondary: #6B7280;    /* Gray seimbang */
  --color-text-muted:     #9CA3AF;    /* Untuk label sekunder */
  --color-text-inverse:   #FFFFFF;

  /* Aksen */
  --color-accent-gold:    #C9A84C;    /* Champagne Gold — premium, status penting */
  --color-accent-blue:    #2563EB;    /* Electric Blue — AI, interaktif */
  --color-accent-blue-hover: #1D4ED8;

  /* Status */
  --color-success:        #059669;    /* Emerald */
  --color-warning:        #D97706;    /* Amber */
  --color-error:          #DC2626;    /* Red */
  --color-info:           #0284C7;    /* Sky Blue */

  /* Border */
  --color-border:         #E5E7EB;
  --color-border-hover:   #D1D5DB;

  /* Shadow */
  --shadow-sm:  0 1px 2px rgba(0,0,0,0.04);
  --shadow-md:  0 4px 12px rgba(0,0,0,0.06);
  --shadow-lg:  0 8px 24px rgba(0,0,0,0.08);
  --shadow-xl:  0 16px 48px rgba(0,0,0,0.10);
}
```

## 4.3 Tipografi

- **Font Utama (UI):** Inter — sans-serif modern, keterbacaan tinggi di layar
- **Font Data/Angka:** JetBrains Mono atau Tabular — untuk tabel & grafik
- **Scale:**
  - Display (Hero): 32px / 2rem — weight 700
  - H1: 24px / 1.5rem — weight 700
  - H2: 20px / 1.25rem — weight 600
  - H3: 16px / 1rem — weight 600
  - Body: 14px / 0.875rem — weight 400
  - Small/Caption: 12px / 0.75rem — weight 400
  - Data large: 36px / 2.25rem — weight 700 (tabular)

## 4.4 Layout & Component Design

### Dashboard Utama (Owner/Admin)

```
┌──────────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]                     │ [MAIN CONTENT]                       │
│ ┌─────────┐                   │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
│ │ Logo    │                   │ │Card 1│ │Card 2│ │Card 3│ │Card 4│ │
│ │         │                   │ │Omset │ │Ticket│ │Rata2 │ │Margin│ │
│ ├─────────┤                   │ │Hari  │ │Aktif │ │Waktu │ │%     │ │
│ │ Menu    │                   │ │Rp 5.2M│ │ 12   │ │2.3 jam│ │ 42%  │ │
│ │         │                   │ └──────┘ └──────┘ └──────┘ └──────┘ │
│ │ ■ Home  │                   │                                       │
│ │ ■ Check │                   │ ┌─────────────────────────────────┐  │
│ │ ■ Tiket │                   │ │ GRAFIK TREND 30 HARI            │  │
│ │ ■ Servis│                   │ │ [Plotly interactive line chart] │  │
│ │ ■ Stok  │                   │ └─────────────────────────────────┘  │
│ │ ■ Kasir │                   │                                       │
│ │ ■ Laporan│                  │ ┌────────────┐ ┌──────────────────┐  │
│ │         │                   │ │TOP TEKNISI  │ │AI INSIGHT       │  │
│ │         │                   │ │1. Andi: 12tk│ │"Keuntungan naik │  │
│ │         │                   │ │2. Budi: 8tk │ │15%... disarankan │  │
│ │         │                   │ │3. Cici: 7tk│ │kurangi stok X"   │  │
│ └─────────┘                   │ └────────────┘ └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### Card Component Spec
- Background: `--color-bg-card` (putih)
- Border radius: 12px
- Padding: 24px
- Shadow: `--shadow-sm` (default), `--shadow-md` (hover)
- Transition: all 0.2s ease
- Icon area: 40x40px rounded-lg dengan bg aksen

### Form Elements
- Input field: Border 1px, radius 8px, padding 12px 16px, focus ring 2px `--color-accent-blue`
- Button primary: bg `--color-accent-blue`, text white, radius 8px, padding 10px 20px
- Button secondary: bg transparent, border 1px, text `--color-text-primary`
- Button ghost: no border, hover bg subtle

### Sidebar
- Background: `--color-bg-sidebar` (#1A1A1A)
- Width: 260px
- Menu item: padding 12px 20px, hover bg rgba(255,255,255,0.08)
- Active: left border 3px `--color-accent-gold`
- Icons: outline style, 20px

### Data Tables
- Header: bg `--color-bg-secondary`, text `--color-text-secondary`, weight 600
- Row: hover bg `--color-bg-secondary`
- Border: horizontal only, `--color-border`
- Pagination: simple, di pojok kanan bawah

### AI Insight Card
- Border left 4px `--color-accent-gold`
- Icon AI (sparkle) di samping judul
- Text body: `--color-text-secondary`
- Tombol "Detail" dengan arrow

---

# 5. FITUR & MENU CERDAS (AI AGENTS)

## 5.1 [Menu] Smart Check-In & Diagnosis Agent

### AI Logic
```
INPUT: complaint (text bebas dari admin/teknisi)
       device_model (string)

PROSES:
1. Text Preprocessing
   - Tokenisasi & stemming (Bahasa Indonesia + English)
   - Ekstrak keywords: ["mati total", "layar retak", "tidak bergetar", "terjatuh"]
   - Mapping keywords ke database knowledge base (ai_diagnosis_knowledge_base)

2. Pattern Matching + Scoring
   - Cocokkan keywords dengan symptom_keywords di knowledge base
   - Hitung probabilitas: (keyword_match_count / total_keywords_in_db_entry) * weight
   - Ambil top-3 diagnosis dengan probabilitas tertinggi

3. Fallback: Jika tidak ada kecocokan di KB → panggil LLM (GPT-4o / Claude)
   - Prompt: "Based on these symptoms {complaint} for {device_model}, what are the 3 most likely faulty components? Include probability, cost estimate, and repair time."

4. Output
   - Daftar kemungkinan kerusakan (sorted by probability)
   - Estimasi biaya: sum of (component_cost * probability)
   - Estimasi waktu: weighted average
   - Severity level: low (<30%), medium (30-70%), high (>70%)
   - Recommended sparepart IDs yang mungkin diperlukan

5. Auto-create ticket dengan hasil diagnosis
6. Kirim estimasi ke WhatsApp pelanggan
```

### Implementasi Service
**File:** `services/ai_agent/diagnosis_agent.py`
```python
class DiagnosisAgent:
    async def diagnose(self, device_model: str, symptoms: List[str]) -> DiagnosisResult:
        # 1. Cari di knowledge base lokal
        kb_matches = await self._search_knowledge_base(device_model, symptoms)
        
        if kb_matches and kb_matches[0].probability > 0.7:
            return self._build_result(kb_matches[:3])
        
        # 2. Fallback ke LLM
        llm_result = await self._call_llm(device_model, symptoms)
        
        # 3. Simpan hasil LLM ke knowledge base untuk caching
        await self._save_to_kb(device_model, symptoms, llm_result)
        
        return llm_result
```

### UI
- Layar check-in: form input pelanggan (nama, no WA, device), kolom keluhan (textarea large)
- Setelah input → muncul **"AI Analysis Card"** dengan loading skeleton → hasil muncul dengan:
  - Progress bar per kemungkinan kerusakan (horizontal bar)
  - Total estimasi biaya (besar, gold color)
  - Tombol **"Kirim Estimasi ke Pelanggan"** → trigger WhatsApp

## 5.2 [Menu] Hardware Repair Copilot

### AI Logic
```
INPUT: ticket_id (sudah di-diagnosis)
       device_model

KNOWLEDGE BASE:
- Kumpulan step-by-step repair guide dari teknisi sebelumnya
- Setiap step memiliki: order, title, description, gambar (opsional),
  estimated_time, required_tools, risk_level

PROSES:
1. Load diagnosis dari ticket
2. Query repair_steps WHERE device_model = ticket.device_model
3. Jika tidak ada → generate dari LLM dengan template terstruktur
4. Tampilkan ke teknisi dalam bentuk checklist interaktif

VALIDASI SPAREPART:
- Saat teknisi pilih sparepart → cek compatibility:
  - sparepart.compatible_models HARUS contain device_model
  - Jika tidak → red warning + saran sparepart alternatif

FEEDBACK LOOP:
- Setiap selesai step → teknisi bisa rate "Membantu" / "Tidak membantu"
- Feedback dikirim ke ai_logs.feedback untuk fine-tuning
```

### UI
- Split panel: kiri (70%) panduan, kanan (30%) info tiket
- Setiap step berupa card dengan:
  - Nomor urut (lingkaran biru)
  - Judul step
  - Deskripsi
  - Tombol "Selesai" / "Skip" (jika tidak relevan)
  - Opsi upload foto (sebelum/sesudah)
- Sidebar kanan:
  - Tiket info (model, keluhan, diagnosis)
  - Sparepart yang digunakan (dengan status compatibility check)
  - Timer: sudah berapa lama di step ini

## 5.3 [Menu] Software Flashing & Unlock Assistant (Enhanced)

### AI Logic — Auto-Identify Link Download & Safe-Guard System

```
INPUT: device_model (string, wajib)
       current_firmware (string, opsional — bisa dideteksi dari ADB)
       bootloader_status (string: locked/unlocked/unknown)
       request_type (string: flash / unlock_bootloader / bypass_icloud / edl_unbrick)
       is_dead_unit (boolean: true jika HP mati total / matot)

┌──────────────────────────────────────────────────────────────────────────┐
│              STEP 1: CHIPSET & DEVICE PROFILE LOOKUP                     │
├──────────────────────────────────────────────────────────────────────────┤
│ Query device_chipset_info WHERE device_model                             │
│ → chipset_brand (qualcomm/mediatek/exynos/apple/unisoc)                  │
│ → chipset_model (Snapdragon 685, Dimensity 1080, dll)                    │
│ → flash_tool (SP Flash Tool, Odin, EDL Tool, 3uTools, MFIT, dll)        │
│ → scatter_file / DA file yang dibutuhkan                                 │
│ → edl_method (testpoint / vol combo / short pin)                         │
│ → bootloader_unlock_method (kode fastboot, token mi unlock, dll)         │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│              STEP 2: AUTO-LINK DOWNLOAD FINDER                           │
├──────────────────────────────────────────────────────────────────────────┤
│ Query device_firmware_links WHERE device_model:                          │
│   1. FIRMWARE_ROM → urut: is_verified DESC, download_count DESC          │
│      → Tampilkan semua versi dengan link download aktif                  │
│   2. RECOVERY → TWRP / PBRP / OrangeFox untuk model tersebut             │
│   3. SCATTER_DA → file scatter/DA untuk SP Flash Tool / EDL             │
│   4. FASTBOOT_TOOL → platform-tools, fastboot binaries                   │
│   5. OEM_UNLOCK_TOOL → Mi Unlock Tool, Samsung Tool, dll                │
│                                                                          │
│ Jika tidak ditemukan di DB → AI generate search query:                   │
│   "Stock ROM {device_model} official firmware download"                  │
│   → Tampilkan sebagai "Suggested Link (Unverified)" dengan warning       │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│              STEP 3: SAFE-GUARD ARB (ANTI-ROLLBACK) DETECTION           │
├──────────────────────────────────────────────────────────────────────────┤
│ Query device_arb_info WHERE device_model AND firmware_version            │
│                                                                          │
│ ARB Level yang terdeteksi:                                               │
│   - Level 0-3: Aman untuk downgrade (warning biasa)                     │
│   - Level 4-6: ⚠️ PERINGATAN — downgrade berisiko bootloop              │
│   - Level 7-10: 🚨 DILARANG DOWNGRADE — HARDBRICK PERMANEN              │
│                                                                          │
│ IF request_type == 'flash' AND user memilih firmware LEBIH TUA:         │
│   IF arb_level >= 4:                                                     │
│     Tampilkan RED ALERT BANNER:                                         │
│     ┌─────────────────────────────────────────────────────────────┐     │
│     │ 🚨  PERINGATAN HARDBRICK                                     │     │
│     │ Perangkat ini memiliki ARB Level {level}.                    │     │
│     │ Menurunkan ke versi {target} akan menyebabkan                │     │
│     │ HARDBRICK PERMANEN yang tidak dapat diperbaiki!              │     │
│     │ Versi minimum yang aman: {min_allowed_version}               │     │
│     │ [Saya Mengerti Risiko — Tetap Flash] [Batalkan]             │     │
│     └─────────────────────────────────────────────────────────────┘     │
│                                                                          │
│ IF request_type == 'unlock_bootloader':                                 │
│   Tampilkan peringatan:                                                  │
│   "UBL akan: (1) Menghapus semua data, (2) Membatalkan garansi,         │
│    (3) Beberapa bank app (BCA/m-Banking) mungkin tidak bisa login"      │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│              STEP 4: TESTPOINT GUIDE (jika HP mati total / EDL mode)    │
├──────────────────────────────────────────────────────────────────────────┤
│ IF is_dead_unit == true AND request_type == 'edl_unbrick':              │
│   Query device_testpoints WHERE device_model AND mode_type = 'edl_9008' │
│                                                                          │
│   IF testpoint ditemukan:                                                │
│     Tampilkan:                                                           │
│     ┌─────────────────────────────────────────────────────────────┐     │
│     │ 📍 TESTPOINT EDL — {device_model}                           │     │
│     │                                                              │     │
│     │ [ DIAGRAM GAMBAR ] ← dari image_url, dengan overlay         │     │
│     │   titik koordinat dari image_annotation                      │     │
│     │                                                              │     │
│     │ Langkah: {description}                                       │     │
│     │ Tingkat Kesulitan: {difficulty}                              │     │
│     │ [Tonton Video Tutorial] ← jika video_url tersedia            │     │
│     │ [Download Scatter/DA File] ← link dari device_firmware_links │     │
│     └─────────────────────────────────────────────────────────────┘     │
│                                                                          │
│   ELSE:                                                                  |
│     Tampilkan generic guide berdasarkan chipset_brand:                   │
│     - Qualcomm: "Short pin 1-2 atau D+ GND pada konektor USB"           │
│     - MediaTek: "Tekan Vol- lalu colok USB, cari di shielding"          │
│     - Kirim request ke admin untuk menambahkan testpoint model ini"     │
└──────────────────────────────────────────────────────────────────────────┘

OUTPUT:
{
  "chipset": { "brand": "mediatek", "model": "Dimensity 1080" },
  "recommended_firmware": {
    "version": "MIUI 14.0.7.0.TKFMIXM",
    "download_url": "https://...",
    "is_verified": true,
    "file_size_mb": 4500
  },
  "links": {
    "recovery": { "twrp": true, "url": "..." },
    "scatter_file": { "name": "MT6877_Android_scatter.txt", "url": "..." },
    "fastboot_tool": { "url": "https://developer.android.com/studio/releases/platform-tools" }
  },
  "arb": { "level": 4, "is_downgrade_safe": false, "min_allowed_version": "MIUI 13.0.2.0" },
  "testpoint": {
    "has_guide": true,
    "image_url": "https://cdn.example.com/testpoints/redmi_note_13_edl.png",
    "coordinates": [{"x": 320, "y": 480}, {"x": 340, "y": 480}],
    "difficulty": "medium"
  },
  "pre_flash_checklist": [
    "Logout Google Account (FRP)",
    "Logout Mi Cloud",
    "Backup data ke PC",
    "Baterai > 50%"
  ]
}
```

### Implementasi Service
**File:** `services/ai_agent/flashing_agent.py`
```python
class FlashingAgent:
    async def analyze(self, device_model: str, request_type: str,
                      current_firmware: str = None,
                      bootloader_status: str = 'unknown',
                      is_dead_unit: bool = False) -> FlashingResult:
        # Step 1: Chipset lookup
        chipset = await self._get_chipset_info(device_model)
        
        # Step 2: Firmware & link finder
        firmware_links = await self._find_firmware_links(device_model, chipset.chipset_brand)
        
        # Step 3: ARB check
        arb_info = None
        if current_firmware:
            arb_info = await self._check_arb(device_model, current_firmware, firmware_links[0].firmware_version if firmware_links else None)
        
        # Step 4: Testpoint guide (if dead unit)
        testpoint = None
        if is_dead_unit and request_type in ('edl_unbrick', 'flash'):
            testpoint = await self._get_testpoint_guide(device_model, chipset.chipset_brand)
        
        # Step 5: Safety validation
        safety_alerts = self._validate_safety(arb_info, bootloader_status, request_type)
        
        return FlashingResult(
            chipset=chipset,
            recommended_firmware=firmware_links[0] if firmware_links else None,
            all_links=firmware_links,
            arb=arb_info,
            testpoint=testpoint,
            safety_alerts=safety_alerts,
            pre_flash_checklist=self._get_pre_flash_checklist(device_model, request_type)
        )
    
    async def _check_arb(self, device_model: str, current_ver: str, target_ver: str) -> ArbInfo:
        """Cek ARB level dan keamanan downgrade"""
        arb = await device_arb_info.find_by_model(device_model, target_ver)
        if not arb:
            return ArbInfo(level=0, is_downgrade_safe=True, risk_none=True)
        
        is_downgrade = self._is_downgrade(current_ver, target_ver)
        if is_downgrade and arb.arb_level >= 4:
            arb.is_downgrade_safe = False
            arb.alert_level = 'critical' if arb.arb_level >= 7 else 'warning'
        
        return arb
```

### UI — Layout Spesifik

**Layout: 3-Panel Column**
```
┌────────────────────────────────────────────────────────────────────┐
│ [Panel Kiri — 35%]           │ [Panel Kanan — 65%]               │
│                              │                                     │
│ ┌─ DEVICE INFO ──────────┐  │ ┌─ TAB: FIRMWARE ────────────────┐ │
│ │ Model: Redmi Note 13   │  │ │ ┌─────────────────────────────┐ │ │
│ │ Chipset: Dimensity 1080│  │ │ │ 🔹 MIUI 14.0.7.0 (Stable)  │ │ │
│ │ Bootloader: Unlocked   │  │ │ │    Size: 4.5GB | Verified ✅│ │ │
│ │ IMEI: 86xxxxxxxxxxx    │  │ │ │    [Download] [Copy Link]   │ │ │
│ └────────────────────────┘  │ │ ├─────────────────────────────┤ │ │
│                              │ │ │ 🔸 MIUI 14.0.5.0 (Stable)  │ │ │
│ ┌─ REQUEST TYPE ────────┐  │ │ │    Size: 4.3GB | Verified ✅│ │ │
│ │ ○ Flash / Update ROM  │  │ │ │    [Download] [Copy Link]   │ │ │
│ │ ○ Unlock Bootloader   │  │ │ ├─────────────────────────────┤ │ │
│ │ ○ EDL Unbrick (Matot) │  │ │ │ ⚠️ MIUI 13.0.2.0 (Unstable)│ │ │
│ │ ○ Bypass Account      │  │ │ │    Size: 3.8GB | ARB Lv4 🚨│ │ │
│ └────────────────────────┘  │ │ │    [Download] [Copy Link]   │ │ │
│                              │ │ └─────────────────────────────┘ │ │
│ ┌─ QUICK LINKS ─────────┐  │ │                                   │ │
│ │ 📦 TWRP Recovery      │  │ │ ┌─ TAB: TESTPOINT ────────────┐ │ │
│ │ 📄 Scatter/DA File    │  │ │ │ [GAMBAR DIAGRAM]            │ │ │
│ │ 🔧 Platform Tools     │  │ │ │ Langkah: 1. Buka casing...  │ │ │
│ │ 🔓 Mi Unlock Tool     │  │ │ │ Kesulitan: Medium           │ │ │
│ └────────────────────────┘  │ │ └─────────────────────────────┘ │ │
│                              │ │                                   │ │
│ ┌─ SAFETY ALERTS ───────┐  │ │ ┌─ TAB: PRE-FLASH CHECKLIST ───┐ │ │
│ │ 🚨 ARB Level 4        │  │ │ │ ☐ Logout Google Account      │ │ │
│ │ Downgrade akan...      │  │ │ │ ☐ Logout Mi Cloud            │ │ │
│ └────────────────────────┘  │ │ │ ☐ Backup Data               │ │ │
│                              │ │ │ ☐ Baterai > 50%            │ │ │
│                              │ │ │ [Mulai Flashing]            │ │ │
│                              │ │ └─────────────────────────────┘ │ │
└────────────────────────────────────────────────────────────────────┘
```

**Komponen UI Khusus:**
- **ARB Warning Banner:** Fixed top, bg merah gradient, icon 🚨, teks putih, tombol "Saya Mengerti Risiko" (harus diklik untuk lanjut)
- **Testpoint Diagram Viewer:** Gambar SVG dengan titik koordinat interaktif (hover → zoom), bisa di-drag
- **Link Card:** Tiap link punya icon type (📦 ROM, 📄 Scatter, 🔧 Tool), badge verified/unverified, tombol kopi
- **Flashing Progress Tracker:** Setelah mulai, muncul progress bar dengan fase: `Preparing` → `Flashing` → `Verifying` → `Done`, teknisi input hasil akhir

## 5.4 [Menu] Predictive Inventory Smart-Saver

### AI Logic
```
SCHEDULER: Run setiap hari jam 00:00 (celery beat / cron job)

PROSES ANALISIS:
1. Query ticket_repair_details JOIN spareparts untuk 90 hari terakhir
   - Hitung usage_rate = total_pemakaian / 90 hari
   - Forecast 30 hari: usage_rate * 30

2. Restock Recommendation
   - Compare forecast dengan stok saat ini (inventory.quantity)
   - Jika forecast > current_stock → "Segera restok {qty_needed} unit"
   - Jika current_stock < min_stock → "Stok kritis!"

3. Dead Stock Detection
   - Cari sparepart dengan last_used > 60 hari
   - Hitung total nilai dead stock (quantity * purchase_price)
   - Rekomendasi: diskon X% untuk promo bundling

4. Trend Analysis
   - Bandingkan usage_rate 30 hari vs 90 hari
   - Jika naik >50% → "Trend meningkat tajam"
   - Jika turun >50% → "Permintaan menurun"

5. Simpan hasil ke ai_logs untuk dashboard
```

### UI
- Tabel inventory dengan color-coded status:
  - **Hijau**: stok aman
  - **Kuning**: stok menipis (< 2x min_stock)
  - **Merah**: stok kritis (< min_stock)
  - **Abu-abu**: dead stock (>60 hari tidak terpakai)
- Card "AI Recommendation":
  - Daftar item yang perlu direstock + qty rekomendasi
  - Daftar dead stock + saran promo
  - Tombol "Buat Purchase Order" (auto-fill dari rekomendasi)

## 5.5 [Menu] Executive Financial & Performance Analytics

### AI Logic
```
PROSES (end of month / on-demand):
1. Aggregasi data:
   - Total revenue, total cost (sparepart + jasa), gross profit
   - Revenue per teknisi
   - Revenue per kategori service
   - Average ticket value
   - Top 5 sparepart by usage

2. Perbandingan: bulan ini vs bulan lalu vs tahun lalu

3. AI Narrative Generation (LLM):
   Prompt template:
   ```
   Data: {json_data}
   Instructions:
   - Buat analisis naratif 3-5 paragraf dalam Bahasa Indonesia
   - Highlight: kenaikan/penurunan, tren, anomaly
   - Sertakan rekomendasi actionable
   - Gunakan angka spesifik
   - Tone: profesional, objektif
   ```

4. Anomaly Detection:
   - Bandingkan expense month-over-month
   - Jika ada lonjakan >30% tanpa korelasi revenue → flag sebagai "Potential Leak"
```

### UI
- Dashboard dengan 4 KPI cards di atas (revenue, profit, avg ticket, active tickets)
- 2 grafik Plotly interaktif:
  - **Revenue Trend** (line chart, bisa filter by teknisi)
  - **Service Category Breakdown** (pie/donut chart)
- Tabel "Teknisi Performance" (nama, tickets completed, revenue, avg time, profit margin)
- **AI Narrative Card** dengan teks insight
  - Expandable untuk baca full analysis
  - Tombol "Download Report as PDF"
- Anomaly alert: card merah jika terdeteksi kebocoran

## 5.6 [Menu] Hardware Diagnostic — Ampere & Battery Health Analyzer

### AI Logic — Current Consumption & Battery Degradation Analysis

```
┌──────────────────────────────────────────────────────────────────────────┐
│    INPUT: Current Reading dari USB Analyzer / Power Supply Digital       │
│           Hasil ADB Battery Info (atau manual oleh teknisi)              │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│    MODE A: CURRENT ANALYSIS (Ampere Meter)                              │
├──────────────────────────────────────────────────────────────────────────┤
│ Teknisi colokkan HP (dalam kondisi mati total) ke power supply/USB      │
│ analyzer, lalu masukkan angka ampere yang tertera di alat:              │
│                                                                          │
│ Form Input:                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │ Arus (A):        [_____0.02_____]  ⓘ contoh: 0.02, 0.5, 1.2   │   │
│   │ Tegangan (V):    [_____3.70_____]                               │   │
│   │ Kondisi:         [▼ Mati Total — tanpa tekan power  ]          │   │
│   │ Apakah ditekan:  ☐ Ya, saya tekan tombol power                  │   │
│   │                   ☐ Ya, saya lepas baterai dan colok langsung   │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ PROSES:                                                                  │
│ 1. Cari rule yang cocok di ampere_diagnosis_rules:                       │
│    WHERE min_ampere <= input_ampere AND max_ampere >= input_ampere       │
│    AND condition_note LIKE '%kondisi_terpilih%'                          │
│ 2. Urutkan by priority DESC, ambil match tertinggi                       │
│ 3. Generate diagnosis:                                                   │
│                                                                          │
│ HASIL DIAGNOSIS (tampil real-time setelah input):                        │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ 🔌 DIAGNOSIS ARUS                                                  │   │
│ │                                                                    │   │
│ │ Arus terukur: 0.02A                                               │   │
│ │                                                                    │   │
│ │ 🟡 SEVERITY: MEDIUM                                                │   │
│ │                                                                    │   │
│ │ Diagnosis: Software Brick atau kerusakan IC eMMC/UFS/CPU           │   │
│ │ — arus hanya cukup untuk RTC, tidak cukup untuk boot               │   │
│ │                                                                    │   │
│ │ Rekomendasi: Coba masuk EDL/Download Mode.                         │   │
│ │ Jika tidak bisa, indikasi eMMC/UFS korup atau IC CPU short rendah  │   │
│ │                                                                    │   │
│ │ [Simpan ke Tiket] [Lanjut ke Flashing Assistant]                   │   │
│ └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│    MODE B: BATTERY HEALTH (via ADB / Manual Input)                     │
├──────────────────────────────────────────────────────────────────────────┤
│ Jika HP masih bisa hidup (bukan matot), teknisi bisa:                    │
│   1. Colokkan HP ke komputer via USB dengan ADB aktif                    │
│   2. Klik tombol "Scan Battery via ADB" di sistem                        │
│   3. Sistem kirim perintah ADB otomatis:                                 │
│                                                                          │
│      adb shell dumpsys battery                                          │
│      → parse: level, voltage, temperature                               │
│                                                                          │
│      adb shell cat /sys/class/power_supply/battery/charge_full           │
│      → kapasitas saat ini (mAh)                                         │
│                                                                          │
│      adb shell cat /sys/class/power_supply/battery/charge_full_design    │
│      → kapasitas pabrik (mAh)                                           │
│                                                                          │
│      adb shell cat /sys/class/power_supply/battery/cycle_count           │
│      → jumlah siklus charge                                              │
│                                                                          │
│   4. Atau teknisi input manual jika ADB tidak tersedia:                   │
│      ┌──────────────────────────────────────────────────────────────┐   │
│      │ Kapasitas Saat Ini (mAh):  [______2850______]                │   │
│      │ Kapasitas Pabrik (mAh):    [______3500______]                │   │
│      │ Cycle Count:               [______420_______]                │   │
│      │ └──────────────────────────────────────────────────────────┘   │
│                                                                          │
│ OUTPUT:                                                                  │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ 🔋 DIAGNOSIS BATERAI                                               │   │
│ │                                                                    │   │
│ │ Kapasitas Saat Ini:  2.850 mAh                                     │   │
│ │ Kapasitas Pabrik:    3.500 mAh                                     │   │
│ │ Kesehatan:           81.4%                                         │   │
│ │ Cycle Count:         420                                           │   │
│ │                                                                    │   │
│ │ 📊 Status: Fair — masih layak pakai                                │   │
│ │    (81% artinya baterai sudah turun ~19% dari pabrik)             │   │
│ │                                                                    │   │
│ │ 💡 Rekomendasi:                                                    │   │
│ │    - Jika pelanggan komplain boros: sarankan ganti baterai          │   │
│ │    - Jika cycle >800: degradasi signifikan, rekomendasi ganti      │   │
│ │                                                                    │   │
│ │ [Simpan ke Tiket] [Tambah ke Nota Service]                         │   │
│ └────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Implementasi Service

**File:** `services/ai_agent/hardware_diagnostic_agent.py`
```python
class HardwareDiagnosticAgent:
    async def analyze_current(self, ampere: float, voltage: float,
                              condition: str) -> AmpereDiagnosisResult:
        # Cari rule yang sesuai
        rule = await ampere_diagnosis_rules.find_match(ampere, condition)
        return AmpereDiagnosisResult(
            ampere=ampere,
            severity=rule.severity,
            diagnosis=rule.diagnosis,
            recommended_action=rule.recommended_action,
            is_critical=(rule.severity == 'critical')
        )
    
    async def analyze_battery(self, ticket_id: str, device_id: str,
                              adb_result: AdbBatteryData = None,
                              manual: ManualBatteryInput = None) -> BatteryDiagnosis:
        data = adb_result or manual
        health = (data.current_capacity / data.design_capacity) * 100
        
        if health >= 85:
            status = "Good — baterai masih sehat"
        elif health >= 70:
            status = "Fair — masih layak pakai, mulai terlihat degradasi"
        elif health >= 50:
            status = "Poor — sangat disarankan ganti baterai"
        else:
            status = "Critical — baterai harus segera diganti"
        
        # Simpan ke DB
        await self._save_battery_log(ticket_id, device_id, data, health)
        
        return BatteryDiagnosis(
            current_capacity=data.current_capacity,
            design_capacity=data.design_capacity,
            health_percent=round(health, 2),
            cycle_count=data.cycle_count,
            status=status,
            recommendation=self._generate_recommendation(health, data.cycle_count)
        )
```

### UI — Layout

**Split Horizontal: Ampere (atas) & Battery (bawah)**

```
┌────────────────────────────────────────────────────────────────────────┐
│  🔌 HARDWARE DIAGNOSTIC — {device_model}                              │
│                                                                        │
│  ┌─ ANALISIS ARUS ─────────────────────────────────────────────────┐   │
│  │ ┌─ INPUT ───────────┐  ┌─ HASIL (real-time) ────────────────┐  │   │
│  │ │ Arus: [0.02] A    │  │ 🟡 Severity: MEDIUM                 │  │   │
│  │ │ Volt: [3.70] V    │  │                                     │  │   │
│  │ │ Kondisi: [▼ Matot]│  │ Diagnosis: Software Brick / IC CPU  │  │   │
│  │ │                    │  │ eMMC/UFS rusak                      │  │   │
│  │ │ [Analisis]         │  │                                     │  │   │
│  │ └────────────────────┘  │ Rekomendasi: Coba EDL Mode...      │  │   │
│  │                         │ [Simpan ke Tiket]                   │  │   │
│  │                         └─────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│  ┌─ ANALISIS BATERAI ──────────────────────────────────────────────┐   │
│  │ ┌─ METODE ───────────┐  ┌─ HASIL ───────────────────────────┐   │   │
│  │ │ ● Scan via ADB     │  │ 🔋 2.850 / 3.500 mAh (81.4%)      │   │   │
│  │ │ ○ Input Manual     │  │ 📊 Cycle: 420                     │   │   │
│  │ │                    │  │                                     │   │   │
│  │ │ [Mulai Scan ADB]   │  │ Status: Fair — masih layak         │   │   │
│  │ │                    │  │                                     │   │   │
│  │ │ Atau input manual: │  │ 💡 Cycle >800: sarankan ganti      │   │   │
│  │ │ mAh: [___2850___]  │  │                                     │   │   │
│  │ │ Des: [___3500___]  │  │ [Simpan ke Tiket] [Tambah Nota]    │   │   │
│  │ │ Cycle: [___420___] │  └─────────────────────────────────────┘   │   │
│  │ └────────────────────┘                                           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### Integrasi ADB untuk Battery Health

Sistem menyediakan **panel ADB Bridge** yang bisa diakses teknisi dari browser:

1. Teknisi install ADB di komputer (sudah include di installer sistem atau pakai ADBKit portable)
2. Colokkan HP ke komputer via USB
3. Di browser, klik "Scan Battery via ADB"
4. Sistem kirim request ke **ADB Bridge Service** (WebSocket/HTTP lokal)
5. ADB Bridge jalankan perintah, parse output, kirim ke server
6. Hasil langsung muncul di UI

**ADB Bridge Service** (service lokal di komputer teknisi):
```
File: services/adb_bridge/adb_service.go (Go — untuk performa parsing)
- WebSocket server di localhost:8765
- Menerima command dari frontend: {"action": "battery", "device_id": "xxxx"}
- Eksekusi adb shell command
- Parse & kirim balik: {"current_capacity": 2850, "design_capacity": 3500, "cycle_count": 420}
```

## 5.7 [Menu] Reset Data & Security Log (Pre-Flashing FRP Checker)

### AI Logic — Pre-Flashing Safety & Flashing Result Logger

```
┌──────────────────────────────────────────────────────────────────────────┐
│  TRIGGER: Teknisi memilih menu Flash / EDL Unbrick di Flashing Assistant │
│           → SEBELUM proses flashing dimulai → tampilkan checklist        │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 1: PRE-FLASHING CHECKLIST                                        │
├──────────────────────────────────────────────────────────────────────────┤
│ Wajib diisi teknisi sebelum flashing dimulai:                            │
│                                                                          │
│ ┌─ SECURITY CHECKLIST ──────────────────────────────────────────────┐   │
│ │  ☐  Google Account (FRP) sudah di-logout                           │   │
│ │     → Jika tidak, HP akan terkunci FRP setelah flash               │   │
│ │                                                                     │   │
│ │  ☐  Mi Cloud / Find My Device sudah dimatikan                      │   │
│ │     → Jika tidak, HP akan terkunci aktivasi                        │   │
│ │                                                                     │   │
│ │  ☐  iCloud / Find My iPhone sudah di-logout (khusus iOS)          │   │
│ │     → Jika tidak, HP akan terkunci Activation Lock                 │   │
│ │                                                                     │   │
│ │  ☐  Samsung Account sudah di-logout                                │   │
│ │     → Jika tidak, akan terkena Reactivation Lock (RRL)             │   │
│ │                                                                     │   │
│ │  ☐  Data pelanggan sudah di-backup                                 │   │
│ │     → Flashing akan menghapus semua data internal                  │   │
│ │                                                                     │   │
│ │  ☐  Baterai terisi >50%                                            │   │
│ │     → Risiko mati di tengah flashing (hardbrick)                   │   │
│ │                                                                     │   │
│ │  ☐  Kabel USB dalam kondisi baik                                   │   │
│ │     → Kabel putus/oksidasi menyebabkan flashing gagal              │   │
│ │                                                                     │   │
│ │  [☑ Centang Semua] [Lanjut ke Flashing] [Batalkan]                │   │
│ └─────────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│ Jika teknisi mencoba lanjut tanpa checklist lengkap:                     │
│   ⚠️ PERINGATAN: "Harap centang semua item sebelum flashing dimulai"     │
│   • Tombol "Lanjut" disabled sampai semua tercentang                     │
│                                                                          │
│ Setelah semua tercentang → pre_flashing_checklist INSERT untuk tiket    │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 2: FLASHING RESULT LOG                                           │
├──────────────────────────────────────────────────────────────────────────┤
│ Setelah proses flashing selesai, teknisi input hasil:                    │
│                                                                          │
│ ┌─ HASIL FLASHING ────────────────────────────────────────────────┐     │
│ │ ○ ✅ Sukses — HP menyala normal, firmware terbaca               │     │
│ │ ○ ⚠️ Sukses Sebagian — ada error tapi HP masih bisa boot       │     │
│ │ ○ ❌ Gagal — HP tidak bisa boot / error di tengah proses        │     │
│ │ ○ 🚨 Hardbrick — HP mati total, tidak bisa masuk recovery/EDL   │     │
│ │                                                                  │     │
│ │ Firmware After: [MIUI 14.0.7.0.TKFMIXM_____________]            │     │
│ │ Error Code:    [STATUS_SEC_IMG_TYPE_MISMATCH______]             │     │
│ │ Error Message: [__________________________________]             │     │
│ │ Catatan Teknisi: [_________________________________]             │     │
│ │                                                                  │     │
│ │ Durasi (menit): [___15___]                                       │     │
│ │                                                                  │     │
│ │ [Simpan Log]                                                     │     │
│ └──────────────────────────────────────────────────────────────────┘     │
│                                                                          │
│ Jika result = 'hardbrick':                                                │
│   → Muncul form tambahan:                                                │
│     "Tindakan Selanjutnya: [Rujuk ke Teknisi Senior / Ganti Motherboard]"│
│     → Auto-notifikasi ke admin: "⚠️ HARDBRICK terjadi pada tiket X"     │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  STEP 3: ANALYTICS — FLASHING PERFORMANCE DASHBOARD                     │
├──────────────────────────────────────────────────────────────────────────┤
│ Data dari flashing_logs diagregasi untuk dashboard owner/admin:           │
│                                                                          │
│ ┌─ FLASHING STATISTICS ───────────────────────────────────────────┐     │
│ │                                                                  │     │
│ │ Total Flashing Bulan Ini: 47                                    │     │
│ │ Tingkat Keberhasilan:     89.4% (42 sukses, 3 gagal, 2 brick)   │     │
│ │                                                                  │     │
│ │ Per Teknisi:                                                     │     │
│ │   Andi:    15 flash — 100% ✅                                    │     │
│ │   Budi:    18 flash — 83.3% ⚠️ (3 gagal)                        │     │
│ │   Cici:    14 flash — 92.9% ✅                                   │     │
│ │                                                                  │     │
│ │ Model Paling Sering Di-flash:                                    │     │
│ │   1. Redmi Note 13 — 12 kali                                     │     │
│ │   2. Samsung A54 — 8 kali                                        │     │
│ │   3. iPhone 11 — 6 kali                                          │     │
│ │                                                                  │     │
│ │ AI Insight: 🔍 "Tingkat kegagalan flashing Redmi Note 13         │     │
│ │ lebih tinggi (25%) dibanding rata-rata. Disarankan cek ulang     │     │
│ │ kualitas kabel USB atau versi firmware yang digunakan."          │     │
│ └──────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
```

### Implementasi Service

**File:** `services/ai_agent/flashing_security_agent.py`
```python
class FlashingSecurityAgent:
    async def get_checklist(self, device_model: str, request_type: str) -> List[ChecklistItem]:
        """Generate pre-flashing checklist based on device type"""
        checklist = [
            ChecklistItem("google_frp", "Google Account (FRP) sudah di-logout", False, is_critical=True),
        ]
        
        # Tambah berdasarkan brand
        if self._is_xiaomi(device_model):
            checklist.append(ChecklistItem("mi_cloud", "Mi Cloud / Find My Device dimatikan", False, is_critical=True))
        elif self._is_apple(device_model):
            checklist.append(ChecklistItem("icloud", "iCloud / Find My iPhone di-logout", False, is_critical=True))
        elif self._is_samsung(device_model):
            checklist.append(ChecklistItem("samsung_account", "Samsung Account di-logout", False, is_critical=True))
        
        checklist.extend([
            ChecklistItem("backup", "Data pelanggan sudah di-backup", False),
            ChecklistItem("battery", "Baterai > 50%", False),
            ChecklistItem("usb_cable", "Kabel USB dalam kondisi baik", False),
        ])
        
        return checklist
    
    async def save_flashing_log(self, ticket_id: str, teknisi_id: str,
                                  result: FlashingResultInput) -> FlashingLog:
        log = FlashingLog(
            ticket_id=ticket_id,
            teknisi_id=teknisi_id,
            result=result.result,
            firmware_after=result.firmware_after,
            error_code=result.error_code or None,
            error_message=result.error_message or None,
            duration_minutes=result.duration_minutes,
            teknisi_note=result.teknisi_note
        )
        await db.insert(log)
        
        # Jika hardbrick → notifikasi admin
        if result.result == 'hardbricked':
            await self._notify_admin_hardbrick(ticket_id, teknisi_id)
        
        return log
```

### UI — Flashing Log Dashboard

```
┌────────────────────────────────────────────────────────────────────────┐
│ 📊 FLASHING PERFORMANCE DASHBOARD — Bulan Juni 2026                   │
│                                                                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│ │  Total   │ │  Sukses  │ │  Gagal   │ │ Hardbrick│                  │
│ │   47     │ │   42     │ │    3     │ │    2     │                  │
│ │ Flashing │ │  89.4%   │ │   6.4%   │ │   4.2%  │                  │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘                  │
│                                                                        │
│ ┌─ TABEL LOG FLASHING (7 hari terakhir) ──────────────────────────┐   │
│ │ Tiket   │ Teknisi │ Model     │ Hasil    │ FW After   │ Durasi │   │
│ │─────────│─────────│───────────│──────────│────────────│────────│   │
│ │ SRV0001 │ Andi    │ RN 13     │ ✅ Sukses│ 14.0.7.0   │ 12 mnt │   │
│ │ SRV0002 │ Budi    │ A54       │ ❌ Gagal │ -          │ 5 mnt  │   │
│ │ SRV0003 │ Andi    │ iPhone 11 │ ✅ Sukses│ iOS 18.5   │ 25 mnt │   │
│ │ SRV0004 │ Cici    │ RN 13     │ 🚨 Brick │ -         │ 3 mnt  │   │
│ └──────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌─ AI INSIGHT ────────────────────────────────────────────────────┐   │
│ │ 🔍 Perhatikan: Redmi Note 13 memiliki tingkat kegagalan 25%     │   │
│ │ (3 dari 12 flashing gagal/brick). Disarankan:                   │   │
│ │ 1. Gunakan kabel USB original berkualitas                       │   │
│ │ 2. Pastikan versi firmware sesuai dengan region device           │   │
│ │ 3. Cek ARB level sebelum flashing                               │   │
│ └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 6. TASK BREAKDOWN — ROADMAP

## Fase 1: Sistem Inti & Database (Minggu 1–3)

| Task | Detail | Output |
|---|---|---|
| **1.1 Setup Environment** | Docker + Docker Compose, PostgreSQL 16, Redis, RabbitMQ | `docker-compose.yml` siap |
| **1.2 Backend Scaffold** | FastAPI project structure, dependency injection, config management | Struktur folder service |
| **1.3 Database Schema** | Jalankan semua DDL di atas (migration dengan Alembic) | Tabel created |
| **1.4 Auth System** | Register, Login, JWT, RBAC middleware | Endpoint auth |
| **1.5 Multi-Tenant** | Branch CRUD + scope isolation di query | Branch-aware queries |
| **1.6 Frontend Scaffold** | Next.js setup, Tailwind, design tokens, layout (sidebar + main) | Halaman kosong dengan layout |
| **1.7 UI Component Library** | Button, Input, Card, Table, Modal, Sidebar (sesuai spec desain) | Komponen reusable |

## Fase 2: Fitur Dasar Operasional (Minggu 4–7)

| Task | Detail | Output |
|---|---|---|
| **2.1 Customer Management** | CRUD + search by name/phone | Modul pelanggan |
| **2.2 Device Management** | CRUD + IMEI auto-detect (lookup brand/model) | Modul device |
| **2.3 Ticketing System** | Check-in → flow status → automatic ticket_number | Tiket service bisa dibuat |
| **2.4 Ticket Logging** | Log setiap perubahan status | Audit trail |
| **2.5 Inventory CRUD** | Sparepart master + inventory FIFO masuk | Stok bisa diisi |
| **2.6 Stock Mutation** | Pencatatan setiap pergerakan stok | Log akurat |
| **2.7 Hardware Diagnostic Basic** | Input ampere manual, diagnosis rule matching, battery manual input | Diagnosa hardware dasar |
| **2.8 POS Basic** | Invoice dari tiket, payment, print/invoice digital | Transaksi selesai |
| **2.9 Dashboard Owner** | KPI cards, grafik Plotly sederhana (total revenue, ticket count) | Dashboard dasar |

## Fase 3: Integrasi AI Agent (Minggu 8–12)

| Task | Detail | Output |
|---|---|---|
| **3.1 Knowledge Base Setup** | Seed data diagnosis + firmware + repair steps | Database pengetahuan awal |
| **3.2 AI Diagnosis Agent** | Implementasi DiagnosisAgent + fallback LLM + caching | Diagnosis otomatis di check-in |
| **3.3 WhatsApp Integration** | Setup gateway, template message, webhook reply | Notifikasi & konfirmasi otomatis |
| **3.4 Repair Copilot** | Display repair steps, checklist, sparepart validation | Panduan perbaikan interaktif |
| **3.5 Flashing Assistant** | Firmware DB query, chipset detection, ARB safe-guard, testpoint guide, auto-link download | Assistant software lengkap |
| **3.6 Flashing Security Agent** | Pre-flash checklist (FRP, cloud logout), flashing result logging, hardbrick notification | Keamanan flashing terjamin |
| **3.7 Hardware Diagnostic Agent** | Ampere analysis engine, battery health via ADB, diagnosis rules | Diagnosa hardware otomatis |
| **3.8 ADB Bridge Service** | Go service untuk eksekusi ADB command via WebSocket dari browser | Integrasi ADB real-time |
| **3.9 Predictive Inventory** | Scheduler, trend analysis, restock/deadstock detection | Rekomendasi stok otomatis |
| **3.10 Financial AI Narrative** | Aggregasi data + LLM narrative generation | Insight naratif bulanan |
| **3.11 AI Logging + Flashing Stats** | Semua hasil AI tercatat + dashboard performa flashing per teknisi | Logging + analytics |

## Fase 4: UI Refinement & Final (Minggu 13–16)

| Task | Detail | Output |
|---|---|---|
| **4.1 UI Polish** | Animasi transisi, loading skeleton, responsive mobile | UI mulus |
| **4.2 AI Insight Card** | Integrasi semua rekomendasi AI ke dashboard card | AI terasa "hadir" |
| **4.3 Error Handling** | Global exception handler, user-friendly error messages | Tidak ada 500 mentah |
| **4.4 Performance Optimization** | Query optimization, Redis caching, pagination | <2s response |
| **4.5 Security Audit** | SQL injection check, XSS, CSRF, rate limiting | Security hardening |
| **4.6 Beta Testing** | Deploy ke 3 toko service riil, collect feedback | Bug report + improvement |
| **4.7 Documentation** | API docs (OpenAPI), deployment guide, user guide | Docs siap pakai |

---

## Lampiran: Struktur Folder (Backend)

```
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py
│   │   │   │   ├── customers.py
│   │   │   │   ├── devices.py
│   │   │   │   ├── tickets.py
│   │   │   │   ├── inventory.py
│   │   │   │   ├── pos.py
│   │   │   │   ├── analytics.py
│   │   │   │   └── ai/
│   │   │   │       ├── diagnosis.py
│   │   │   │       ├── copilot.py
│   │   │   │       ├── flashing.py
│   │   │   │       ├── inventory_predict.py
│   │   │   │       └── finance_narrative.py
│   │   │   └── __init__.py
│   │   └── deps.py          # Dependency injection (DB, auth, RBAC)
│   ├── core/
│   │   ├── config.py         # Settings via pydantic-settings
│   │   ├── security.py       # JWT, bcrypt hashing
│   │   └── database.py       # SQLAlchemy engine + session
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── device.py
│   │   ├── ticket.py
│   │   ├── sparepart.py
│   │   ├── inventory.py
│   │   ├── transaction.py
│   │   └── ai_log.py
│   ├── schemas/              # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── ticket.py
│   │   └── ...
│   ├── services/             # Business logic
│   │   ├── auth_service.py
│   │   ├── ticket_service.py
│   │   ├── inventory_service.py  # FIFO logic here
│   │   ├── notification_service.py
│   │   └── ai_agent/
│   │       ├── base_agent.py
│   │       ├── diagnosis_agent.py
│   │       ├── copilot_agent.py
│   │       ├── flashing_agent.py
│   │       ├── hardware_diagnostic_agent.py
│   │       ├── flashing_security_agent.py
│   │       ├── inventory_predict_agent.py
│   │       └── finance_narrative_agent.py
│   ├── workers/              # Background tasks (Celery / RQ)
│   │   ├── inventory_scheduler.py
│   │   └── whatsapp_worker.py
│   └── main.py               # FastAPI app factory
├── adb_bridge/               # ADB Bridge Service (Go)
│   ├── main.go
│   ├── adb_executor.go
│   ├── battery_parser.go
│   └── websocket_handler.go
├── alembic/                  # Database migrations
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Lampiran: Struktur Folder (Frontend)

```
frontend/
├── src/
│   ├── app/                   # Next.js App Router
│   │   ├── (auth)/login/
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx       # Home dashboard
│   │   │   ├── check-in/
│   │   │   ├── tickets/
│   │   │   ├── inventory/
│   │   │   ├── pos/
│   │   │   ├── ai-diagnosis/
│   │   │   ├── repair-copilot/
│   │   │   ├── flashing/
│   │   │   ├── hardware-diagnostic/    # Ampere & Battery Health
│   │   │   ├── flashing-log/            # Flashing result dashboard
│   │   │   └── analytics/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                # Design system components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   ├── KpiCard.tsx
│   │   │   ├── AlertBanner.tsx         # ARB Warning Banner (red/gold)
│   │   │   └── ProgressTracker.tsx     # Flashing progress bar
│   │   ├── ai/               # AI-specific components
│   │   │   ├── DiagnosisCard.tsx
│   │   │   ├── RepairStepList.tsx
│   │   │   ├── InventoryAlert.tsx
│   │   │   ├── AiNarrative.tsx
│   │   │   ├── FlashingAssistant.tsx   # 3-panel flashing layout
│   │   │   ├── FirmwareLinkCard.tsx    # Download link card
│   │   │   ├── TestpointViewer.tsx     # Interactive testpoint diagram
│   │   │   ├── AmpereAnalyzer.tsx      # Ampere input + diagnosis
│   │   │   ├── BatteryHealthScan.tsx   # ADB battery scanner
│   │   │   ├── PreFlashChecklist.tsx   # FRP/account checklist
│   │   │   └── FlashingResultForm.tsx  # Post-flashing result input
│   │   ├── charts/           # Plotly wrappers
│   │   │   ├── RevenueChart.tsx
│   │   │   ├── CategoryPie.tsx
│   │   │   └── FlashingStatsChart.tsx  # Flashing success/fail rate
│   │   └── layout/
│   │       ├── AppSidebar.tsx
│   │       ├── TopBar.tsx
│   │       └── PageContainer.tsx
│   ├── lib/
│   │   ├── api-client.ts      # Axios/fetch wrapper
│   │   └── utils.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   └── useTickets.ts
│   └── styles/
│       └── globals.css        # Tailwind + design tokens
├── tailwind.config.ts
├── package.json
└── tsconfig.json
```

---

> **Catatan Akhir:** Dokumen ini adalah *blueprint teknis* yang siap diimplementasikan. Setiap service, tabel, dan endpoint telah dirancang dengan prinsip modularitas — sehingga tim pengembang bisa mengerjakan modul secara paralel. Mulai dari Fase 1 (database & auth) sebagai fondasi, lalu bertahap hingga AI Agent di Fase 3. Dengan tambahan fitur **Auto-Identify Link Download**, **Safe-Guard ARB**, **Testpoint Guide**, **Ampere & Battery Health Analyzer**, dan **Pre-Flashing Security Log**, sistem ini tidak hanya menjadi pencatat transaksi — tetapi benar-benar menjadi *AI co-pilot* yang mendampingi teknisi dari diagnosis awal, perbaikan hardware, flashing software, hingga analitik bisnis.
