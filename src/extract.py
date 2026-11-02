"""
Extract: membaca semua file mentah dari data/raw.
Di tahap ini data hanya dibaca dengan pengaturan yang benar, belum diubah.
"""

from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def baca_wil1():
    return pd.read_excel(RAW / "laporan_wil1_surabaya_raya.xlsx")


def baca_wil2():
    # Semua kolom dibaca sebagai teks agar kode "007" tidak berubah menjadi 7
    return pd.read_csv(RAW / "laporan_wil2_malang_raya.csv", sep=";", dtype=str)


def baca_wil3():
    # Header tabel berada di baris ke-5
    return pd.read_excel(RAW / "Laporan Wilayah III Mataraman.xlsx", header=4)


def baca_wil4():
    return pd.read_csv(RAW / "wil4_tapalkuda_rekap.csv")


def baca_wil5():
    # Data dipisah per sheet tahun, lalu digabung
    sheets = pd.read_excel(RAW / "Wil5_Madura_Pantura.xlsx", sheet_name=None,
                           dtype={"periode": str})
    return pd.concat(sheets.values(), ignore_index=True)


def baca_target():
    return pd.read_excel(RAW / "target_anggaran_2024_2025.xlsx", sheet_name=None)


def baca_master():
    return pd.read_excel(RAW / "master_cabang.xlsx")


def extract_semua():
    return {
        "wil1": baca_wil1(),
        "wil2": baca_wil2(),
        "wil3": baca_wil3(),
        "wil4": baca_wil4(),
        "wil5": baca_wil5(),
        "target": baca_target(),
        "master": baca_master(),
    }


if __name__ == "__main__":
    data = extract_semua()
    for nama, isi in data.items():
        if isinstance(isi, dict):
            print(nama, {k: v.shape for k, v in isi.items()})
        else:
            print(nama, isi.shape)