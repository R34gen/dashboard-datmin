"""Buat satu DuckDB per Excel dan satu warehouse gabungan dari database sumber."""
from pathlib import Path
import json
import hashlib
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'database'
OUT.mkdir(exist_ok=True)

def prepare(df, columns):
    df = df.copy()
    df.columns = columns
    df['kabupaten_kota'] = df['kabupaten_kota'].astype('string').str.strip()
    for c in columns[1:]:
        df[c] = pd.to_numeric(df[c], errors='raise')
    df['tahun'] = 2025
    assert len(df) == 38 and not df.isna().any().any()
    assert not df.duplicated(['kabupaten_kota', 'tahun']).any()
    return df

def source_db(filename, tables, source_name, note):
    path = OUT / filename
    if path.exists():
        path.unlink()
    with duckdb.connect(str(path)) as con:
        for name, df in tables.items():
            con.register('source_df', df)
            con.execute(f'CREATE TABLE {name} AS SELECT * FROM source_df')
            con.unregister('source_df')
        con.execute('CREATE SCHEMA metadata')
        con.execute('CREATE TABLE metadata.sumber (file_excel VARCHAR, tahun_integrasi INTEGER, catatan VARCHAR)')
        con.execute('INSERT INTO metadata.sumber VALUES (?, ?, ?)', [source_name, 2025, note])
        con.execute('CHECKPOINT')
    return path

ipm = prepare(pd.read_excel(ROOT/'sumber/IPM 2025.xlsx', sheet_name='IPM Jawa Timur'), ['kabupaten_kota','ipm'])
rls_raw = pd.read_excel(ROOT/'sumber/rataratalamasekolah.xlsx', header=None)
rls_raw.columns = ['kabupaten_kota','rata_lama_sekolah']
rls_raw['kabupaten_kota'] = rls_raw['kabupaten_kota'].astype('string').str.strip()
rls_raw['rata_lama_sekolah'] = pd.to_numeric(rls_raw['rata_lama_sekolah'], errors='coerce')
rls_raw = rls_raw[rls_raw.kabupaten_kota.notna() & rls_raw.rata_lama_sekolah.notna()].copy()
prov = rls_raw[rls_raw.kabupaten_kota.eq('Jawa Timur')].copy()
prov['tahun'] = 2025
rls = prepare(rls_raw[rls_raw.kabupaten_kota.ne('Jawa Timur')], ['kabupaten_kota','rata_lama_sekolah'])
edu = {}
for sheet, name in [('Jumlah Sekolah','jumlah_sekolah'),('Jumlah Guru','jumlah_guru'),('Jumlah Murid','jumlah_murid')]:
    edu[name] = prepare(pd.read_excel(ROOT/'sumber/dataset_integrasi_sekolah_guru_murid_jawa_timur.xlsx', sheet_name=sheet), ['kabupaten_kota','sd','smp','sma'])

paths = [
    source_db('ipm_2025.duckdb', {'ipm':ipm}, 'IPM 2025.xlsx', 'Tahun 2025 sesuai file lampiran. URL sumber perlu dilengkapi.'),
    source_db('lama_sekolah_2025.duckdb', {'rata_lama_sekolah':rls,'agregat_provinsi':prov}, 'rataratalamasekolah.xlsx', 'RLS usia 15+ sesuai header. Agregat provinsi dipisahkan dari 38 wilayah.'),
    source_db('sekolah_guru_murid.duckdb', edu, 'dataset_integrasi_sekolah_guru_murid_jawa_timur.xlsx', 'Tahun integrasi 2025 ditambahkan oleh notebook. Tahun sumber dan cakupan sekolah belum terverifikasi.')
]
warehouse = OUT/'warehouse_jatim.duckdb'
if warehouse.exists():
    warehouse.unlink()
with duckdb.connect(str(warehouse)) as con:
    for alias, p in zip(['src_ipm','src_rls','src_pendidikan'], paths):
        escaped = str(p).replace("'", "''")
        con.execute(f"ATTACH '{escaped}' AS {alias} (READ_ONLY)")
    con.execute('CREATE SCHEMA raw')
    con.execute('CREATE SCHEMA dw')
    for target, source in [('ipm','src_ipm.ipm'), ('rata_lama_sekolah','src_rls.rata_lama_sekolah'), ('jumlah_sekolah','src_pendidikan.jumlah_sekolah'), ('jumlah_guru','src_pendidikan.jumlah_guru'), ('jumlah_murid','src_pendidikan.jumlah_murid')]:
        con.execute(f'CREATE TABLE raw.{target} AS SELECT * FROM {source}')
    con.execute('CREATE TABLE dw.dim_wilayah(wilayah_id INTEGER PRIMARY KEY, kabupaten_kota VARCHAR UNIQUE NOT NULL, jenis_wilayah VARCHAR NOT NULL)')
    con.execute("INSERT INTO dw.dim_wilayah SELECT ROW_NUMBER() OVER (ORDER BY kabupaten_kota), kabupaten_kota, CASE WHEN kabupaten_kota LIKE 'Kota %' THEN 'Kota' ELSE 'Kabupaten' END FROM raw.ipm")
    con.execute('CREATE TABLE dw.dim_tahun(tahun_id INTEGER PRIMARY KEY, tahun INTEGER UNIQUE NOT NULL)')
    con.execute('INSERT INTO dw.dim_tahun SELECT ROW_NUMBER() OVER (ORDER BY tahun), tahun FROM (SELECT DISTINCT tahun FROM raw.ipm)')
    con.execute('''CREATE TABLE dw.fact_indikator_pendidikan(
        wilayah_id INTEGER NOT NULL REFERENCES dw.dim_wilayah(wilayah_id),
        tahun_id INTEGER NOT NULL REFERENCES dw.dim_tahun(tahun_id),
        ipm DOUBLE NOT NULL,
        sekolah_sd BIGINT NOT NULL, sekolah_smp BIGINT NOT NULL, sekolah_sma BIGINT NOT NULL,
        guru_sd BIGINT NOT NULL, guru_smp BIGINT NOT NULL, guru_sma BIGINT NOT NULL,
        murid_sd BIGINT NOT NULL, murid_smp BIGINT NOT NULL, murid_sma BIGINT NOT NULL,
        rata_lama_sekolah DOUBLE NOT NULL,
        PRIMARY KEY(wilayah_id, tahun_id))''')
    con.execute('''INSERT INTO dw.fact_indikator_pendidikan
        SELECT w.wilayah_id,t.tahun_id,i.ipm,s.sd,s.smp,s.sma,g.sd,g.smp,g.sma,m.sd,m.smp,m.sma,r.rata_lama_sekolah
        FROM raw.ipm i JOIN dw.dim_wilayah w USING(kabupaten_kota)
        JOIN dw.dim_tahun t USING(tahun)
        JOIN raw.jumlah_sekolah s USING(kabupaten_kota,tahun)
        JOIN raw.jumlah_guru g USING(kabupaten_kota,tahun)
        JOIN raw.jumlah_murid m USING(kabupaten_kota,tahun)
        JOIN raw.rata_lama_sekolah r USING(kabupaten_kota,tahun)''')
    con.execute('''CREATE VIEW dw.v_indikator_jawa_timur AS SELECT
        w.kabupaten_kota,t.tahun,f.ipm,
        f.sekolah_sd,f.sekolah_smp,f.sekolah_sma,
        f.guru_sd,f.guru_smp,f.guru_sma,
        f.murid_sd,f.murid_smp,f.murid_sma,f.rata_lama_sekolah,
        w.jenis_wilayah,
        f.sekolah_sd+f.sekolah_smp+f.sekolah_sma AS total_sekolah,
        f.guru_sd+f.guru_smp+f.guru_sma AS total_guru,
        f.murid_sd+f.murid_smp+f.murid_sma AS total_murid
        FROM dw.fact_indikator_pendidikan f JOIN dw.dim_wilayah w USING(wilayah_id)
        JOIN dw.dim_tahun t USING(tahun_id)''')
    assert con.execute('SELECT COUNT(*) FROM dw.fact_indikator_pendidikan').fetchone()[0] == 38
    for alias in ['src_ipm','src_rls','src_pendidikan']:
        con.execute(f'DETACH {alias}')
    con.execute('CHECKPOINT')

# Tutup, buka ulang read-only, lalu cocokkan isi persisted database dengan CSV.
expected = pd.read_csv(ROOT/'data/indikator_jatim.csv').sort_values('kabupaten_kota').reset_index(drop=True)
with duckdb.connect(str(warehouse), read_only=True) as con:
    actual = con.execute('SELECT * FROM dw.v_indikator_jawa_timur ORDER BY kabupaten_kota').df()
    pd.testing.assert_frame_equal(actual[expected.columns], expected, check_dtype=False)
    totals = con.execute('SELECT SUM(total_sekolah), SUM(total_guru), SUM(total_murid) FROM dw.v_indikator_jawa_timur').fetchone()
    assert totals == (25521,294886,4282023)

report = []
for p in paths + [warehouse]:
    with duckdb.connect(str(p), read_only=True) as con:
        counts = {}
        for schema, table in con.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_type='BASE TABLE' ORDER BY 1,2").fetchall():
            counts[schema+'.'+table] = con.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"').fetchone()[0]
    report.append({'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'tables':counts})
(OUT/'manifest.json').write_text(json.dumps({'duckdb_version':duckdb.__version__,'files':report,'warehouse_totals':totals},indent=2),encoding='utf-8')
print(json.dumps({'version':duckdb.__version__,'files':report,'totals':totals},indent=2))
