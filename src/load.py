"""
Load: memasukkan data hasil transform ke database SQLite (star schema).

Cara menjalankan (dari folder utama proyek):
    python src/load.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
SQL = ROOT / "sql"
DB = ROOT / "database" / "kinerja_cabang.db"

NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]


def buat_dim_waktu(periode):
    waktu = pd.DataFrame({"periode": sorted(periode.unique())})
    waktu["tahun"] = waktu["periode"].str[:4].astype(int)
    waktu["bulan"] = waktu["periode"].str[5:].astype(int)
    waktu["nama_bulan"] = waktu["bulan"].map(lambda b: NAMA_BULAN[b - 1])
    waktu["kuartal"] = (waktu["bulan"] - 1) // 3 + 1
    waktu["semester"] = (waktu["bulan"] - 1) // 6 + 1
    return waktu


def jalankan_sql(conn, nama_file):
    conn.executescript((SQL / nama_file).read_text(encoding="utf-8"))


def load(master, kinerja, target):
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)

    # Tabel dibuat ulang setiap kali load dijalankan
    jalankan_sql(conn, "01_schema.sql")

    dim_cabang = master[["kode_cabang", "nama_cabang", "kab_kota", "wilayah",
                         "latitude", "longitude"]]
    dim_waktu = buat_dim_waktu(kinerja["periode"])
    fakta_kinerja = kinerja.drop(columns=["nama_cabang", "kab_kota", "wilayah"])
    fakta_kinerja["is_estimasi"] = fakta_kinerja["is_estimasi"].astype(int)

    dim_cabang.to_sql("dim_cabang", conn, if_exists="append", index=False)
    dim_waktu.to_sql("dim_waktu", conn, if_exists="append", index=False)
    fakta_kinerja.to_sql("fact_kinerja", conn, if_exists="append", index=False)
    target.to_sql("fact_target", conn, if_exists="append", index=False)

    jalankan_sql(conn, "02_views.sql")
    conn.commit()

    for tabel in ["dim_cabang", "dim_waktu", "fact_kinerja", "fact_target"]:
        jumlah = conn.execute(f"SELECT COUNT(*) FROM {tabel}").fetchone()[0]
        print(f"{tabel:<13}: {jumlah} baris")
    conn.close()


if __name__ == "__main__":
    master = pd.read_excel(ROOT / "data" / "raw" / "master_cabang.xlsx")
    kinerja = pd.read_csv(PROCESSED / "kinerja_bulanan.csv")
    target = pd.read_csv(PROCESSED / "target_bulanan.csv")
    load(master, kinerja, target)
    print("Database tersimpan di", DB)