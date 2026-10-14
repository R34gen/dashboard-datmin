(function() {
  'use strict';
  const A=JatimAnalytics;
  const all=A.enrich(JSON.parse(document.getElementById('dataset').textContent));
  const $=id=>document.getElementById(id);
  const fmt=(x,d=0)=>x==null||!Number.isFinite(x)?'—':new Intl.NumberFormat('id-ID',{minimumFractionDigits:d,maximumFractionDigits:d}).format(x);
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const color=r=>r.jenis_wilayah==='Kota'?'var(--blue)':'var(--orange)';
  const titleNames=['Ringkasan hasil','Jelajah wilayah','Bandingkan daerah','Data dan proses'];
  let active=0, presenting=false, rows=all, state={type:'semua',level:'semua',search:'',min:0,max:100};
  const levelName=()=>state.level==='semua'?'SD, SMP, dan SMA':state.level.toUpperCase();
  const metricValue=(r,k)=>['rasio','kepadatan'].includes(k)?A.measures(r,state.level)[k]:r[k];
  const labels={ipm:'IPM',rata_lama_sekolah:'Lama sekolah (tahun)',rasio:'Murid per guru',kepadatan:'Murid per sekolah'};
  function bars(data,key='ipm',max=null){
    const limit=max || Math.max(...data.map(r=>metricValue(r,key)).filter(Number.isFinite),1);
    return '<div class="bars">'+data.map(r=>{
      const val=metricValue(r,key); const width=val==null?0:Math.max(0,Math.min(100,val/limit*100));
      return `<button class="bar-row" data-region="${esc(r.kabupaten_kota)}" aria-label="Bandingkan ${esc(r.kabupaten_kota)}, ${esc(labels[key])} ${fmt(val,2)}"><span class="bar-label">${esc(r.kabupaten_kota)}</span><span class="track"><span class="fill" style="display:block;width:${width}%;background:${color(r)}"></span></span><span class="bar-num">${fmt(val,key==='kepadatan'?1:2)}</span></button>`;
    }).join('')+'</div>';
  }
  function overview(){
    if(!rows.length){$('overview').innerHTML='';return;}
    const s=A.summary(rows,state.level), ranked=[...rows].sort((a,b)=>b.ipm-a.ipm), hi=ranked[0],lo=ranked[ranked.length-1];
    const gap=hi.ipm-lo.ipm;
    const stat=(label,value,foot)=>`<article class="card"><div class="card-label">${label}</div><div class="card-value">${value}</div><div class="card-foot">${foot}</div></article>`;
    const groups=['Kota','Kabupaten'].map(type=>{
      const subset=rows.filter(r=>r.jenis_wilayah===type),t=A.summary(subset,state.level);
      return `<div class="group-card"><h3>${type}</h3><div class="group-value">${fmt(t.ipm,2)}</div><p>Rata-rata IPM dari ${subset.length} ${type.toLowerCase()}</p></div>`;
    }).join('');
    const lc=rows.filter(r=>r.jenis_wilayah==='Kota'),lk=rows.filter(r=>r.jenis_wilayah==='Kabupaten');
    const g=lc.length&&lk.length?A.summary(lc).ipm-A.summary(lk).ipm:null;
    let story=rows.length>1?`Selisih IPM tertinggi dan terendah mencapai ${fmt(gap,2)} poin.`:`Menampilkan ${esc(hi.kabupaten_kota)}.`;
    let desc=rows.length>1?`${esc(hi.kabupaten_kota)} memiliki IPM ${fmt(hi.ipm,2)}, sementara ${esc(lo.kabupaten_kota)} ${fmt(lo.ipm,2)}. Perbandingan ini mengikuti wilayah yang sedang dipilih.`:`IPM ${fmt(hi.ipm,2)} dan lama sekolah ${fmt(hi.rata_lama_sekolah,2)} tahun. Buka bagian perbandingan untuk melihat daerah lain.`;
    $('overview').innerHTML=`<div class="cards">${stat('Wilayah ditampilkan',fmt(s.n),'Dari 38 kabupaten/kota')}${stat('Sekolah',fmt(s.sekolah),levelName())}${stat('Guru',fmt(s.guru),levelName())}${stat('Murid',fmt(s.murid),levelName())}</div>
      <div class="story"><div><h2>${story}</h2><p>${desc}</p></div><div class="big-stat">${fmt(gap,2)}<small>poin selisih IPM</small></div></div>
      <div class="three"><article class="card card-accent"><div class="card-label">Rata-rata IPM antardaerah</div><div class="card-value">${fmt(s.ipm,2)}</div><div class="card-foot">Rata-rata sederhana wilayah terpilih</div></article><article class="card card-accent"><div class="card-label">Rata-rata lama sekolah antardaerah</div><div class="card-value">${fmt(s.rls,2)} <span style="font-size:15px">tahun</span></div><div class="card-foot">RLS usia 15+ sesuai header lampiran</div></article><article class="card card-accent"><div class="card-label">Murid per guru, ${levelName()}</div><div class="card-value">${fmt(s.rasio,1)}</div><div class="card-foot">Total murid ÷ total guru wilayah terpilih</div></article></div>
      <p class="note" style="margin-bottom:20px">Rata-rata antardaerah memberi bobot yang sama pada setiap wilayah. Angka ini berbeda dari agregat resmi provinsi.</p>
      <div class="two"><article class="panel"><div class="panel-head"><div><h2>IPM tertinggi</h2><p class="sub">Hingga 5 wilayah sesuai filter</p></div><div class="legend"><span><i class="dot city"></i>Kota</span><span><i class="dot regency"></i>Kabupaten</span></div></div>${bars(ranked.slice(0,5),'ipm',100)}<p class="note">Panjang batang memakai skala IPM 0–100.</p></article><article class="panel"><div class="panel-head"><div><h2>IPM terendah</h2><p class="sub">Hingga 5 wilayah sesuai filter</p></div></div>${bars([...ranked].reverse().slice(0,5),'ipm',100)}<p class="note">Klik nama daerah untuk membuka perbandingan.</p></article></div>
      <div class="two"><article class="panel"><h2>Gambaran kota dan kabupaten</h2><p class="sub" style="margin-bottom:16px">Rata-rata IPM per kelompok, mengikuti filter</p><div class="two" style="grid-template-columns:1fr 1fr;gap:12px">${groups}</div><div class="callout">${g==null?'Pilih kota dan kabupaten untuk membandingkan kedua kelompok.':`Rata-rata IPM kota ${g>=0?'lebih tinggi':'lebih rendah'} ${fmt(Math.abs(g),2)} poin dari kabupaten. Ini adalah gambaran kelompok daerah terpilih.`}</div></article>
      <article class="panel"><h2>Bagaimana membaca angka?</h2><div class="definitions" style="margin-top:15px"><div class="definition"><b>IPM</b>Indeks yang merangkum kesehatan, pendidikan, dan standar hidup. Angka yang lebih tinggi menunjukkan capaian pembangunan manusia yang lebih tinggi.</div><div class="definition"><b>Lama sekolah</b>Rata-rata tahun pendidikan formal yang dijalani penduduk. Kelompok umur mengikuti definisi dataset.</div><div class="definition"><b>Murid per guru</b>Contoh: 15 berarti ada sekitar 15 murid untuk setiap guru secara agregat. Angka ini bukan jumlah murid per kelas.</div><div class="definition"><b>Murid per sekolah</b>Total murid dibagi jumlah sekolah. Ukuran rata-rata sekolah ini belum menjelaskan kapasitas ruang kelas.</div></div></article></div>`;
  }
  function ranking(){
    const key=$('metric').value;
    const sorted=[...rows].sort((a,b)=>(metricValue(b,key)??-Infinity)-(metricValue(a,key)??-Infinity));
    $('ranking').innerHTML=`<div style="max-height:610px;overflow:auto;padding-right:8px">${bars(sorted,key,key==='ipm'?100:null)}</div><p class="note">${esc(labels[key])}${['rasio','kepadatan'].includes(key)?', jenjang '+levelName():''}. Urut dari nilai tertinggi. Rasio yang lebih tinggi belum menentukan mutu pendidikan.</p>`;
  }
  function scatter(){
    if(!rows.length){$('scatter').innerHTML='';$('correlation').textContent='';return;}
    const W=760,H=355,L=65,R=24,T=22,B=55;
    let xmin=Math.floor(Math.min(...rows.map(r=>r.rata_lama_sekolah))),xmax=Math.ceil(Math.max(...rows.map(r=>r.rata_lama_sekolah)));
    let ymin=Math.floor(Math.min(...rows.map(r=>r.ipm))/5)*5,ymax=Math.ceil(Math.max(...rows.map(r=>r.ipm))/5)*5;
    if(xmin===xmax){xmin-=1;xmax+=1;} if(ymin===ymax){ymin-=5;ymax+=5;}
    const x=v=>L+(v-xmin)/(xmax-xmin)*(W-L-R),y=v=>H-B-(v-ymin)/(ymax-ymin)*(H-T-B);
    let out=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Diagram titik lama sekolah dan IPM pada ${rows.length} wilayah"><text x="${L}" y="13" fill="#607086" font-size="11">IPM</text>`;
    for(let i=0;i<=4;i++){
      const yy=ymin+(ymax-ymin)*i/4,xx=xmin+(xmax-xmin)*i/4;
      out+=`<line x1="${L}" x2="${W-R}" y1="${y(yy)}" y2="${y(yy)}" stroke="#e4e9f0"/><text x="${L-12}" y="${y(yy)+4}" text-anchor="end" font-size="11" fill="#607086">${fmt(yy,1)}</text><text x="${x(xx)}" y="${H-B+24}" text-anchor="middle" font-size="11" fill="#607086">${fmt(xx,1)}</text>`;
    }
    for(const r of rows){const name=esc(r.kabupaten_kota),label=`${name}: lama sekolah ${fmt(r.rata_lama_sekolah,2)} tahun, IPM ${fmt(r.ipm,2)}`;out+=`<circle cx="${x(r.rata_lama_sekolah)}" cy="${y(r.ipm)}" r="6.5" fill="${color(r)}" opacity=".85" stroke="white" stroke-width="1.5" tabindex="0" role="button" data-region="${name}" aria-label="Bandingkan ${label}"><title>${label}</title></circle>`;}
    out+=`<text x="${(W+L-R)/2}" y="${H-8}" text-anchor="middle" font-size="12" fill="#607086">Lama sekolah (tahun, usia 15+ pada lampiran)</text></svg>`;
    $('scatter').innerHTML=out;
    const r=A.corr(rows);
    $('correlation').textContent=r==null?'Korelasi tidak ditampilkan. Diperlukan minimal 3 wilayah dengan variasi nilai pada kedua indikator.':`Korelasi ${fmt(r,3)}. ${r>=.7?'Pada daerah terpilih, lama sekolah yang lebih tinggi cenderung sejalan dengan IPM yang lebih tinggi.':r<=-.7?'Pada daerah terpilih, lama sekolah yang lebih tinggi cenderung sejalan dengan IPM yang lebih rendah.':'Hubungan kedua indikator tidak kuat pada daerah terpilih.'} Perbandingan ini bersifat deskriptif.`;
  }
  function compare(){
    const a=all.find(r=>r.kabupaten_kota===$('compare-a').value),b=all.find(r=>r.kabupaten_kota===$('compare-b').value);
    const col=r=>{const m=A.measures(r,state.level);return `<article class="group-card"><div class="compare-header"><h2>${esc(r.kabupaten_kota)}</h2><span>${r.jenis_wilayah}</span></div>${[['IPM',r.ipm,2],['Lama sekolah (tahun)',r.rata_lama_sekolah,2],['Murid per guru',m.rasio,2],['Murid per sekolah',m.kepadatan,1],['Sekolah',m.sekolah,0],['Guru',m.guru,0],['Murid',m.murid,0]].map(([k,v,d])=>`<div class="metric-block"><span>${k}</span><b>${fmt(v,d)}</b></div>`).join('')}</article>`;};
    const delta=a.ipm-b.ipm;
    $('comparison').innerHTML=`<div class="two">${col(a)}${col(b)}</div><div class="callout">${a===b?'Kedua pilihan adalah daerah yang sama. Pilih daerah berbeda untuk membandingkan hasil.':delta===0?`Kedua daerah memiliki IPM yang sama: ${fmt(a.ipm,2)}.`:`IPM ${esc(a.kabupaten_kota)} ${delta>0?'lebih tinggi':'lebih rendah'} ${fmt(Math.abs(delta),2)} poin daripada ${esc(b.kabupaten_kota)}.`}</div><p class="note">Jumlah sekolah, guru, murid, serta rasionya memakai jenjang ${levelName()}. IPM dan lama sekolah merupakan indikator wilayah. Perbandingan ini belum memperhitungkan populasi penduduk dan akses geografis.</p>`;
  }
  function table(){
    const key=$('table-sort').value,ordered=[...rows].sort((a,b)=>key==='nama'?a.kabupaten_kota.localeCompare(b.kabupaten_kota,'id'):key==='ipm'?b.ipm-a.ipm:(A.measures(b,state.level).rasio??-Infinity)-(A.measures(a,state.level).rasio??-Infinity));
    $('table').innerHTML=`<table><caption style="text-align:left;padding:12px;color:#607086">${rows.length} wilayah; jenjang ${levelName()}; tahun integrasi 2025</caption><thead><tr><th scope="col">Wilayah</th>${['IPM','Lama sekolah (tahun)','Sekolah','Guru','Murid','Murid/guru','Murid/sekolah'].map(x=>`<th scope="col" class="num">${x}</th>`).join('')}</tr></thead><tbody>${ordered.map(r=>{const m=A.measures(r,state.level);return `<tr><td>${esc(r.kabupaten_kota)}</td>${[[r.ipm,2],[r.rata_lama_sekolah,2],[m.sekolah,0],[m.guru,0],[m.murid,0],[m.rasio,2],[m.kepadatan,1]].map(([v,d])=>`<td class="num">${fmt(v,d)}</td>`).join('')}</tr>`;}).join('')}</tbody></table>`;
  }
  function syncPanels(){
    const empty=!rows.length && active!==2;
    $('empty').hidden=!empty;
    for(let i=0;i<4;i++){
      $('pane-'+i).hidden=i!==active||empty;
      $('tab-'+i).setAttribute('aria-selected',String(i===active));
      $('tab-'+i).tabIndex=i===active?0:-1;
    }
    $('prev').disabled=active===0;$('next').disabled=active===3;
    $('demo-step').textContent=`${active+1} / 4 · ${titleNames[active]}`;
  }
  function render(){
    state={type:$('type').value,level:$('level').value,search:$('search').value,min:Number($('min').value),max:Number($('max').value)};
    rows=A.filter(all,state);
    $('context').innerHTML=`<span><b>${rows.length}</b> dari 38 wilayah</span><span>Jenjang: <b>${levelName()}</b></span><span>Data: <b>snapshot integrasi</b></span>${state.search?`<span>Pencarian: <b>${esc(state.search)}</b></span>`:''}<span>IPM: <b>${fmt(state.min,1)}–${fmt(state.max,1)}</b></span>`;
    $('download').disabled=rows.length===0;
    overview();ranking();scatter();compare();table();syncPanels();
  }
  function switchTab(n,focus=false){active=Math.max(0,Math.min(3,n));syncPanels();if(focus)$('tab-'+active).focus();}
  function reset(){ $('type').value='semua';$('level').value='semua';$('search').value='';$('min').value=0;$('max').value=100;render();}
  for(const id of ['type','level','search','metric','table-sort','compare-a','compare-b'])$(id).addEventListener(id==='search'?'input':'change',render);
  for(const id of ['min','max'])$(id).addEventListener('change',()=>{
    let v=Number($(id).value);if(!Number.isFinite(v))v=id==='min'?0:100;
    $(id).value=Math.max(0,Math.min(100,v));
    if(Number($('min').value)>Number($('max').value))$(id==='min'?'max':'min').value=$(id).value;
    render();
  });
  const options=all.map(r=>`<option>${esc(r.kabupaten_kota)}</option>`).join('');$('compare-a').innerHTML=options;$('compare-b').innerHTML=options;
  $('compare-a').value='Kota Surabaya';$('compare-b').value='Sampang';
  document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>switchTab(Number(b.dataset.tab))));
  document.querySelector('.tabs').addEventListener('keydown',e=>{
    if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();switchTab(e.key==='Home'?0:e.key==='End'?3:(active+(e.key==='ArrowRight'?1:3))%4,true);}
  });
  $('reset').addEventListener('click',reset);$('empty-reset').addEventListener('click',reset);
  $('prev').addEventListener('click',()=>switchTab(active-1));$('next').addEventListener('click',()=>switchTab(active+1));
  $('demo').addEventListener('click',()=>{
    presenting=!presenting;document.body.classList.toggle('presentation',presenting);
    $('demo').textContent=presenting?'Keluar presentasi':'Mode presentasi';$('demo').setAttribute('aria-pressed',String(presenting));syncPanels();if(presenting)$('main').focus();
  });
  document.addEventListener('keydown',e=>{
    if(!presenting||['INPUT','SELECT','TEXTAREA','BUTTON'].includes(e.target.tagName))return;
    if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();switchTab(active+(e.key==='ArrowRight'?1:-1));}
    if(e.key==='Escape')$('demo').click();
  });
  function regionClick(e){const el=e.target.closest('[data-region]');if(!el)return;$('compare-a').value=el.dataset.region;if($('compare-b').value===el.dataset.region)$('compare-b').value=all.find(r=>r.kabupaten_kota!==el.dataset.region).kabupaten_kota;compare();switchTab(2);}
  $('main').addEventListener('click',regionClick);
  $('scatter').addEventListener('keydown',e=>{if(e.target.matches('[data-region]')&&['Enter',' '].includes(e.key)){e.preventDefault();regionClick(e);}});
  $('download').addEventListener('click',()=>{
    const blob=new Blob([A.csv(rows,state.level)],{type:'text/csv;charset=utf-8;'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='pendidikan_jatim_'+state.level+'_2025.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  render();
})();
