# Dashboard Pendidikan Jawa Timur

Dashboard interaktif untuk mendemonstrasikan hasil tugas data warehousing kepada orang awam. Data lampiran mencakup 38 kabupaten/kota. Tahun integrasi adalah 2025.

## Membuka dashboard sekarang

Buka `index.html` dengan Chrome, Edge, atau Firefox. Semua grafik, data, dan aset sudah ada dalam file ini. Tidak perlu menginstal Python atau terhubung ke internet untuk demonstrasi. Versi web memakai snapshot dataset terintegrasi, bukan koneksi langsung ke warehouse.

## Publikasi ke GitHub Pages

1. Ekstrak paket ini. Buat repository GitHub, misalnya `dashboard-pendidikan-jatim`.
2. Unggah isi folder proyek ke repository, bukan file ZIP. Pastikan `index.html` berada di root repository.
3. Buka **Settings > Pages**. Pilih **Deploy from a branch**.
4. Pilih branch **main** dan folder **/(root)**, lalu **Save**.
5. Tunggu proses publikasi selesai. GitHub menampilkan alamat dashboard pada halaman Pages. URL umumnya mengikuti pola `https://NAMA-PENGGUNA.github.io/NAMA-REPOSITORY/`.

GitHub Pages menjalankan versi HTML/CSS/JavaScript. Aplikasi Python Streamlit memerlukan runtime terpisah. Repository GitHub menyimpan source code, sedangkan GitHub Pages menayangkan `index.html`. Tidak ada publikasi otomatis yang sudah dilakukan oleh pembuat paket ini.

Rujukan resmi: [pengaturan sumber GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Alur demonstrasi sekitar 5 menit

1. Buka Ringkasan hasil. Jelaskan cakupan 38 daerah serta jumlah sekolah, guru, dan murid.
2. Tunjukkan selisih IPM tertinggi dan terendah. IPM yang lebih tinggi menggambarkan capaian pembangunan manusia lebih tinggi.
3. Buka Jelajah wilayah. Pilih Murid per guru lalu ubah jenjang ke SD atau SMA. Jelaskan rasio sebagai perbandingan jumlah, bukan ukuran murid per kelas.
4. Klik daerah pada grafik atau buka Bandingkan daerah. Bandingkan Kota Surabaya dengan Sampang, lalu pilih daerah lain sesuai pertanyaan audiens.
5. Buka Data dan proses. Jelaskan bahwa data warehousing menyatukan sumber yang terpisah. Tunjukkan tabel hasil, proses integrasi, dan status koneksi cloud.

Klik Mode presentasi untuk menyembunyikan sidebar dan memakai navigasi empat bagian. Tombol panah kiri/kanan berpindah bagian saat fokus tidak berada di kontrol. Escape mengakhiri mode presentasi. Unduh data mengekspor hasil yang mengikuti filter. Untuk mengubah filter saat presentasi, keluar dari mode presentasi lebih dulu.

## Menjalankan Streamlit

Gunakan Python 3.10 atau lebih baru, buat virtual environment, lalu jalankan:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Di Windows, gunakan lingkungan Python/venv yang biasa digunakan. Versi Streamlit memprioritaskan `database/warehouse_jatim.duckdb` bila koneksi MotherDuck tidak tersedia. Jika file warehouse tidak ada, aplikasi memakai `data/indikator_jatim.csv`. Database dan CSV sudah disertakan pada lokasi yang sesuai.

Untuk hosting Streamlit, unggah proyek ke GitHub lalu di Streamlit Community Cloud pilih repository, branch, dan file utama `app.py`. [Panduan resmi](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

### MotherDuck opsional

Opsi ini hanya bekerja jika database `jatim_dw` dan tabel `fact_indikator_pendidikan` sudah tersedia dengan kolom nama wilayah, tahun, IPM, RLS, serta sekolah/guru/murid SD/SMP/SMA. Publikasi MotherDuck belum ada pada notebook lampiran. Jangan menyatakan dashboard sudah membaca cloud hanya karena source code menyiapkan koneksi.

Simpan token melalui Streamlit secrets atau environment `MOTHERDUCK_TOKEN`. Jangan unggah token ke repository. `.streamlit/secrets.toml` sudah masuk daftar ignore. Jika koneksi gagal, aplikasi beralih ke CSV tanpa menampilkan detail exception koneksi.

## Susunan proyek

| Lokasi | Isi |
| --- | --- |
| `index.html` | Dashboard web mandiri untuk demonstrasi dan GitHub Pages |
| `app.py` | Versi Streamlit yang disesuaikan dari lampiran |
| `data/indikator_jatim.csv` | Snapshot integrasi 38 wilayah dan 13 kolom |
| `database/` | Tiga database sumber, satu warehouse gabungan, dan manifest verifikasi |
| `assets/duckdb-logo.svg` | Logo DuckDB resmi dari repository duckdb/duckdb-r |
| `sumber/` | Tiga file Excel asli |
| `notebooks/DataWarehouse_Datmin.ipynb` | Notebook asli ETL DuckDB dan DuckLake |
| `scripts/` | Source HTML/CSS/JavaScript, builder, dan verifikasi web |
| `METODOLOGI.md` | Definisi ukuran, status implementasi, dan batas interpretasi |
| `VALIDASI.md` | Pemeriksaan yang benar-benar dilakukan |

## Database DuckDB per dataset

| Dataset | File database | Isi |
| --- | --- | --- |
| IPM 2025.xlsx | `database/ipm_2025.duckdb` | Tabel ipm, 38 wilayah |
| rataratalamasekolah.xlsx | `database/lama_sekolah_2025.duckdb` | Tabel rata_lama_sekolah, 38 wilayah; agregat_provinsi, 1 baris |
| dataset_integrasi_sekolah_guru_murid_jawa_timur.xlsx | `database/sekolah_guru_murid.duckdb` | jumlah_sekolah, jumlah_guru, jumlah_murid; masing-masing 38 wilayah |
| Hasil integrasi | `database/warehouse_jatim.duckdb` | Lima tabel raw, dua dimensi, tabel fakta, dan view terintegrasi |

Setiap sumber juga memiliki tabel metadata.sumber untuk mencatat asal file dan batas data. Database dibuat dengan DuckDB 1.4.1, ditutup, lalu dibuka ulang read-only untuk verifikasi. Warehouse memakai primary key dan foreign key serta menghasilkan data yang cocok dengan CSV.

Untuk membangun ulang database dari Excel, instal dependensi dashboard ditambah `openpyxl`, kemudian jalankan `python scripts/build_duckdb.py`. Script hanya mengganti file database hasil pada folder database, bukan sumber Excel.

Contoh membuka warehouse dalam Python:

```python
import duckdb
con = duckdb.connect("database/warehouse_jatim.duckdb", read_only=True)
print(con.sql("SELECT * FROM dw.v_indikator_jawa_timur LIMIT 5").df())
con.close()
```

File dapat dibuka melalui DuckDB Python, CLI, atau klien yang mendukung DuckDB. Ikon file pada Windows mengikuti aplikasi bawaan/asosiasi file dan tidak otomatis menjadi bebek karena ekstensi berubah. Logo bebek DuckDB tampil pada dashboard bagian Data dan proses. Sumber logo: https://raw.githubusercontent.com/duckdb/duckdb-r/main/man/figures/DuckDB_Logo-horizontal.svg dan https://duckdb.org/design/.

## Memperbarui versi web

Setelah mengganti CSV, jalankan `python scripts/build_web.py`. Builder menyematkan data dan source web ke `index.html`. Script saat ini memeriksa 38 wilayah sesuai cakupan tugas. Publikasikan ulang hasil `index.html` yang baru melalui repository.

Untuk verifikasi perhitungan dan interaksi model DOM, jalankan `node scripts/verify_web.cjs`. Node hanya diperlukan untuk pengembangan, bukan untuk membuka dashboard. Tes ini bukan pengganti inspeksi visual browser.

## Temuan utama dari lampiran

Total SD/SMP/SMA adalah 25.521 sekolah, 294.886 guru, dan 4.282.023 murid. IPM tertinggi adalah Kota Surabaya 85,65 dan terendah Sampang 67,23. Rata-rata IPM sederhana kota adalah 82,42 dan kabupaten 74,09.

Angka ini mencerminkan lampiran yang digunakan, belum merupakan verifikasi ulang publikasi BPS. Tahun asal data sekolah/guru/murid dan URL sumber masih perlu dilengkapi sebelum laporan akademik final.
