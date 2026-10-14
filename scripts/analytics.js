(function(root) {
  'use strict';
  const LEVELS = ['sd', 'smp', 'sma'];
  const sum = (rows, key) => rows.reduce((n, r) => n + r[key], 0);
  const ratio = (a, b) => b > 0 ? a / b : null;
  function enrich(rows) {
    return rows.map(row => {
      const r = {...row, jenis_wilayah: row.kabupaten_kota.startsWith('Kota ') ? 'Kota' : 'Kabupaten'};
      for (const metric of ['sekolah', 'guru', 'murid']) r['total_' + metric] = LEVELS.reduce((n, level) => n + r[metric + '_' + level], 0);
      return r;
    });
  }
  function measures(r, level = 'semua') {
    const key = metric => level === 'semua' ? 'total_' + metric : metric + '_' + level;
    return {sekolah: r[key('sekolah')], guru: r[key('guru')], murid: r[key('murid')],
      rasio: ratio(r[key('murid')], r[key('guru')]), kepadatan: ratio(r[key('murid')], r[key('sekolah')])};
  }
  function filter(rows, state) {
    const search = (state.search || '').trim().toLocaleLowerCase('id');
    return rows.filter(r => (!state.type || state.type === 'semua' || r.jenis_wilayah === state.type)
      && r.ipm >= state.min && r.ipm <= state.max
      && r.kabupaten_kota.toLocaleLowerCase('id').includes(search));
  }
  function summary(rows, level = 'semua') {
    const totals = rows.reduce((a,r) => {
      const m = measures(r, level);
      for (const k of ['sekolah','guru','murid']) a[k] += m[k];
      return a;
    }, {sekolah:0,guru:0,murid:0});
    return {...totals, n:rows.length, ipm:rows.length ? sum(rows,'ipm')/rows.length : null,
      rls:rows.length ? sum(rows,'rata_lama_sekolah')/rows.length : null,
      rasio:ratio(totals.murid,totals.guru), kepadatan:ratio(totals.murid,totals.sekolah)};
  }
  function corr(rows, x='rata_lama_sekolah', y='ipm') {
    if (rows.length < 3) return null;
    const mx=sum(rows,x)/rows.length, my=sum(rows,y)/rows.length;
    let xx=0,yy=0,xy=0;
    for(const r of rows){const dx=r[x]-mx,dy=r[y]-my;xx+=dx*dx;yy+=dy*dy;xy+=dx*dy;}
    return xx>0 && yy>0 ? xy/Math.sqrt(xx*yy) : null;
  }
  function csv(rows, level = 'semua') {
    const keys=['kabupaten_kota','tahun','jenis_wilayah','ipm','rata_lama_sekolah','sekolah_sd','sekolah_smp','sekolah_sma','guru_sd','guru_smp','guru_sma','murid_sd','murid_smp','murid_sma'];
    const more=['jenjang_dipilih','sekolah_dipilih','guru_dipilih','murid_dipilih','murid_per_guru','murid_per_sekolah'];
    const quote=v=>'"'+String(v == null ? '' : v).replace(/"/g,'""')+'"';
    const lines=[keys.concat(more).map(quote).join(',')];
    for(const r of rows){const m=measures(r,level); lines.push(keys.map(k=>r[k]).concat([level,m.sekolah,m.guru,m.murid,m.rasio,m.kepadatan]).map(quote).join(','));}
    return '\ufeff'+lines.join('\r\n');
  }
  const api={enrich,measures,filter,summary,corr,csv,LEVELS};
  if(typeof module==='object' && module.exports) module.exports=api;
  root.JatimAnalytics=api;
})(typeof globalThis!=='undefined' ? globalThis : this);
