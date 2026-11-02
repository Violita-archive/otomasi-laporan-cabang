-- Query analisis untuk menjawab pertanyaan di README
-- Posisi akhir yang dipakai: Desember 2025


-- Q1. Capaian target setiap cabang (Desember 2025)
SELECT
    kode_cabang,
    nama_cabang,
    wilayah,
    capaian_kredit,
    capaian_dpk,
    capaian_laba_ytd
FROM v_kinerja_cabang
WHERE periode = '2025-12'
ORDER BY kode_cabang;


-- Q1b. Capaian target per wilayah (Desember 2025)
SELECT
    wilayah,
    jumlah_cabang,
    capaian_kredit,
    capaian_dpk,
    capaian_laba_ytd,
    npl
FROM v_kinerja_wilayah
WHERE periode = '2025-12'
ORDER BY capaian_laba_ytd DESC;


-- Q2. Peringkat cabang berdasarkan capaian laba YTD 2025
SELECT
    RANK() OVER (ORDER BY capaian_laba_ytd DESC) AS peringkat,
    nama_cabang,
    wilayah,
    ROUND(laba_ytd, 0)        AS laba_ytd,
    ROUND(target_laba_ytd, 0) AS target_laba_ytd,
    capaian_laba_ytd
FROM v_kinerja_cabang
WHERE periode = '2025-12'
ORDER BY peringkat;


-- Q3. Cabang dengan NPL di atas 5% dan berapa bulan kondisinya bertahan
SELECT
    nama_cabang,
    wilayah,
    COUNT(*)     AS jumlah_bulan_npl_di_atas_5,
    MIN(periode) AS pertama_kali,
    MAX(periode) AS terakhir,
    MAX(npl)     AS npl_tertinggi
FROM v_kinerja_cabang
WHERE npl > 5
GROUP BY nama_cabang, wilayah
ORDER BY jumlah_bulan_npl_di_atas_5 DESC;


-- Q3b. NPL per cabang, Desember 2024 dibanding Desember 2025
SELECT
    nama_cabang,
    MAX(CASE WHEN periode = '2024-12' THEN npl END) AS npl_des_2024,
    MAX(CASE WHEN periode = '2025-12' THEN npl END) AS npl_des_2025,
    ROUND(MAX(CASE WHEN periode = '2025-12' THEN npl END)
        - MAX(CASE WHEN periode = '2024-12' THEN npl END), 2) AS perubahan
FROM v_kinerja_cabang
GROUP BY nama_cabang
ORDER BY perubahan DESC;


-- Q4. Tren bulanan seluruh cabang
SELECT
    periode,
    ROUND(SUM(kredit_outstanding), 0) AS kredit_outstanding,
    ROUND(SUM(total_dpk), 0)          AS total_dpk,
    ROUND(SUM(laba_sebelum_pajak), 0) AS laba_sebelum_pajak,
    ROUND(100.0 * SUM(kredit_bermasalah) / SUM(kredit_outstanding), 2) AS npl,
    ROUND(100.0 * SUM(dpk_giro + dpk_tabungan) / SUM(total_dpk), 2)   AS casa
FROM v_kinerja_cabang
GROUP BY periode
ORDER BY periode;


-- Q5. Penyebab perubahan laba 2025 dibanding 2024
-- Perubahan laba = perubahan pendapatan bunga - perubahan beban bunga
--                + perubahan pendapatan non bunga - perubahan biaya operasional
WITH per_tahun AS (
    SELECT
        kode_cabang,
        nama_cabang,
        tahun,
        SUM(pendapatan_bunga)    AS pendapatan_bunga,
        SUM(beban_bunga)         AS beban_bunga,
        SUM(pendapatan_nonbunga) AS pendapatan_nonbunga,
        SUM(biaya_operasional)   AS biaya_operasional,
        SUM(laba_sebelum_pajak)  AS laba,
        SUM(target_laba)         AS target_laba
    FROM v_kinerja_cabang
    GROUP BY kode_cabang, nama_cabang, tahun
)
SELECT
    a.nama_cabang,
    ROUND(100.0 * a.laba / a.target_laba, 2)                     AS capaian_laba_2025,
    ROUND(a.laba - b.laba, 0)                                    AS perubahan_laba,
    ROUND(a.pendapatan_bunga - b.pendapatan_bunga, 0)            AS dari_pendapatan_bunga,
    ROUND(-(a.beban_bunga - b.beban_bunga), 0)                   AS dari_beban_bunga,
    ROUND(a.pendapatan_nonbunga - b.pendapatan_nonbunga, 0)      AS dari_pendapatan_nonbunga,
    ROUND(-(a.biaya_operasional - b.biaya_operasional), 0)       AS dari_biaya_operasional
FROM per_tahun a
JOIN per_tahun b ON a.kode_cabang = b.kode_cabang AND b.tahun = 2024
WHERE a.tahun = 2025
ORDER BY capaian_laba_2025;


-- Q6. Cabang yang perlu perhatian (Desember 2025)
SELECT *
FROM v_flag_cabang
WHERE periode = '2025-12'
ORDER BY flag_npl + flag_kredit + flag_laba DESC, capaian_laba_ytd;


-- Q7. Efisiensi: BOPO rata-rata 2025 per cabang
SELECT
    nama_cabang,
    wilayah,
    ROUND(100.0 * SUM(beban_bunga + biaya_operasional)
        / SUM(pendapatan_bunga + pendapatan_nonbunga), 2) AS bopo_2025,
    -- Laba setahun dibagi rata-rata kredit, untuk membandingkan cabang besar dan kecil
    ROUND(100.0 * SUM(laba_sebelum_pajak) / AVG(kredit_outstanding), 2) AS laba_per_kredit_2025
FROM v_kinerja_cabang
WHERE tahun = 2025
GROUP BY nama_cabang, wilayah
ORDER BY bopo_2025 DESC;