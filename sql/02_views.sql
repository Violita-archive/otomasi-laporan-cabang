-- View untuk analisis, laporan, dan dashboard
-- Rasio ditulis dalam persen

DROP VIEW IF EXISTS v_flag_cabang;
DROP VIEW IF EXISTS v_kinerja_wilayah;
DROP VIEW IF EXISTS v_kinerja_cabang;

-- 1. Kinerja per cabang per bulan, lengkap dengan target dan rasio
CREATE VIEW v_kinerja_cabang AS
WITH dasar AS (
    SELECT
        k.periode,
        w.tahun,
        w.bulan,
        w.nama_bulan,
        c.kode_cabang,
        c.nama_cabang,
        c.kab_kota,
        c.wilayah,
        c.latitude,
        c.longitude,
        k.kredit_outstanding,
        k.dpk_giro,
        k.dpk_tabungan,
        k.dpk_deposito,
        k.dpk_giro + k.dpk_tabungan + k.dpk_deposito AS total_dpk,
        k.kredit_bermasalah,
        k.pendapatan_bunga,
        k.beban_bunga,
        k.pendapatan_bunga - k.beban_bunga AS pendapatan_bunga_bersih,
        k.pendapatan_nonbunga,
        k.biaya_operasional,
        k.laba_sebelum_pajak,
        t.target_kredit,
        t.target_dpk,
        t.target_laba,
        k.is_estimasi
    FROM fact_kinerja k
    JOIN dim_cabang c ON k.kode_cabang = c.kode_cabang
    JOIN dim_waktu w  ON k.periode = w.periode
    LEFT JOIN fact_target t ON k.periode = t.periode AND k.kode_cabang = t.kode_cabang
),
kumulatif AS (
    SELECT
        *,
        -- Laba dijumlahkan sejak Januari tahun berjalan (year to date)
        SUM(laba_sebelum_pajak) OVER (PARTITION BY kode_cabang, tahun ORDER BY periode) AS laba_ytd,
        SUM(target_laba) OVER (PARTITION BY kode_cabang, tahun ORDER BY periode) AS target_laba_ytd,
        LAG(kredit_outstanding, 1) OVER (PARTITION BY kode_cabang ORDER BY periode) AS kredit_bulan_lalu,
        LAG(kredit_outstanding, 12) OVER (PARTITION BY kode_cabang ORDER BY periode) AS kredit_tahun_lalu,
        LAG(total_dpk, 12) OVER (PARTITION BY kode_cabang ORDER BY periode) AS dpk_tahun_lalu
    FROM dasar
)
SELECT
    *,
    ROUND(100.0 * kredit_outstanding / target_kredit, 2) AS capaian_kredit,
    ROUND(100.0 * total_dpk / target_dpk, 2)             AS capaian_dpk,
    ROUND(100.0 * laba_ytd / target_laba_ytd, 2)         AS capaian_laba_ytd,
    ROUND(100.0 * kredit_bermasalah / kredit_outstanding, 2) AS npl,
    ROUND(100.0 * kredit_outstanding / total_dpk, 2)     AS ldr,
    ROUND(100.0 * (dpk_giro + dpk_tabungan) / total_dpk, 2) AS casa,
    ROUND(100.0 * (beban_bunga + biaya_operasional)
                / (pendapatan_bunga + pendapatan_nonbunga), 2) AS bopo,
    ROUND(100.0 * (kredit_outstanding / kredit_bulan_lalu - 1), 2) AS growth_kredit_mom,
    ROUND(100.0 * (kredit_outstanding / kredit_tahun_lalu - 1), 2) AS growth_kredit_yoy,
    ROUND(100.0 * (total_dpk / dpk_tahun_lalu - 1), 2)            AS growth_dpk_yoy
FROM kumulatif;


-- 2. Rekap per wilayah per bulan
CREATE VIEW v_kinerja_wilayah AS
SELECT
    periode,
    tahun,
    wilayah,
    COUNT(*)                     AS jumlah_cabang,
    SUM(kredit_outstanding)      AS kredit_outstanding,
    SUM(total_dpk)               AS total_dpk,
    SUM(kredit_bermasalah)       AS kredit_bermasalah,
    SUM(laba_sebelum_pajak)      AS laba_sebelum_pajak,
    SUM(laba_ytd)                AS laba_ytd,
    ROUND(100.0 * SUM(kredit_outstanding) / SUM(target_kredit), 2) AS capaian_kredit,
    ROUND(100.0 * SUM(total_dpk) / SUM(target_dpk), 2)             AS capaian_dpk,
    ROUND(100.0 * SUM(laba_ytd) / SUM(target_laba_ytd), 2)         AS capaian_laba_ytd,
    ROUND(100.0 * SUM(kredit_bermasalah) / SUM(kredit_outstanding), 2) AS npl,
    ROUND(100.0 * SUM(kredit_outstanding) / SUM(total_dpk), 2)     AS ldr
FROM v_kinerja_cabang
GROUP BY periode, tahun, wilayah;


-- 3. Penanda cabang yang perlu perhatian
-- Batas: NPL di atas 5%, capaian kredit di bawah 95%, capaian laba YTD di bawah 90%
CREATE VIEW v_flag_cabang AS
SELECT
    periode,
    kode_cabang,
    nama_cabang,
    wilayah,
    npl,
    capaian_kredit,
    capaian_dpk,
    capaian_laba_ytd,
    CASE WHEN npl > 5 THEN 1 ELSE 0 END               AS flag_npl,
    CASE WHEN capaian_kredit < 95 THEN 1 ELSE 0 END   AS flag_kredit,
    CASE WHEN capaian_laba_ytd < 90 THEN 1 ELSE 0 END AS flag_laba
FROM v_kinerja_cabang
WHERE npl > 5 OR capaian_kredit < 95 OR capaian_laba_ytd < 90;