# Pemeriksaan hasil

Tanggal: 14 Oktober 2026.

## Lulus

- CSV terintegrasi direkonsiliasi ulang terhadap seluruh nilai dalam tiga Excel. Hasil cocok persis setelah tahun integrasi 2025 ditambahkan sesuai notebook. Join one-to-one berhasil.
- 38 wilayah unik, 29 kabupaten dan 9 kota, tanpa nilai kosong atau baris duplikat.
- Total sekolah 25.521, guru 294.886, dan murid 4.282.023. Total per jenjang juga diperiksa.
- Rata-rata IPM 76,06447368421051, RLS 8,941315789473686, dan korelasi Pearson 0,97963430749045 cocok dengan perhitungan Python dan output notebook.
- Penghitungan JavaScript diuji terhadap total dan statistik referensi. Rasio gabungan memakai total murid dibagi total guru.
- Model DOM memeriksa perubahan filter, hasil kosong, reset, batas rentang IPM, perbandingan independen dari filter, pilihan daerah yang sama, navigasi tab dan presentasi, serta jalur unduh CSV.
- JavaScript lolos pemeriksaan syntax Node. app.py dan builder lolos pemeriksaan syntax Python.
- Dataset di index.html disematkan dan sama dengan CSV. Tidak ada dependensi aset eksternal untuk membuka versi web.

## Batas verifikasi

Layout, rendering SVG/CSS, dan interaksi pada browser nyata belum diuji di lingkungan ini. Tes model DOM memeriksa logika UI, bukan tampilan aktual atau perilaku browser secara menyeluruh.

UI Streamlit belum dijalankan karena paket Streamlit tidak tersedia di lingkungan pemeriksaan. Koneksi MotherDuck, ekstensi DuckLake, serta eksekusi ulang seluruh notebook tidak diuji. Publikasi GitHub/Pages belum dilakukan. URL tabel sumber dan tahun asli data pendidikan belum diverifikasi.

## Pembaruan database fisik

DuckDB 1.4.1 tersedia dalam lingkungan pemeriksaan terpisah. Tiga database sumber dan satu warehouse gabungan berhasil dibuat dari Excel. Semua file ditutup, dibuka ulang read-only, dan tabel serta jumlah barisnya diperiksa. View warehouse cocok dengan CSV pada seluruh 13 kolom dan 38 baris. SHA-256 dan daftar tabel tersimpan dalam database/manifest.json. Database fisik disertakan, bukan file kosong atau hasil mengganti ekstensi.

Fungsi pembacaan data aktual pada app.py diuji dengan DuckDB lokal, tanpa menjalankan UI Streamlit. Hasilnya 38 wilayah dengan total yang sesuai.

Untuk pengecekan akhir di perangkat demonstrasi: buka index.html, pilih Kota, pilih SD, cari Surabaya, klik Mode presentasi, pindah bagian, bandingkan dua daerah, dan unduh CSV. Coba juga pada layar proyektor atau monitor fakultas.
