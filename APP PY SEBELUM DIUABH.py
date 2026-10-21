"""
Dashboard Indikator Pendidikan & IPM Provinsi Jawa Timur 2025
Sumber data : BPS (IPM, Rata-rata Lama Sekolah) & data jumlah sekolah/guru/murid
Arsitektur notebook: Excel -> DuckDB (schema raw & dw, star schema) -> DuckLake
MotherDuck: opsi koneksi aplikasi; publikasi belum tersedia pada notebook lampiran.

Jalankan lokal : streamlit run app.py
Koneksi MotherDuck dibaca dari st.secrets["MOTHERDUCK_TOKEN"].
Jika token tidak ada, dashboard memakai data/indikator_jatim.csv (mode lokal).
"""

import os

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# KONFIGURASI
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Pendidikan Jawa Timur",
    page_icon="📊",
    layout="wide",
)

MD_DATABASE = "jatim_dw"                      # nama database di MotherDuck
FACT_TABLE = "fact_indikator_pendidikan"      # tabel fakta (sudah denormalisasi)
CSV_FALLBACK = os.path.join(os.path.dirname(__file__), "data", "indikator_jatim.csv")
LOCAL_WAREHOUSE = os.path.join(os.path.dirname(__file__), "database", "warehouse_jatim.duckdb")

WARNA_JENIS = {"Kota": "#2563eb", "Kabupaten": "#f59e0b"}


# ------------------------------------------------------------------
# KONEKSI DATA
# ------------------------------------------------------------------
def _ambil_token():
    try:
        return st.secrets.get("MOTHERDUCK_TOKEN") or os.environ.get("MOTHERDUCK_TOKEN")
    except Exception:
        return os.environ.get("MOTHERDUCK_TOKEN")


def get_connection():
    """Kembalikan (koneksi, sumber, nama_tabel)."""
    token = _ambil_token()
    if token:
        cloud_con = None
        try:
            cloud_con = duckdb.connect(f"md:{MD_DATABASE}?motherduck_token={token}")
            cloud_con.execute(f"SELECT 1 FROM {FACT_TABLE} LIMIT 1")
            return cloud_con, "MotherDuck", FACT_TABLE
        except Exception:  # Pesan exception koneksi tidak ditampilkan agar token tidak bocor.
            if cloud_con is not None:
                cloud_con.close()
            st.warning("Koneksi MotherDuck belum tersedia. Menggunakan snapshot CSV lokal.")

    if os.path.isfile(LOCAL_WAREHOUSE):
        con = duckdb.connect(LOCAL_WAREHOUSE, read_only=True)
        return con, "DuckDB lokal", "dw.v_indikator_jawa_timur"

    con = duckdb.connect()
    if not os.path.isfile(CSV_FALLBACK):
        st.error("Data tidak ditemukan. Pastikan data/indikator_jatim.csv tersedia dalam proyek.")
        st.stop()
    source_df = pd.read_csv(CSV_FALLBACK)
    con.register("csv_snapshot", source_df)
    con.execute(f"CREATE OR REPLACE TABLE {FACT_TABLE} AS SELECT * FROM csv_snapshot")
    return con, "CSV lokal", FACT_TABLE


@st.cache_data(ttl=600, show_spinner="Memuat data…")
def load_data():
    con, sumber, tabel = get_connection()
    # Turunan indikator dihitung di sisi DuckDB/MotherDuck
    q = f"""
    SELECT
        kabupaten_kota,
        tahun,
        CASE WHEN kabupaten_kota LIKE 'Kota %' THEN 'Kota' ELSE 'Kabupaten' END AS jenis_wilayah,
        ipm,
        rata_lama_sekolah,
        sekolah_sd, sekolah_smp, sekolah_sma,
        sekolah_sd + sekolah_smp + sekolah_sma AS total_sekolah,
        guru_sd, guru_smp, guru_sma,
        guru_sd + guru_smp + guru_sma AS total_guru,
        murid_sd, murid_smp, murid_sma,
        murid_sd + murid_smp + murid_sma AS total_murid,
        ROUND(murid_sd  / NULLIF(guru_sd, 0), 2)  AS rasio_murid_guru_sd,
        ROUND(murid_smp / NULLIF(guru_smp, 0), 2) AS rasio_murid_guru_smp,
        ROUND(murid_sma / NULLIF(guru_sma, 0), 2) AS rasio_murid_guru_sma,
        ROUND((murid_sd + murid_smp + murid_sma)
              / NULLIF(guru_sd + guru_smp + guru_sma, 0), 2) AS rasio_murid_guru,
        ROUND((murid_sd + murid_smp + murid_sma)
              / NULLIF(sekolah_sd + sekolah_smp + sekolah_sma, 0), 1) AS murid_per_sekolah,
        ROUND(100.0 * murid_sma / NULLIF(murid_sd, 0), 1) AS persen_sma_thd_sd
    FROM {tabel}
    ORDER BY kabupaten_kota
    """
    try:
        return con.execute(q).df(), sumber
    finally:
        con.close()


df_all, SUMBER = load_data()

# ------------------------------------------------------------------
# SIDEBAR / FILTER
# ------------------------------------------------------------------
st.sidebar.header("Filter")
jenis = st.sidebar.multiselect(
    "Jenis wilayah", ["Kabupaten", "Kota"], default=["Kabupaten", "Kota"]
)
pilihan_wilayah = st.sidebar.multiselect(
    "Kabupaten/Kota (kosongkan = semua)",
    sorted(df_all["kabupaten_kota"].unique()),
)
rentang_ipm = st.sidebar.slider(
    "Rentang IPM",
    float(np.floor(df_all["ipm"].min())),
    float(np.ceil(df_all["ipm"].max())),
    (float(np.floor(df_all["ipm"].min())), float(np.ceil(df_all["ipm"].max()))),
    step=0.5,
)

df = df_all[df_all["jenis_wilayah"].isin(jenis)]
if pilihan_wilayah:
    df = df[df["kabupaten_kota"].isin(pilihan_wilayah)]
df = df[df["ipm"].between(*rentang_ipm)]

st.sidebar.markdown("---")
st.sidebar.caption(f"Sumber data: **{SUMBER}**")
st.sidebar.caption(f"Wilayah ditampilkan: **{len(df)}** dari {len(df_all)}")

# ------------------------------------------------------------------
# HEADER
# ------------------------------------------------------------------
st.title("Apa yang terlihat dari pendidikan Jawa Timur?")
st.caption(
    "Tahun integrasi 2025. Jelajahi 38 kabupaten/kota melalui IPM, lama sekolah, dan rasio murid per guru. "
    "Angka mengikuti wilayah yang dipilih. Sumber aktif: " + SUMBER + "."
)

if df.empty:
    st.info("Tidak ada wilayah yang cocok dengan filter. Ubah filter di sidebar.")
    st.stop()


def fmt(n, d=0):
    s = f"{n:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# ------------------------------------------------------------------
# KPI
# ------------------------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total Sekolah", fmt(df["total_sekolah"].sum()))
k2.metric("Total Guru", fmt(df["total_guru"].sum()))
k3.metric("Total Murid", fmt(df["total_murid"].sum()))
k4.metric("Rata-rata IPM antardaerah", fmt(df["ipm"].mean(), 2))
k5.metric("Rata-rata RLS antardaerah", fmt(df["rata_lama_sekolah"].mean(), 2))
total_guru = df["total_guru"].sum()
k6.metric("Murid per guru", fmt(df["total_murid"].sum() / total_guru, 1) if total_guru > 0 else "–")
st.caption("Rata-rata IPM/RLS memberi bobot sama pada setiap daerah, bukan angka resmi agregat provinsi. Total pendidikan hanya SD, SMP, dan SMA sesuai lampiran.")
tertinggi = df.loc[df["ipm"].idxmax()]
terendah = df.loc[df["ipm"].idxmin()]
st.info(f"Pada {len(df)} wilayah terpilih, IPM tertinggi adalah {tertinggi.kabupaten_kota} ({tertinggi.ipm:.2f}) dan terendah {terendah.kabupaten_kota} ({terendah.ipm:.2f}). Selisihnya {tertinggi.ipm - terendah.ipm:.2f} poin.")
with st.expander("Bagaimana membaca indikator?"):
    st.write("IPM merangkum capaian kesehatan, pendidikan, dan standar hidup. Lama sekolah adalah rata-rata tahun pendidikan formal. Murid per guru = jumlah murid dibagi jumlah guru, bukan jumlah murid per kelas.")
    st.write("Header data lama sekolah menyebut penduduk usia 15 tahun ke atas. RLS komponen IPM metode baru memakai penduduk usia 25 tahun ke atas. Tahun asal data sekolah/guru/murid perlu diverifikasi karena 2025 ditambahkan oleh notebook.")

# ------------------------------------------------------------------
# TAB
# ------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab_compare, tab5 = st.tabs(
    ["Peringkat IPM", "IPM vs Lama Sekolah", "Rasio Pendidikan", "Jenjang Pendidikan", "Bandingkan daerah", "Data & Proses"]
)

# --- Tab 1: peringkat IPM ---
with tab1:
    c1, c2 = st.columns([3, 2])
    with c1:
        d = df.sort_values("ipm")
        fig = px.bar(
            d, x="ipm", y="kabupaten_kota", color="jenis_wilayah", orientation="h",
            color_discrete_map=WARNA_JENIS,
            labels={"ipm": "IPM", "kabupaten_kota": "", "jenis_wilayah": "Jenis"},
            height=max(400, 22 * len(d)),
        )
        fig.add_vline(x=df_all["ipm"].mean(), line_dash="dash", line_color="gray",
                      annotation_text=f"Rata-rata 38 daerah {df_all['ipm'].mean():.2f}")
        fig.update_layout(margin=dict(l=0, r=10, t=30, b=0), legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.subheader("5 IPM tertinggi")
        st.dataframe(
            df.nlargest(5, "ipm")[["kabupaten_kota", "ipm", "rata_lama_sekolah"]],
            hide_index=True, width="stretch",
        )
        st.subheader("5 IPM terendah")
        st.dataframe(
            df.nsmallest(5, "ipm")[["kabupaten_kota", "ipm", "rata_lama_sekolah"]],
            hide_index=True, width="stretch",
        )
        rata_kota = df.loc[df.jenis_wilayah == "Kota", "ipm"].mean()
        rata_kab = df.loc[df.jenis_wilayah == "Kabupaten", "ipm"].mean()
        if pd.notna(rata_kota) and pd.notna(rata_kab):
            st.info(f"Pada filter ini, rata-rata IPM kota {rata_kota:.2f} dan kabupaten {rata_kab:.2f}. Selisih {rata_kota-rata_kab:.2f} poin.")

# --- Tab 2: hubungan IPM dan RLS ---
with tab2:
    if len(df) >= 3 and df["rata_lama_sekolah"].nunique() > 1 and df["ipm"].nunique() > 1:
        r = df["ipm"].corr(df["rata_lama_sekolah"])
        b1, b0 = np.polyfit(df["rata_lama_sekolah"], df["ipm"], 1)
        r2 = r ** 2
    else:
        r = b1 = b0 = r2 = np.nan

    c1, c2 = st.columns([3, 1])
    with c1:
        fig = px.scatter(
            df, x="rata_lama_sekolah", y="ipm", color="jenis_wilayah",
            size="total_murid", hover_name="kabupaten_kota",
            color_discrete_map=WARNA_JENIS, size_max=40,
            labels={"rata_lama_sekolah": "Rata-rata Lama Sekolah (tahun)", "ipm": "IPM",
                    "jenis_wilayah": "Jenis", "total_murid": "Total murid"},
            height=520,
        )
        if not np.isnan(b1):
            xs = np.linspace(df["rata_lama_sekolah"].min(), df["rata_lama_sekolah"].max(), 50)
            fig.add_scatter(x=xs, y=b0 + b1 * xs, mode="lines", name="Garis regresi",
                            line=dict(color="gray", dash="dash"))
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    with c2:
        st.metric("Korelasi Pearson (r)", "–" if np.isnan(r) else f"{r:.4f}")
        st.metric("Koefisien determinasi (R²)", "–" if np.isnan(r2) else f"{r2:.4f}")
        if not np.isnan(b1):
            st.markdown(f"**Persamaan:**  \nIPM = {b0:.2f} + {b1:.2f} × RLS")
            st.caption(
                f"Setiap tambahan 1 tahun rata-rata lama sekolah berasosiasi dengan "
                f"perbedaan IPM sekitar {b1:.2f} poin pada regresi deskriptif ini. "
                f"Hubungan ini tidak membuktikan sebab-akibat. Header RLS lampiran memakai usia 15+, "
                f"sedangkan RLS komponen IPM metode baru memakai usia 25+."
            )
        st.caption("Ukuran titik = total murid.")

# --- Tab 3: rasio pendidikan ---
with tab3:
    jenjang = st.radio("Jenjang", ["Semua", "SD", "SMP", "SMA"], horizontal=True)
    kolom = {"Semua": "rasio_murid_guru", "SD": "rasio_murid_guru_sd",
             "SMP": "rasio_murid_guru_smp", "SMA": "rasio_murid_guru_sma"}[jenjang]
    c1, c2 = st.columns(2)
    with c1:
        d = df.sort_values(kolom, ascending=False)
        fig = px.bar(
            d, x="kabupaten_kota", y=kolom, color="jenis_wilayah",
            color_discrete_map=WARNA_JENIS,
            labels={kolom: "Murid per guru", "kabupaten_kota": "", "jenis_wilayah": "Jenis"},
            title=f"Rasio murid per guru ({jenjang})", height=460,
        )
        fig.update_layout(xaxis_tickangle=-60, legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    with c2:
        fig = px.scatter(
            df, x="murid_per_sekolah", y="ipm", color="jenis_wilayah",
            hover_name="kabupaten_kota", color_discrete_map=WARNA_JENIS,
            labels={"murid_per_sekolah": "Rata-rata murid per sekolah", "ipm": "IPM",
                    "jenis_wilayah": "Jenis"},
            title="Kepadatan sekolah vs IPM", height=460,
        )
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    st.caption(
        "Rasio murid per guru dihitung di DuckDB: Σ murid / Σ guru. "
        "Nilai lebih tinggi berarti lebih banyak murid per guru secara agregat. Ini bukan ukuran jumlah murid per kelas atau mutu mengajar."
    )

# --- Tab 4: jenjang ---
with tab4:
    total = pd.DataFrame({
        "Jenjang": ["SD", "SMP", "SMA"] * 3,
        "Kategori": ["Sekolah"] * 3 + ["Guru"] * 3 + ["Murid"] * 3,
        "Jumlah": [
            df.sekolah_sd.sum(), df.sekolah_smp.sum(), df.sekolah_sma.sum(),
            df.guru_sd.sum(), df.guru_smp.sum(), df.guru_sma.sum(),
            df.murid_sd.sum(), df.murid_smp.sum(), df.murid_sma.sum(),
        ],
    })
    cols = st.columns(3)
    for col, kat in zip(cols, ["Sekolah", "Guru", "Murid"]):
        with col:
            fig = px.pie(total[total.Kategori == kat], names="Jenjang", values="Jumlah",
                         hole=0.5, title=f"Komposisi {kat.lower()}",
                         color_discrete_sequence=["#2563eb", "#10b981", "#f59e0b"])
            st.plotly_chart(fig, width="stretch")

    d = df.sort_values("persen_sma_thd_sd", ascending=False)
    fig = px.bar(
        d, x="kabupaten_kota", y="persen_sma_thd_sd", color="jenis_wilayah",
        color_discrete_map=WARNA_JENIS,
        labels={"persen_sma_thd_sd": "Murid SMA / murid SD (%)", "kabupaten_kota": "",
                "jenis_wilayah": "Jenis"},
        title="Perbandingan jumlah murid SMA dan SD",
        height=440,
    )
    fig.update_layout(xaxis_tickangle=-60, legend_title_text="")
    st.plotly_chart(fig, width="stretch")

    st.caption("Jumlah murid SD dan SMA berasal dari kelompok siswa berbeda. Rasio ini tidak menghitung angka putus sekolah atau tingkat transisi kohort.")

with tab_compare:
    st.subheader("Dua daerah, dua gambaran")
    st.caption("Pilihan daerah di tab ini terpisah dari filter sidebar. Data mencakup SD, SMP, dan SMA.")
    choices = sorted(df_all.kabupaten_kota.unique())
    c1, c2 = st.columns(2)
    a = c1.selectbox("Daerah pertama", choices, index=choices.index("Kota Surabaya"))
    b = c2.selectbox("Daerah kedua", choices, index=choices.index("Sampang"))
    for col, name in [(c1, a), (c2, b)]:
        row = df_all[df_all.kabupaten_kota == name].iloc[0]
        col.metric("IPM", fmt(row.ipm, 2))
        col.metric("Lama sekolah (tahun)", fmt(row.rata_lama_sekolah, 2))
        col.metric("Murid per guru", fmt(row.rasio_murid_guru, 2))
        col.metric("Total murid", fmt(row.total_murid))
    ra = df_all[df_all.kabupaten_kota == a].iloc[0]
    rb = df_all[df_all.kabupaten_kota == b].iloc[0]
    st.info(f"Selisih IPM {a} dikurangi {b}: {ra.ipm - rb.ipm:.2f} poin.")

# --- Tab 5: data & arsitektur ---
with tab5:
    st.subheader("Database DuckDB per dataset")
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "duckdb-logo.svg")
    if os.path.isfile(logo_path):
        st.image(logo_path, width=150)
    for filename, description in [
        ("ipm_2025.duckdb", "IPM: 38 wilayah"),
        ("lama_sekolah_2025.duckdb", "Lama sekolah: 38 wilayah, agregat provinsi terpisah"),
        ("sekolah_guru_murid.duckdb", "Sekolah/guru/murid: tiga tabel, masing-masing 38 wilayah"),
        ("warehouse_jatim.duckdb", "Warehouse terintegrasi: dua dimensi dan satu tabel fakta"),
    ]:
        db_path = os.path.join(os.path.dirname(__file__), "database", filename)
        if os.path.isfile(db_path):
            with open(db_path, "rb") as handle:
                st.download_button(description, handle.read(), file_name=filename, mime="application/octet-stream", key=filename)
    st.caption("Setiap file .duckdb adalah database persisten dan sudah dibuka ulang untuk verifikasi. Tiga sheet pendidikan berada dalam satu database sesuai satu file Excel.")
    st.subheader("Tabel data terintegrasi")
    st.dataframe(df, hide_index=True, width="stretch")
    st.download_button(
        "Unduh CSV (sesuai filter)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="indikator_pendidikan_jatim_2025.csv",
        mime="text/csv",
    )
    st.subheader("Alur data")
    st.markdown(
        """
| Tahap | Proses | Hasil |
|---|---|---|
| 1. Extract | Membaca 3 file Excel (IPM, RLS, sekolah/guru/murid) | DataFrame pandas |
| 2. Transform | Standarisasi nama wilayah, konversi numerik, buang header & agregat provinsi | 5 tabel bersih (38 wilayah) |
| 3. Load – raw | `raw.ipm`, `raw.jumlah_sekolah`, `raw.jumlah_guru`, `raw.jumlah_murid`, `raw.rata_lama_sekolah` | DuckDB |
| 4. Load – DW | Star schema: `dim_wilayah`, `dim_tahun`, `fact_indikator_pendidikan` | DuckDB schema `dw` |
| 5. Lakehouse | Salin dimensi & fakta ke DuckLake (Parquet + katalog metadata) | `lake_jatim` |
| 6. Cloud (opsional) | Koneksi aplikasi disiapkan; publikasi notebook belum tersedia | database `jatim_dw` bila sudah dikonfigurasi |
| 7. Visualisasi | Streamlit membaca MotherDuck atau snapshot CSV melalui DuckDB | Dashboard ini |
"""
    )
    st.caption(f"Sumber data aktif: {SUMBER}. Mode CSV menjalankan analisis snapshot melalui DuckDB, tanpa membaca DuckLake secara langsung.")
    st.write("Satu baris = satu wilayah pada satu tahun. Memilih jenis wilayah adalah slice. Memilih wilayah dengan rentang IPM adalah dice. Menjumlahkan sekolah/guru/murid adalah agregasi. Data satu tahun belum menyediakan tren tahunan.")
    st.caption("URL tabel sumber, tahun asal data pendidikan, dan cakupan sekolah perlu dilengkapi dari sumber asli. Hasil di atas bersifat deskriptif.")
