# Metodologi dan batas pembacaan

## Data dan grain

Tiga workbook menghasilkan lima tabel bersih, masing-masing 38 wilayah: IPM, RLS, sekolah, guru, dan murid. Satu baris tabel fakta mewakili satu kabupaten/kota pada satu tahun. Tahun integrasi 2025 ditambahkan notebook. File IPM dan RLS menunjukkan tahun 2025, sedangkan tahun asli sekolah/guru/murid belum terdokumentasi pada header.

Nama wilayah dibersihkan dari spasi di awal/akhir. Angka dikonversi menjadi numerik. Header, baris kosong, dan agregat Jawa Timur di file RLS tidak dimasukkan sebagai wilayah. Join memakai nama wilayah dan tahun. Tabel IPM menjadi basis LEFT JOIN di notebook.

## Arsitektur

Notebook membangun lima tabel schema raw pada DuckDB. Schema dw memiliki dim_wilayah, dim_tahun, dan fact_indikator_pendidikan. Jenjang masih disimpan sebagai kolom, bukan dim_jenjang. View terintegrasi menambahkan nama wilayah, tahun, dan total ukuran. DuckLake menyimpan salinan view terintegrasi yang denormalisasi serta dua tabel dimensi.

Dashboard HTML membaca snapshot dari CSV yang disematkan melalui scripts/build_web.py. Penghitungan berlangsung di browser. Dashboard Streamlit membaca tabel MotherDuck bila token dan tabel tersedia, lalu memprioritaskan file warehouse DuckDB lokal bila koneksi cloud tidak tersedia. CSV dipakai hanya jika file warehouse tidak ada. Notebook belum menyediakan proses publikasi MotherDuck.

Paket terbaru menyediakan tiga database sumber, satu per file Excel: ipm_2025.duckdb, lama_sekolah_2025.duckdb, dan sekolah_guru_murid.duckdb. Tiga sheet sekolah/guru/murid disimpan sebagai tiga tabel dalam satu file. warehouse_jatim.duckdb mengintegrasikan data dari ketiga database tersebut. Builder baru menambahkan primary key dan foreign key pada star schema warehouse. Notebook asli tetap disertakan sebagai sumber awal.

## Rumus

| Ukuran | Perhitungan |
| --- | --- |
| Total sekolah/guru/murid semua jenjang | Jumlah kolom SD + SMP + SMA untuk wilayah terpilih |
| Total untuk jenjang tertentu | Jumlah kolom jenjang terpilih untuk wilayah terpilih |
| Rata-rata IPM antarwilayah | Jumlah IPM / banyak wilayah terpilih |
| Rata-rata RLS antarwilayah | Jumlah RLS / banyak wilayah terpilih |
| Murid per guru gabungan | Total murid terpilih / total guru terpilih |
| Murid per sekolah gabungan | Total murid terpilih / total sekolah terpilih |
| Selisih IPM dua daerah | IPM daerah pertama dikurangi IPM daerah kedua |
| Korelasi | Korelasi Pearson IPM dan RLS antarwilayah terpilih, minimal 3 wilayah dan kedua variabel bervariasi |

Jika penyebut rasio nol, tampilkan nilai tidak tersedia. Rasio gabungan dihitung dari jumlah, bukan rata-rata sederhana rasio tiap wilayah. Nilai dihitung dengan presisi penuh dan dibulatkan hanya untuk tampilan.

## Pembacaan untuk audiens umum

IPM mengukur capaian pembangunan manusia melalui kesehatan, pendidikan, dan standar hidup. Metode baru memakai RLS penduduk usia 25 tahun ke atas. [BPS, Booklet IPM Metode Baru](https://searchengine.web.bps.go.id/filemenu/Booklet-IPM-Metode-Baru.pdf).

Header RLS lampiran menyebut penduduk usia 15 tahun ke atas. Karena kelompok umur berbeda, RLS lampiran tidak boleh langsung disebut identik dengan RLS komponen IPM. Korelasi 0,9796 pada seluruh wilayah menunjukkan hubungan statistik yang kuat, tetapi tidak membuktikan pengaruh atau sebab-akibat.

Rata-rata IPM 76,0645 dan RLS 8,9413 adalah rata-rata sederhana 38 kabupaten/kota. Angka tersebut bukan agregat resmi provinsi. Agregat RLS Jawa Timur pada workbook adalah 8,81 tahun.

Murid per guru menggambarkan perbandingan jumlah secara agregat. Rasio lebih tinggi dapat digunakan sebagai petunjuk awal untuk menelaah ketersediaan guru, tetapi tidak langsung mengukur beban kelas, kebutuhan guru, atau mutu pendidikan. Penentuan kebutuhan membutuhkan jumlah kelas, mata pelajaran, jam mengajar, dan distribusi sekolah.

Perbedaan jumlah murid lintas jenjang tidak mengukur angka putus sekolah atau tingkat transisi siswa. Dataset tidak melacak kohort siswa. Jumlah jenjang yang disajikan terbatas pada SD, SMP, dan SMA sesuai kolom lampiran, tanpa asumsi cakupan SMK/madrasah/negeri/swasta.

## Operasi analisis

Filter jenis wilayah merupakan contoh slice. Kombinasi jenis wilayah, nama, dan rentang IPM merupakan dice. Agregasi menggabungkan jumlah sekolah/guru/murid. Berpindah dari semua jenjang ke SD menyeleksi kolom ukuran. Ini bukan dimensi jenjang tersendiri dalam star schema yang sekarang. Tidak ada tren tahunan atau drill-down waktu karena hanya satu tahun data.

## Informasi sumber yang belum lengkap

URL tabel BPS asli untuk nilai IPM dan RLS belum tersedia pada lampiran. Tahun asli sekolah/guru/murid, cakupan sekolah, serta sumber publiknya perlu dicatat. Tiga workbook adalah tiga input file, bukan bukti bahwa tiga penerbit sumber telah diverifikasi. Jangan mengubah nilai lampiran untuk menyesuaikan dugaan sumber.
