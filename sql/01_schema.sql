-- Star schema kinerja cabang
-- Grain: satu baris = satu cabang dalam satu bulan
-- Semua nilai dalam Rp juta

DROP VIEW IF EXISTS v_flag_cabang;
DROP VIEW IF EXISTS v_kinerja_wilayah;
DROP VIEW IF EXISTS v_kinerja_cabang;
DROP TABLE IF EXISTS fact_target;
DROP TABLE IF EXISTS fact_kinerja;
DROP TABLE IF EXISTS dim_waktu;
DROP TABLE IF EXISTS dim_cabang;

-- Dimensi cabang
CREATE TABLE dim_cabang (
    kode_cabang  TEXT PRIMARY KEY,
    nama_cabang  TEXT NOT NULL,
    kab_kota     TEXT,
    wilayah      TEXT,
    latitude     REAL,
    longitude    REAL
);

-- Dimensi waktu
CREATE TABLE dim_waktu (
    periode      TEXT PRIMARY KEY,   -- format YYYY-MM
    tahun        INTEGER NOT NULL,
    bulan        INTEGER NOT NULL,
    nama_bulan   TEXT,
    kuartal      INTEGER,
    semester     INTEGER
);

-- Fakta realisasi
CREATE TABLE fact_kinerja (
    periode              TEXT NOT NULL REFERENCES dim_waktu(periode),
    kode_cabang          TEXT NOT NULL REFERENCES dim_cabang(kode_cabang),
    kredit_outstanding   REAL,
    dpk_giro             REAL,
    dpk_tabungan         REAL,
    dpk_deposito         REAL,
    kredit_bermasalah    REAL,
    pendapatan_bunga     REAL,
    beban_bunga          REAL,
    pendapatan_nonbunga  REAL,
    biaya_operasional    REAL,
    laba_sebelum_pajak   REAL,
    is_estimasi          INTEGER DEFAULT 0,   -- 1 jika nilai hasil interpolasi
    PRIMARY KEY (periode, kode_cabang)
);

-- Fakta target
CREATE TABLE fact_target (
    periode        TEXT NOT NULL REFERENCES dim_waktu(periode),
    kode_cabang    TEXT NOT NULL REFERENCES dim_cabang(kode_cabang),
    target_kredit  REAL,
    target_dpk     REAL,
    target_laba    REAL,
    PRIMARY KEY (periode, kode_cabang)
);