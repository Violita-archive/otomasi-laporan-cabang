"""
Transform: menyeragamkan dan membersihkan data hasil extract.
Hasil disimpan di data/processed:
- kinerja_bulanan.csv : realisasi per cabang per bulan
- target_bulanan.csv  : target per cabang per bulan
- log_cleaning.csv    : catatan setiap perbaikan yang dilakukan

Cara menjalankan (dari folder utama proyek):
    python src/transform.py
"""

from pathlib import Path

import pandas as pd

from extract import extract_semua

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"

KOLOM_NILAI = ["kredit_outstanding", "dpk_giro", "dpk_tabungan", "dpk_deposito",
               "kredit_bermasalah", "pendapatan_bunga", "beban_bunga",
               "pendapatan_nonbunga", "biaya_operasional", "laba_sebelum_pajak"]
KOLOM_DPK = ["dpk_giro", "dpk_tabungan", "dpk_deposito"]
KOLOM_LABA = ["pendapatan_bunga", "beban_bunga", "pendapatan_nonbunga",
              "biaya_operasional", "laba_sebelum_pajak"]

BULAN_ID = {"Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04", "Mei": "05", "Jun": "06",
            "Jul": "07", "Agu": "08", "Sep": "09", "Okt": "10", "Nov": "11", "Des": "12"}

LOG = []


def catat(kode, periode, kolom, masalah, tindakan):
    LOG.append({"kode_cabang": kode, "periode": periode, "kolom": kolom,
                "masalah": masalah, "tindakan": tindakan})


# ---------------------------------------------------------------
# 1. Penyeragaman format per wilayah
# ---------------------------------------------------------------
def standar_wil1(df):
    df = df.copy()
    df.columns = df.columns.str.lower().str.replace(" ", "_")
    df["periode"] = pd.to_datetime(df["periode"]).dt.strftime("%Y-%m")
    return df


def standar_wil2(df):
    df = df.copy()
    df["periode"] = df["periode"].str[4:] + "-" + df["periode"].str[:3].map(BULAN_ID)
    df["kode_cabang"] = "KC" + df["kode_cabang"].str.zfill(3)

    # Format Indonesia: titik untuk ribuan, koma untuk desimal
    for kol in KOLOM_NILAI + ["total_dpk"]:
        teks = df[kol].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        df[kol] = pd.to_numeric(teks)
    return df


def standar_wil3(df):
    df = df.drop(columns="No").rename(columns={
        "Bulan": "periode", "Kode": "kode_cabang", "Nama Cabang": "nama_cabang",
        "Kredit (Rp Juta)": "kredit_outstanding", "Giro": "dpk_giro",
        "Tabungan": "dpk_tabungan", "Deposito": "dpk_deposito", "Total DPK": "total_dpk",
        "Kredit Bermasalah": "kredit_bermasalah", "Pend. Bunga": "pendapatan_bunga",
        "Beban Bunga": "beban_bunga", "Pend. Non Bunga": "pendapatan_nonbunga",
        "Biaya Operasional": "biaya_operasional", "Laba Sblm Pajak": "laba_sebelum_pajak"})

    # "01/2024" diubah menjadi "2024-01"
    df["periode"] = df["periode"].str[3:] + "-" + df["periode"].str[:2]
    df["kode_cabang"] = "KC" + df["kode_cabang"].astype(str).str.zfill(3)

    # "Rp 1,115,601.88" diubah menjadi 1115601.88
    for kol in KOLOM_NILAI + ["total_dpk"]:
        teks = df[kol].str.replace("Rp ", "", regex=False).str.replace(",", "", regex=False)
        df[kol] = pd.to_numeric(teks)
    return df


def standar_wil4(df):
    df = df.rename(columns={
        "tanggal": "periode", "outstanding_kredit": "kredit_outstanding",
        "dana_giro": "dpk_giro", "dana_tabungan": "dpk_tabungan",
        "dana_deposito": "dpk_deposito", "kredit_kol345": "kredit_bermasalah"})
    df["periode"] = df["periode"].str[:7]
    return df


def standar_wil5(df):
    df = df.rename(columns={
        "kd_cab": "kode_cabang", "cabang": "nama_cabang", "os_kredit": "kredit_outstanding",
        "giro": "dpk_giro", "tabungan": "dpk_tabungan", "deposito": "dpk_deposito",
        "npl_nominal": "kredit_bermasalah", "pdpt_bunga": "pendapatan_bunga",
        "pdpt_non_bunga": "pendapatan_nonbunga", "biaya_ops": "biaya_operasional",
        "laba_sbl_pajak": "laba_sebelum_pajak", "tot_dpk": "total_dpk"})
    df["periode"] = df["periode"].astype(str).str[:7]
    df["kode_cabang"] = df["kode_cabang"].str.replace("-", "", regex=False)
    return df


def gabung_wilayah(data):
    hasil = [standar_wil1(data["wil1"]), standar_wil2(data["wil2"]),
             standar_wil3(data["wil3"]), standar_wil4(data["wil4"]),
             standar_wil5(data["wil5"])]
    kolom = ["periode", "kode_cabang"] + KOLOM_NILAI + ["total_dpk"]

    # Nama cabang dari file tidak dipakai, nanti diambil dari master
    return pd.concat([d[kolom] for d in hasil], ignore_index=True)


# ---------------------------------------------------------------
# 2. Pembersihan
# ---------------------------------------------------------------
def hapus_duplikat(df):
    dup = df[df.duplicated()]
    for _, r in dup.iterrows():
        catat(r["kode_cabang"], r["periode"], "-", "baris duplikat", "baris dihapus")
    df = df.drop_duplicates().reset_index(drop=True)

    sisa = df.duplicated(subset=["kode_cabang", "periode"]).sum()
    if sisa > 0:
        print("Peringatan: masih ada", sisa, "cabang-bulan yang tercatat lebih dari sekali")
    return df


def perbaiki_satuan(df):
    # Nilai lebih dari 1000 kali median cabangnya dianggap ditulis dalam Rupiah penuh
    for kol in KOLOM_NILAI:
        median = df.groupby("kode_cabang")[kol].transform("median")
        salah = df[kol] > median * 1000
        for _, r in df[salah].iterrows():
            catat(r["kode_cabang"], r["periode"], kol, "satuan Rupiah penuh",
                  "dibagi 1.000.000")
        df.loc[salah, kol] = df.loc[salah, kol] / 1_000_000
    return df


def cek_total_dpk(df):
    hitung = df[KOLOM_DPK].sum(axis=1)
    lengkap = df[KOLOM_DPK + ["total_dpk"]].notna().all(axis=1)
    beda = lengkap & ((df["total_dpk"] - hitung).abs() > 1)
    for _, r in df[beda].iterrows():
        catat(r["kode_cabang"], r["periode"], "total_dpk",
              "total tidak sama dengan giro+tabungan+deposito",
              "total dihitung ulang dari komponen")

    # Jika hanya satu komponen kosong, nilainya diisi dari total dikurangi komponen lain
    satu_kosong = df[KOLOM_DPK].isna().sum(axis=1) == 1
    for kol in KOLOM_DPK:
        isi = satu_kosong & df[kol].isna() & df["total_dpk"].notna()
        lain = [k for k in KOLOM_DPK if k != kol]
        df.loc[isi, kol] = df.loc[isi, "total_dpk"] - df.loc[isi, lain].sum(axis=1)
        for _, r in df[isi].iterrows():
            catat(r["kode_cabang"], r["periode"], kol, "sel kosong",
                  "diisi dari total_dpk dikurangi komponen lain")
    return df


def lengkapi_laba(df):
    # laba = pendapatan bunga - beban bunga + pendapatan non bunga - biaya operasional
    # Jika hanya satu dari lima kolom ini kosong, nilainya bisa dihitung dari empat lainnya
    pb, bb, nb, bo, lb = (df[k] for k in KOLOM_LABA)
    rumus = {
        "pendapatan_bunga": lb + bb - nb + bo,
        "beban_bunga": pb + nb - bo - lb,
        "pendapatan_nonbunga": lb - pb + bb + bo,
        "biaya_operasional": pb - bb + nb - lb,
        "laba_sebelum_pajak": pb - bb + nb - bo,
    }
    satu_kosong = df[KOLOM_LABA].isna().sum(axis=1) == 1
    for kol, nilai in rumus.items():
        isi = satu_kosong & df[kol].isna()
        df.loc[isi, kol] = nilai[isi]
        for _, r in df[isi].iterrows():
            catat(r["kode_cabang"], r["periode"], kol, "sel kosong",
                  "dihitung dari rumus laba")
    return df


def lengkapi_bulan(df, master):
    # Setiap cabang harus punya 24 bulan, baris yang tidak ada ditambahkan dalam keadaan kosong
    semua_periode = sorted(df["periode"].unique())
    kerangka = pd.MultiIndex.from_product([master["kode_cabang"], semua_periode],
                                          names=["kode_cabang", "periode"])
    df = df.set_index(["kode_cabang", "periode"]).reindex(kerangka).reset_index()

    hilang = df[KOLOM_NILAI].isna().all(axis=1)
    for _, r in df[hilang].iterrows():
        catat(r["kode_cabang"], r["periode"], "-", "baris tidak ada",
              "baris ditambahkan, nilai diisi interpolasi")
    df["is_estimasi"] = hilang
    return df


def interpolasi(df):
    # Sel yang masih kosong diisi dengan nilai di antara bulan sebelum dan sesudahnya
    df = df.sort_values(["kode_cabang", "periode"]).reset_index(drop=True)
    for kol in KOLOM_NILAI:
        kosong = df[kol].isna()
        for _, r in df[kosong & ~df["is_estimasi"]].iterrows():
            catat(r["kode_cabang"], r["periode"], kol, "sel kosong", "diisi interpolasi")
        df[kol] = df.groupby("kode_cabang")[kol].transform(
            lambda s: s.interpolate(limit_direction="both"))
        df.loc[kosong, "is_estimasi"] = True
    return df


def transform_kinerja(data):
    df = gabung_wilayah(data)
    df = hapus_duplikat(df)
    df = perbaiki_satuan(df)
    df = cek_total_dpk(df)
    df = lengkapi_laba(df)
    df = lengkapi_bulan(df, data["master"])
    df = interpolasi(df)

    # Kolom total_dpk tidak disimpan karena bisa dihitung dari komponennya
    df = df.drop(columns="total_dpk")
    df[KOLOM_NILAI] = df[KOLOM_NILAI].round(2)

    info = data["master"][["kode_cabang", "nama_cabang", "kab_kota", "wilayah"]]
    df = df.merge(info, on="kode_cabang", how="left")
    urutan = ["periode", "kode_cabang", "nama_cabang", "kab_kota", "wilayah"] + KOLOM_NILAI
    return df[urutan + ["is_estimasi"]]


def transform_target(target_sheets):
    nama_kolom = {"Target Kredit": "target_kredit", "Target DPK": "target_dpk",
                  "Target Laba": "target_laba"}
    hasil = None
    for sheet, kol in nama_kolom.items():
        # Format lebar (bulan sebagai kolom) diubah menjadi format panjang
        panjang = target_sheets[sheet].drop(columns="nama_cabang").melt(
            id_vars="kode_cabang", var_name="periode", value_name=kol)
        panjang["periode"] = panjang["periode"].astype(str).str[:7]
        hasil = panjang if hasil is None else hasil.merge(panjang, on=["kode_cabang", "periode"])
    return hasil.sort_values(["kode_cabang", "periode"]).reset_index(drop=True)


if __name__ == "__main__":
    data = extract_semua()
    kinerja = transform_kinerja(data)
    target = transform_target(data["target"])
    log = pd.DataFrame(LOG)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    kinerja.to_csv(PROCESSED / "kinerja_bulanan.csv", index=False)
    target.to_csv(PROCESSED / "target_bulanan.csv", index=False)
    log.to_csv(PROCESSED / "log_cleaning.csv", index=False)

    print("kinerja_bulanan :", kinerja.shape)
    print("target_bulanan  :", target.shape)
    print("jumlah perbaikan:", len(log))
    print(log["masalah"].value_counts().to_string())