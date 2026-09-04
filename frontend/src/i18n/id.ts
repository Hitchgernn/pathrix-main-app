/** Indonesian, and the source of truth for the key set.
 *
 *  Adding a key here makes `en.ts` fail to compile until it is translated,
 *  which is the point.
 *
 *  **Do not translate**, in either catalogue: Yogyakarta place names,
 *  TransJogja, KRL, YIA, andong, becak, halte, pangkalan, Pathrix, MAPID.
 *  They are the domain vocabulary, not English-or-Indonesian words, and an
 *  English build that says "horse cart stand" for `pangkalan andong` is worse
 *  than one that leaves the term alone.
 *
 *  No `as const`: values widen to `string` so `en` can differ in wording while
 *  still being held to the same keys and call signatures.
 */
export const id = {
  // --- navigation ---------------------------------------------------------
  "nav.home": "Beranda",
  "nav.explore": "Peta",
  "nav.agent": "Agen",
  "nav.saved": "Tersimpan",
  "nav.profile": "Profil",
  "nav.group.main": "Navigasi",
  "nav.group.yours": "Milik Anda",
  "nav.aria": "Navigasi utama",
  "nav.collapse": "Ciutkan navigasi",
  "nav.expand": "Lebarkan navigasi",
  "nav.thisDevice": "Perangkat ini",

  // --- home ---------------------------------------------------------------
  "home.greeting": (name: string) => `Halo, ${name}`,
  "home.question": "Mau ke mana hari ini?",
  "home.carbonMonth": "CO₂e bulan ini",
  "home.openMap": "Buka peta",
  "home.savedCount": "tersimpan",
  "home.seeAll": "Lihat semua",
  "home.recent": "Terakhir",
  "home.sampleTrips": "Contoh perjalanan",
  "home.sampleNote": "Contoh perjalanan. Riwayat asli Anda muncul di sini setelah pencarian pertama.",
  "home.savedOnDevice": "Tersimpan di perangkat ini",

  "action.route.title": "Cari rute",
  "action.route.sub": "Lintas moda, pintu ke pintu",
  "action.stops.title": "Halte terdekat",
  "action.stops.sub": "TransJogja, KRL, KA Bandara",
  "action.pangkalan.title": "Andong & becak",
  "action.pangkalan.sub": "Pangkalan hasil survei",
  "action.layers.title": "Layer peta",
  "action.layers.sub": "6 layer tematik",

  // --- time ---------------------------------------------------------------
  "time.today": "Hari ini",
  "time.yesterday": "Kemarin",
  "time.daysAgo": (n: number) => `${n} hari lalu`,

  // --- search -------------------------------------------------------------
  "search.label": "Cari tempat",
  "search.placeholder": "Cari halte, tempat, atau alamat",
  "search.close": "Tutup pencarian",
  "search.saved": "Tersimpan",
  "search.recent": "Terakhir dicari",
  "search.searching": "Mencari…",
  "search.results": (n: number, local: boolean) =>
    `${n} hasil dari ${local ? "data Pathrix dan alamat" : "pencarian alamat"}`,
  "search.emptyTitle": (q: string) => `Tidak ada hasil untuk “${q}”`,
  "search.emptyBody": "Coba nama halte, stasiun, atau kawasan.",
  "search.askAgent": "Tanyakan ke agen",
  "search.failedTitle": "Pencarian tidak bisa dijangkau",
  "search.failedBody":
    "Layanan pencarian sedang tidak merespons. Peta dan agen tetap bisa dipakai.",

  // --- map chrome ---------------------------------------------------------
  "map.styleGroup": "Gaya peta",
  "map.styleLight": "Peta terang",
  "map.styleDark": "Peta gelap",
  "map.carbon": "Jejak karbon",
  "map.allLayers": "Semua layer",
  "map.recenterUser": "Pusatkan ke lokasi Anda",
  "map.recenterCity": "Pusatkan ke Yogyakarta",
  "map.yourLocation": "Lokasi Anda",
  "map.noKey": "Kunci basemap belum diatur. Setel VITE_MAPID_BASEMAP_KEY untuk memuat MAPID Maps.",

  "filter.all": "Semua",
  "filter.transit": "Halte & KRL",
  "filter.pangkalan": "Andong & becak",
  "filter.tourism": "Wisata",
  "filter.property": "Properti",
  "filter.reach": "Jangkauan",

  // --- agent --------------------------------------------------------------
  "agent.name": "Agen Pathrix",
  "agent.demoBanner": "Mode contoh, agen belum terpasang",
  "agent.reading": "Membaca peta yang Anda lihat",
  "agent.composing": "Menyusun rute…",
  "agent.calculating": "Sedang menghitung…",
  "agent.intro":
    "Saya membaca peta yang sedang Anda lihat: layer aktif, rute terakhir, dan viewport. Sebutkan tujuan, atau minta hal lain.",
  "agent.placeholder": "Tanya agen…",
  "agent.inputLabel": "Pesan untuk agen",
  "agent.send": "Kirim",
  "agent.expand": "Buka percakapan penuh",
  "agent.collapse": "Kecilkan percakapan",
  "agent.unavailable": "Chat sedang tidak tersedia.",

  "demo.step.readMap": "Membaca peta yang Anda lihat",
  "demo.step.endpoints": "Mencari titik awal dan tujuan",
  "demo.step.route": "Menyusun rute lintas moda",
  "demo.step.carbon": "Menghitung tarif dan jejak karbon",
  "demo.step.nearby": "Mencari halte dan pangkalan di sekitar",
  "demo.step.answer": "Menyiapkan jawaban",

  // --- place --------------------------------------------------------------
  "place.detail": "Detail tempat",
  "place.close": "Tutup",
  "place.routeHere": "Rute ke sini",
  "place.share": "Bagikan lokasi",
  "place.askAbout": (name: string) => `Ceritakan tentang ${name}`,
  "place.routeTo": (name: string) => `Rute ke ${name}`,
  "place.details": "Detail",
  "place.coordinate": "Koordinat",
  "place.source": "Sumber",
  "place.photo": "Foto",
  "place.fieldSurvey": "Survei lapangan",
  "place.noPhoto": "Foto survei belum tersedia untuk titik ini",
  "place.pendingDetails":
    "Jam operasional dan tarif akan muncul di sini setelah digitalisasi survei lapangan selesai.",
  "place.save": (name: string) => `Simpan ${name}`,
  "place.unsave": (name: string) => `Hapus ${name} dari tersimpan`,

  "kind.poi": "Tempat",
  "kind.properti": "Properti",
  "kind.transit": "Halte",
  "kind.pangkalan": "Pangkalan",
  "kind.address": "Alamat",

  "source.address": "Nominatim MAPID",
  "source.pangkalan": "Survei lapangan",
  "source.transit": "Data transit Pathrix",
  "source.mission": "Misi MAPID Apps",

  "fact.hours": "Jam buka",
  "fact.avgPrice": "Harga rata-rata",
  "fact.type": "Jenis",

  // --- saved --------------------------------------------------------------
  "saved.title": "Tersimpan",
  "saved.note": "Disimpan di perangkat ini saja. Tidak ada akun, dan tidak dikirim ke mana pun.",
  "saved.tabPlaces": (n: number) => `Tempat (${n})`,
  "saved.tabRoutes": (n: number) => `Rute (${n})`,
  "saved.emptyPlacesTitle": "Belum ada tempat tersimpan",
  "saved.emptyPlacesBody":
    "Ketuk ikon hati pada halte, pangkalan, atau tempat mana pun di peta untuk menyimpannya di sini.",
  "saved.emptyRoutesTitle": "Belum ada rute tersimpan",
  "saved.emptyRoutesBody":
    "Setelah agen menyusun perjalanan, simpan rutenya dari kartu rute agar bisa dibuka lagi tanpa bertanya ulang.",
  "saved.openMap": "Buka peta",
  "saved.askAgent": "Tanya agen",
  "saved.remove": (title: string) => `Hapus ${title}`,

  // --- profile ------------------------------------------------------------
  "profile.title": "Profil",
  "profile.nameLabel": "Nama Anda",
  "profile.saveName": "Simpan nama",
  "profile.storedHere": "Tersimpan di perangkat ini",
  "profile.trips": "Perjalanan",
  "profile.carbonSample": "CO₂e contoh",
  "profile.saved": "Tersimpan",
  "profile.carbonNote":
    "Angka CO₂e masih memakai faktor emisi contoh. Nilai asli muncul setelah faktor emisi dimuat dari basis data.",
  "profile.sourcePrefix": (source: string) => `Sumber: ${source}`,
  "profile.groupMap": "Peta",
  "profile.groupData": "Data",
  "profile.groupLanguage": "Bahasa",
  "profile.mapStyle": "Tampilan peta",
  "profile.mapStyleSub": "Terang atau gelap",
  "profile.light": "Terang",
  "profile.dark": "Gelap",
  "profile.location": "Akses lokasi",
  "profile.permGranted": "Diizinkan",
  "profile.permDenied": "Ditolak",
  "profile.permUnknown": "Belum diminta",
  "profile.permRefresh": "Perbarui",
  "profile.permAsk": "Minta izin",
  "profile.language": "Bahasa aplikasi",
  "profile.languageSub": "Nama tempat tetap dalam bahasa aslinya",
  "profile.dataSources": "Sumber data",
  "profile.dataSourcesSub": "MAPID Apps, OpenStreetMap, survei lapangan",
  "profile.clear": "Hapus data lokal",
  "profile.clearSub": "Profil, tersimpan, dan riwayat",
  "profile.clearAction": "Hapus",
  "profile.clearConfirm": "Yakin, hapus",
  "profile.footer": "Pathrix, Yogyakarta",
  "profile.changeAvatar": "Ubah gambar profil",

  "avatar.pick": "Pilih gambar",
  "avatar.option": (seed: string) => `Gambar profil ${seed}`,
  "avatar.upload": "Unggah foto",
  "avatar.remove": "Hapus",
  "avatar.cancel": "Batal",
  "avatar.localOnly": "Gambar disimpan di perangkat ini saja.",
  "avatar.tooBig": "Foto tidak bisa disimpan. Coba gambar yang lebih kecil.",

  // --- permission ---------------------------------------------------------
  "perm.title": "Izinkan akses lokasi",
  "perm.body":
    "Dipakai untuk menunjukkan halte, pangkalan andong dan becak terdekat, serta menghitung rute dari posisi Anda.",
  "perm.note":
    "Lokasi diproses di perangkat dan dikirim ke server hanya sebagai titik awal rute. Anda bisa mengubahnya kapan saja di Profil.",
  "perm.allow": "Izinkan akses",
  "perm.waiting": "Menunggu izin…",
  "perm.later": "Nanti saja, buka peta Yogyakarta",

  // --- panels -------------------------------------------------------------
  "panel.layers": "Layer tematik",
  "panel.route": "Malioboro → Prambanan",
  "panel.sustain": "Jejak karbon",
  "panel.close": "Tutup panel",
  "panel.expand": "Perbesar panel",
  "panel.shrink": "Perkecil panel",

  "layers.note": "Data dimuat saat layer diaktifkan, bukan sekaligus di awal.",
  "layers.notConnected": (meta: string) => `${meta}, belum tersambung`,

  "route.transfers": (n: number) => `${n} transfer`,
  "route.saveThis": "Simpan rute ini",
  "route.savedHere": "Tersimpan di perangkat ini",

  "sustain.avoidedThisTrip": "CO₂e terhindari, perjalanan ini",
  "sustain.thisMonth": "Bulan ini",
  "sustain.tripsRecorded": "Perjalanan tercatat",
  "sustain.empty": "Belum ada perjalanan tercatat",
  "sustain.emptyBody":
    "Belum ada perjalanan tercatat. Hitung satu rute dan angkanya muncul di sini bersama sumbernya.",
  "sustain.factorsReady": "Faktor emisi siap: KLHK (2023), IPCC 2006 Tier 1.",
  "sustain.sampleRoute": "Lihat rute contoh",
  "sustain.sourcePrefix": (source: string) => `Sumber: ${source}`,
};
