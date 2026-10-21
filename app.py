"""
Dashboard Indikator Pendidikan & IPM Provinsi Jawa Timur 2025
Sumber data : BPS (IPM, Rata-rata Lama Sekolah) & data jumlah sekolah/guru/murid
Arsitektur notebook: Excel -> DuckDB (schema raw & dw, star schema) -> DuckLake
MotherDuck: opsi koneksi aplikasi; publikasi belum tersedia pada notebook lampiran.

Jalankan lokal : streamlit run app.py
Mode awal memakai warehouse DuckDB lokal, lalu CSV bila warehouse tidak dapat dibuka.
MotherDuck hanya dicoba bila DASHBOARD_ENABLE_MOTHERDUCK=1 dan token dikonfigurasi.
"""

import os
from html import escape

import streamlit as st

st.set_page_config(
    page_title="Dashboard Pendidikan Jawa Timur",
    page_icon="📊",
    layout="wide",
)
startup = st.empty()
startup.info("Menyiapkan visualisasi dashboard…")

import numpy as np
import pandas as pd
import duckdb
import plotly.express as px
import streamlit.components.v1 as components

from peta import ambang_tiga_kelas, bangun_peta_html, muat_geojson, titik_wilayah
from visualisasi import (WARNA_JENIS, fmt, nama_wilayah, terapkan_tema, gaya_grafik,
                         tampilkan_grafik, legenda_wilayah, grafik_peringkat, grafik_donut)

# ------------------------------------------------------------------
# KONFIGURASI
# ------------------------------------------------------------------
MD_DATABASE = "jatim_dw"                      # nama database di MotherDuck
FACT_TABLE = "fact_indikator_pendidikan"      # tabel fakta (sudah denormalisasi)
CSV_FALLBACK = os.path.join(os.path.dirname(__file__), "data", "indikator_jatim.csv")
LOCAL_WAREHOUSE = os.path.join(os.path.dirname(__file__), "database", "warehouse_jatim.duckdb")
USE_MOTHERDUCK = os.environ.get("DASHBOARD_ENABLE_MOTHERDUCK", "").lower() in {"1", "true", "yes"}

terapkan_tema()


# ------------------------------------------------------------------
# KONEKSI DATA
# ------------------------------------------------------------------
def _ambil_token():
    try:
        return st.secrets.get("MOTHERDUCK_TOKEN") or os.environ.get("MOTHERDUCK_TOKEN")
    except Exception:
        return os.environ.get("MOTHERDUCK_TOKEN")


def get_connection():
    """Kembalikan koneksi, sumber aktif, tabel, dan status koneksi cloud."""
    token = _ambil_token() if USE_MOTHERDUCK else None
    status_cloud = "belum_dikonfigurasi" if USE_MOTHERDUCK else "nonaktif"
    if token:
        cloud_con = None
        try:
            cloud_con = duckdb.connect(f"md:{MD_DATABASE}?motherduck_token={token}")
            cloud_con.execute(f"SELECT 1 FROM {FACT_TABLE} LIMIT 1")
            return cloud_con, "MotherDuck", FACT_TABLE, "aktif"
        except Exception:  # Pesan exception koneksi tidak ditampilkan agar token tidak bocor.
            if cloud_con is not None:
                cloud_con.close()
            status_cloud = "tidak_tersambung"

    if os.path.isfile(LOCAL_WAREHOUSE):
        con = None
        try:
            con = duckdb.connect(LOCAL_WAREHOUSE, read_only=True)
            con.execute("SELECT 1 FROM dw.v_indikator_jawa_timur LIMIT 1")
            return con, "DuckDB lokal", "dw.v_indikator_jawa_timur", status_cloud
        except duckdb.Error:
            if con is not None:
                con.close()
            print("[dashboard] Warehouse lokal tidak dapat dibuka. Memakai CSV lokal.", flush=True)

    con = duckdb.connect()
    if not os.path.isfile(CSV_FALLBACK):
        st.error("Data tidak ditemukan. Pastikan data/indikator_jatim.csv tersedia dalam proyek.")
        st.stop()
    source_df = pd.read_csv(CSV_FALLBACK)
    con.register("csv_snapshot", source_df)
    con.execute(f"CREATE OR REPLACE TABLE {FACT_TABLE} AS SELECT * FROM csv_snapshot")
    return con, "CSV lokal", FACT_TABLE, status_cloud


@st.cache_data(ttl=600, show_spinner="Memuat data…")
def load_data():
    con, sumber, tabel, status_cloud = get_connection()
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
        return con.execute(q).df(), sumber, status_cloud
    finally:
        con.close()


startup.info("Membaca data pendidikan…")
df_all, SUMBER, STATUS_CLOUD = load_data()
startup.empty()
print(f"[dashboard] Data siap: {SUMBER}, {len(df_all)} wilayah.", flush=True)

# ------------------------------------------------------------------
# SIDEBAR / FILTER
# ------------------------------------------------------------------
IPM_RANGE = (float(np.floor(df_all.ipm.min())), float(np.ceil(df_all.ipm.max())))


def reset_filter():
    st.session_state.filter_jenis = "Kabupaten dan kota"
    st.session_state.filter_wilayah = []
    st.session_state.filter_ipm = IPM_RANGE


def reset_pilihan_wilayah():
    st.session_state.filter_wilayah = []


st.sidebar.markdown('<div class="brand">JATIM / EDUCATION INSIGHTS</div>', unsafe_allow_html=True)
st.sidebar.header("Jelajahi wilayah")
st.sidebar.caption("Tentukan cakupan analisis Anda.")
jenis = st.sidebar.selectbox("Jenis wilayah", ["Kabupaten dan kota", "Kabupaten", "Kota"],
                             key="filter_jenis", on_change=reset_pilihan_wilayah)
wilayah_tersedia = df_all if jenis == "Kabupaten dan kota" else df_all[df_all.jenis_wilayah == jenis]
pilihan_wilayah = st.sidebar.multiselect(
    "Pilih kabupaten/kota", sorted(wilayah_tersedia.kabupaten_kota.unique()),
    format_func=nama_wilayah, placeholder="Pilih dari daftar…",
    accept_new_options=False, key="filter_wilayah",
    help="Klik kotak untuk membuka daftar. Anda dapat memilih lebih dari satu wilayah. Kosong berarti semua wilayah pada jenis yang dipilih.",
)
st.sidebar.caption(f"{len(wilayah_tersedia)} pilihan tersedia. Kosong = semua wilayah.")
st.session_state.setdefault("filter_ipm", IPM_RANGE)
rentang_ipm = st.sidebar.slider("Rentang IPM", *IPM_RANGE, step=0.5, key="filter_ipm")
st.sidebar.button("Reset semua filter", on_click=reset_filter, width="stretch")

df = wilayah_tersedia
if pilihan_wilayah:
    df = df[df.kabupaten_kota.isin(pilihan_wilayah)]
df = df[df.ipm.between(*rentang_ipm)]
st.sidebar.divider()
st.sidebar.caption(f"Menampilkan **{len(df)} dari {len(df_all)} wilayah**")
st.sidebar.caption(f"Sumber aktif: **{SUMBER}**")
st.sidebar.caption("Tahun integrasi 2025 · SD, SMP, SMA")

st.markdown('<div class="hero"><div class="eyebrow">DATA WAREHOUSE · JAWA TIMUR · 2025</div>'
            '<h1>Dashboard Pendidikan Jawa Timur</h1>'
            '<p>IPM, lama sekolah, serta distribusi sekolah, guru, dan murid di 38 kabupaten/kota.</p></div>',
            unsafe_allow_html=True)
if df.empty:
    st.info("Tidak ada wilayah yang cocok dengan filter. Ubah rentang IPM atau klik Reset semua filter.")
    st.stop()

# ------------------------------------------------------------------
# KPI
# ------------------------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Total sekolah", fmt(df.total_sekolah.sum()))
k2.metric("Total guru", fmt(df.total_guru.sum()))
k3.metric("Total murid", fmt(df.total_murid.sum()))
k4.metric("Rata-rata IPM", fmt(df.ipm.mean(), 2))
k5.metric("RLS · tahun", fmt(df.rata_lama_sekolah.mean(), 2))
total_guru = df.total_guru.sum()
k6.metric("Murid per guru", fmt(df.total_murid.sum() / total_guru, 1) if total_guru > 0 else "–")
st.caption("Rata-rata IPM/RLS memberi bobot sama pada setiap daerah; bukan angka resmi agregat provinsi. Total pendidikan mencakup SD, SMP, dan SMA.")

# ------------------------------------------------------------------
# NAVIGASI
# ------------------------------------------------------------------
tab1, tab_peta, tab2, tab3, tab4, tab_compare, tab5 = st.tabs(
    ["Ringkasan & peringkat", "Peta interaktif", "IPM & lama sekolah", "Rasio pendidikan", "Jenjang pendidikan", "Bandingkan daerah", "Data & proses"]
)

# --- Tab 0: peta interaktif dari unggahan ---
with tab_peta:
    st.subheader("Peta sebaran pendidikan")
    st.caption("Klik penanda untuk rincian wilayah. Gunakan +/− untuk zoom; filter wilayah mengikuti sidebar.")
    pc1, pc2, pc3 = st.columns([2, 3, 3])
    with pc1:
        indikator = st.radio("Indikator", ["Sekolah", "Guru", "Murid"], horizontal=True, key="peta_indikator")
    with pc2:
        jenjang_peta = st.radio("Jenjang", ["Semua", "SD", "SMP", "SMA"], horizontal=True, key="peta_jenjang")
    with pc3:
        warnai_ipm = st.checkbox("Warnai wilayah menurut IPM", value=False, key="peta_warna_ipm")

    awalan = {"Sekolah": "sekolah", "Guru": "guru", "Murid": "murid"}[indikator]
    kolom_peta = f"total_{awalan}" if jenjang_peta == "Semua" else f"{awalan}_{jenjang_peta.lower()}"
    judul_peta = f"Jumlah {awalan}" + ("" if jenjang_peta == "Semua" else f" {jenjang_peta}")

    geo = muat_geojson()
    titik = titik_wilayah(geo)
    tidak_cocok = sorted(set(df.kabupaten_kota) - set(titik))
    if tidak_cocok:
        st.warning("Batas wilayah belum tersedia untuk: " + ", ".join(tidak_cocok))
    wilayah_peta = []
    for r in df.itertuples():
        if r.kabupaten_kota not in titik:
            continue
        lat, lon = titik[r.kabupaten_kota]
        ukuran = {
            k: getattr(r, f"total_{k}" if jenjang_peta == "Semua" else f"{k}_{jenjang_peta.lower()}")
            for k in ("sekolah", "guru", "murid")
        }
        wilayah_peta.append({
            "nama": r.kabupaten_kota,
            "lat": lat,
            "lon": lon,
            "nilai": int(getattr(r, kolom_peta)),
            "rincian": [
                [judul_peta, fmt(getattr(r, kolom_peta))],
                ["Jenjang", "SD, SMP, SMA" if jenjang_peta == "Semua" else jenjang_peta],
                ["IPM", fmt(r.ipm, 2)],
                ["Rata-rata lama sekolah", f"{fmt(r.rata_lama_sekolah, 2)} tahun"],
                ["Sekolah", fmt(ukuran["sekolah"])],
                ["Guru", fmt(ukuran["guru"])],
                ["Murid", fmt(ukuran["murid"])],
                ["Murid per guru", fmt(ukuran["murid"] / ukuran["guru"], 2) if ukuran["guru"] else "–"],
            ],
        })

    html_peta = bangun_peta_html(
            wilayah_peta,
            geo,
            judul=judul_peta,
            ambang=ambang_tiga_kelas(df_all[kolom_peta]),   # ambang dari seluruh wilayah agar warna stabil saat difilter
            ipm={r.kabupaten_kota: r.ipm for r in df_all.itertuples()},
            warna_ipm=warnai_ipm,
        )
    st.caption(f"{len(wilayah_peta)} wilayah · {judul_peta} · total {fmt(df[kolom_peta].sum())}")
    components.html(html_peta, height=590)
    st.caption(
        "Penanda menampilkan data agregat kabupaten/kota. Klik penanda untuk melihat rincian. "
        "Gelembung yang berdekatan menyatu saat peta di-zoom out dan jumlahnya dijumlahkan. "
        "Batas wilayah: BPS, WFP, OCHA ROAP via geoBoundaries (CC BY 3.0 IGO). "
        "Batas dan penanda tersedia tanpa peta dasar eksternal. Penggabungan penanda hanya untuk tampilan, bukan analisis clustering."
    )

# --- Tab 1: ringkasan dan peringkat ---
with tab1:
    tertinggi = df.loc[df.ipm.idxmax()]
    terendah = df.loc[df.ipm.idxmin()]
    st.markdown(f'<div class="note">Dari <b>{len(df)} wilayah</b> terpilih, IPM tertinggi ada di '
                f'<b>{escape(nama_wilayah(tertinggi.kabupaten_kota))} ({fmt(tertinggi.ipm, 2)})</b>. '
                f'Selisih dengan {escape(nama_wilayah(terendah.kabupaten_kota))}: '
                f'<b>{fmt(tertinggi.ipm-terendah.ipm, 2)} poin</b>.</div>', unsafe_allow_html=True)
    legenda_wilayah()
    rentang_ipm_grafik = [max(0, float(df.ipm.min()) - 3), min(104, float(df.ipm.max()) + 5)]
    atas, bawah = st.columns(2)
    for col, rendah, judul, kunci in [(atas, False, "IPM tertinggi", "ipm_tertinggi"),
                                      (bawah, True, "IPM terendah", "ipm_terendah")]:
        with col, st.container(border=True, key="card_" + kunci):
            st.subheader(judul)
            st.caption(f"{min(5, len(df))} wilayah sesuai filter · arahkan kursor untuk rincian")
            tampilkan_grafik(grafik_peringkat(df, "ipm", "IPM", ascending=rendah, limit=5,
                rata=df.ipm.mean(), rentang=rentang_ipm_grafik, kompak=True), kunci)
    st.caption("Posisi titik menunjukkan IPM. Kedua grafik menggunakan rentang sumbu yang sama; garis putus-putus adalah rata-rata wilayah terpilih.")
    with st.container(border=True, key="card_peringkat"):
        st.subheader("Perbedaan antarwilayah")
        c1, c2, c3 = st.columns([2, 1, 1])
        indikator_rank = c1.selectbox("Indikator peringkat", ["IPM", "Lama sekolah", "Murid per guru", "Jumlah sekolah", "Jumlah guru", "Jumlah murid"], key="rank_indikator")
        urutan = c2.selectbox("Urutan", ["Tertinggi", "Terendah"], key="rank_urutan")
        banyak = c3.selectbox("Jumlah ditampilkan", ["10 wilayah", "20 wilayah", "Semua wilayah"], key="rank_jumlah")
        opsi = {"IPM": ("ipm", 2), "Lama sekolah": ("rata_lama_sekolah", 2),
                "Murid per guru": ("rasio_murid_guru", 2), "Jumlah sekolah": ("total_sekolah", 0),
                "Jumlah guru": ("total_guru", 0), "Jumlah murid": ("total_murid", 0)}
        kol, desimal = opsi[indikator_rank]
        limit = len(df) if banyak == "Semua wilayah" else int(banyak.split()[0])
        label = "Lama sekolah (tahun)" if indikator_rank == "Lama sekolah" else indikator_rank
        legenda_wilayah()
        with st.container(height=560 if min(limit, len(df)) > 15 else "content", border=False):
            tampilkan_grafik(grafik_peringkat(df, kol, label, ascending=urutan == "Terendah", limit=limit,
                            rata=df[kol].mean(), desimal=desimal), "peringkat_wilayah")
        st.caption(f"{min(limit, len(df))} dari {len(df)} wilayah ditampilkan. Titik lebih ke kanan berarti nilai lebih tinggi. Garis pembanding memakai rata-rata sederhana seluruh wilayah pada filter, bukan hanya daftar teratas.")
    with st.expander("Cara membaca indikator"):
        st.write("IPM merangkum kesehatan, pendidikan, dan standar hidup. Murid per guru = jumlah murid dibagi jumlah guru; bukan jumlah murid per kelas. Rata-rata rasio pada grafik memberi bobot sama pada wilayah, sedangkan KPI atas memakai total murid / total guru.")
        st.write("Header RLS lampiran memakai usia 15 tahun ke atas; RLS komponen IPM metode baru memakai usia 25 tahun ke atas. Tahun asli data sekolah/guru/murid perlu diverifikasi karena 2025 ditambahkan sebagai tahun integrasi.")

# --- Tab 2: hubungan IPM dan RLS ---
with tab2:
    st.subheader("Bagaimana IPM berkaitan dengan lama sekolah?")
    st.caption("Satu titik mewakili satu wilayah. Besar gelembung mengikuti jumlah murid.")
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
                            line=dict(color="#718298", dash="dot", width=2))
        gaya_grafik(fig, 500)
        fig.update_traces(marker=dict(line=dict(color="white", width=1.5)), selector=dict(mode="markers"))
        tampilkan_grafik(fig, "hubungan_ipm_rls")
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
    st.subheader("Distribusi murid dan guru")
    st.caption("Rasio membantu membandingkan jumlah murid yang dilayani guru secara agregat.")
    ca, cb = st.columns([2, 1])
    jenjang = ca.radio("Jenjang rasio", ["Semua", "SD", "SMP", "SMA"], horizontal=True, key="rasio_jenjang")
    semua_rasio = cb.checkbox("Tampilkan seluruh wilayah", key="rasio_semua")
    kolom = {"Semua": "rasio_murid_guru", "SD": "rasio_murid_guru_sd",
             "SMP": "rasio_murid_guru_smp", "SMA": "rasio_murid_guru_sma"}[jenjang]
    c1, c2 = st.columns(2)
    with c1, st.container(border=True, key="card_rasio"):
        st.subheader("Murid per guru")
        st.caption("Nilai tertinggi · " + jenjang)
        legenda_wilayah()
        with st.container(height=500, border=False):
            tampilkan_grafik(grafik_peringkat(df, kolom, "Murid per guru", limit=len(df) if semua_rasio else 12,
                                             rata=df[kolom].mean()), "peringkat_rasio")
    with c2, st.container(border=True, key="card_kepadatan"):
        st.subheader("Kepadatan sekolah & IPM")
        st.caption("Murid per sekolah · seluruh SD, SMP, SMA")
        fig = px.scatter(df, x="murid_per_sekolah", y="ipm", color="jenis_wilayah", size="total_murid",
            size_max=32, hover_name="kabupaten_kota", color_discrete_map=WARNA_JENIS,
            labels={"murid_per_sekolah":"Murid per sekolah", "ipm":"IPM", "jenis_wilayah":"Jenis", "total_murid":"Jumlah murid"})
        gaya_grafik(fig, 500)
        fig.update_traces(marker=dict(line=dict(color="white", width=1.5), opacity=.85))
        tampilkan_grafik(fig, "kepadatan_ipm")
    st.caption("Rasio tinggi bukan kesimpulan tentang mutu mengajar atau kebutuhan guru. Penilaian lebih lanjut membutuhkan data kelas, mata pelajaran, dan distribusi sekolah.")

# --- Tab 4: jenjang ---
with tab4:
    st.subheader("Komposisi pendidikan menurut jenjang")
    st.caption("Jumlah dan persentase SD, SMP, SMA pada wilayah terpilih.")
    total = pd.DataFrame({
        "Jenjang": ["SD", "SMP", "SMA"] * 3,
        "Kategori": ["Sekolah"] * 3 + ["Guru"] * 3 + ["Murid"] * 3,
        "Jumlah": [df[f"{ukuran}_{jenjang}"].sum() for ukuran in ("sekolah", "guru", "murid") for jenjang in ("sd", "smp", "sma")],
    })
    for col, kat in zip(st.columns(3), ["Sekolah", "Guru", "Murid"]):
        with col, st.container(border=True, key="card_komposisi_" + kat):
            st.subheader(kat)
            tampilkan_grafik(grafik_donut(total, kat), "komposisi_" + kat.lower())
    with st.container(border=True, key="card_transisi"):
        st.subheader("Perbandingan jumlah murid SMA dan SD")
        st.caption("Murid SMA ÷ murid SD × 100% · bukan angka putus sekolah")
        semua_jenjang = st.checkbox("Tampilkan semua wilayah", key="jenjang_semua")
        legenda_wilayah()
        with st.container(height=500, border=False):
            tampilkan_grafik(grafik_peringkat(df, "persen_sma_thd_sd", "Murid SMA / murid SD (%)",
                desimal=1, limit=len(df) if semua_jenjang else 12), "perbandingan_sma_sd")
    st.caption("Siswa SD dan SMA merupakan kelompok berbeda. Dataset tidak melacak transisi kohort; rasio ini tidak mengukur putus sekolah.")

with tab_compare:
    st.subheader("Dua daerah, dua gambaran")
    st.caption("Pilihan daerah di tab ini terpisah dari filter sidebar. Data mencakup SD, SMP, dan SMA.")
    choices = sorted(df_all.kabupaten_kota.unique())
    c1, c2 = st.columns(2)
    a = c1.selectbox("Daerah pertama", choices, index=choices.index("Kota Surabaya"), format_func=nama_wilayah)
    b = c2.selectbox("Daerah kedua", choices, index=choices.index("Sampang"), format_func=nama_wilayah)
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
    st.subheader("Status sumber data")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f'<div class="status"><small>Sumber yang sedang digunakan</small><strong>{escape(SUMBER)} · aktif</strong><p>{len(df_all)} wilayah berhasil dibaca. Grafik dan peta memakai sumber ini.</p></div>', unsafe_allow_html=True)
    with sc2:
        if STATUS_CLOUD == "aktif":
            kelas, label_cloud, ket_cloud = "", "MotherDuck · terhubung", "Koneksi cloud berhasil dan tabel sumber dapat dibaca."
        elif STATUS_CLOUD == "tidak_tersambung":
            kelas, label_cloud, ket_cloud = "warning", "MotherDuck · belum tersambung", "Koneksi yang dikonfigurasi belum berhasil. Dashboard menggunakan sumber lokal yang tertera di sebelah."
        elif STATUS_CLOUD == "nonaktif":
            kelas, label_cloud, ket_cloud = "neutral", "MotherDuck · opsional", "Mode lokal digunakan. Koneksi cloud tidak dijalankan otomatis."
        else:
            kelas, label_cloud, ket_cloud = "neutral", "MotherDuck · opsional", "Belum dikonfigurasi. Dashboard tetap berjalan menggunakan data lokal."
        st.markdown(f'<div class="status {kelas}"><small>Koneksi cloud</small><strong>{label_cloud}</strong><p>{ket_cloud}</p></div>', unsafe_allow_html=True)
    with st.expander("Tentang koneksi MotherDuck"):
        st.write("Mode awal memakai data lokal. Untuk menggunakan cloud, aktifkan DASHBOARD_ENABLE_MOTHERDUCK=1 sebelum menjalankan aplikasi dan simpan token pada Streamlit secrets atau environment MOTHERDUCK_TOKEN. Status terhubung hanya muncul setelah koneksi dan pembacaan tabel berhasil.")
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
| 7. Visualisasi | Streamlit membaca MotherDuck, warehouse DuckDB lokal, atau CSV cadangan | Dashboard ini |
"""
    )
    st.caption(f"Sumber data aktif: {SUMBER}. Mode CSV menjalankan analisis snapshot melalui DuckDB, tanpa membaca DuckLake secara langsung.")
    st.write("Satu baris = satu wilayah pada satu tahun. Memilih jenis wilayah adalah slice. Memilih wilayah dengan rentang IPM adalah dice. Menjumlahkan sekolah/guru/murid adalah agregasi. Data satu tahun belum menyediakan tren tahunan.")
    st.caption("URL tabel sumber, tahun asal data pendidikan, dan cakupan sekolah perlu dilengkapi dari sumber asli. Hasil di atas bersifat deskriptif.")
