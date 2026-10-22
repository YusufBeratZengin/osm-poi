# osm-poi

[![CI](https://github.com/YusufBeratZengin/osm-poi/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/osm-poi/actions/workflows/ci.yml)

OpenStreetMap üzerindeki ilgi noktalarını (işletmeler, hizmetler, dükkânlar) CSV, GeoJSON veya
JSONL olarak dışa aktarır. Herkese açık Overpass API ve Nominatim ile çalışır, kullanım
politikalarına uyar ve Python standart kütüphanesi dışında çalışma zamanı bağımlılığı yoktur.

Ücretli bir Places API kullanmadan, bir bölgedeki işletmeleri ücretsiz ve yasal biçimde listelemek
isteyen küçük ajanslar, araştırmacılar ve sivil projeler için hazırlandı.

## Özellikler

- Alan girişi: sınırlayıcı kutu (bbox), idari bölge adı (Nominatim ile çözülür) veya GeoJSON
  poligonu. Birden fazla alan birlikte kullanılabilir.
- Kategori ön ayarları (`cafe`, `restaurant`, `pharmacy`, `dentist`, `real_estate_agent`,
  `hairdresser`, `hotel` ve daha fazlası) düz bir JSON dosyasında tutulur, genişletilebilir.
- Düğüm (node), yol (way) ve ilişki (relation) türlerinin hepsi sorgulanır; yol ve ilişkilerde
  merkez nokta kullanılır.
- Düzenlenmiş alanlar: ad, kategori, adres parçaları, telefon, web sitesi, e-posta, çalışma
  saatleri, OSM kimliği ve bağlantısı.
- Aynı OSM nesnesinin tekrarları ile yakın kopyalar (varsayılan olarak 75 m içinde aynı ad ve
  kategori; örneğin bina çizimi ile nokta) temizlenir.
- CSV, GeoJSON veya JSONL çıktısı. CSV hücreleri elektronik tabloda formül çalıştırmaya karşı
  korunur.
- Nazik çalışır: User-Agent zorunlu, istekler arasında bekleme, 429 ve 5xx hatalarında üstel
  geri çekilmeyle yeniden deneme (`Retry-After` dikkate alınır) ve her isteğin özetiyle
  adlandırılan disk önbelleği.
- `--dry-run` Overpass sorgusunu göndermeden yazdırır.
- ODbL atıf metni her çıktı dosyasının yanına yazılır.

## Kurulum

```
pip install .
```

Python 3.10 veya üstü gerekir. Kaynak dizininden `pip install -e ".[dev]"` test ve lint
araçlarını da kurar.

## Hızlı başlangıç

Overpass ve Nominatim uygulamanızı tanıtmanızı ister. Size ulaşılabilecek bir iletişim bilgisi
içeren bir User-Agent tanımlayın:

```
export OSM_POI_USER_AGENT="my-project/1.0 (me@example.org)"      # Linux, macOS
$env:OSM_POI_USER_AGENT = "my-project/1.0 (me@example.org)"      # PowerShell
```

Sonra:

```
osm-poi fetch --area "Kadikoy, Istanbul" --category cafe,restaurant -o out.csv
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c pharmacy -o pharmacies.geojson
osm-poi fetch --polygon district.geojson -c dentist -f jsonl -o dentists.jsonl
osm-poi fetch --bbox 40.95,29.00,41.03,29.11 -c cafe --dry-run
osm-poi presets
```

`--bbox` Overpass sırasını kullanır: `güney,batı,kuzey,doğu` (`south,west,north,east`). Çıktı biçimi
dosya uzantısından (`.csv`, `.geojson`/`.json`, `.jsonl`) ya da `--format` seçeneğinden gelir.
`-o -` (varsayılan) sonucu standart çıktıya yazar.

### Çıktı sütunları

`osm_type, osm_id, osm_url, name, category, lat, lon, street, housenumber, postcode, city,
country, phone, website, email, opening_hours`

Adı olmayan kayıtlar `--include-unnamed` verilmedikçe atlanır. Eksik değerler boş metindir.

## Ön ayarlar

`osm-poi presets` ile listelenir. Ön ayar eklemek ya da değiştirmek için `--presets-file my.json`
verin:

```json
{
  "bike_shop": {
    "label": "Bisiklet dükkanları",
    "tags": [{"shop": "bicycle"}]
  },
  "bar": {
    "tags": [{"amenity": ["bar", "pub", "biergarten"]}]
  }
}
```

`tags` bir etiket kümeleri listesidir. Bir kayıt, kümelerden herhangi biriyle eşleşirse ön ayara
uyar; bir küme içinde tüm anahtarlar eşleşmelidir. Değer; bir metin, seçenek listesi ya da
"anahtar var mı" anlamına gelen `"*"` olabilir.

## Yapılandırma

Öncelik sırası (düşükten yükseğe): varsayılanlar, JSON yapılandırma dosyası, ortam değişkenleri,
komut satırı seçenekleri.

| Ayar | Ortam değişkeni | Seçenek | Varsayılan |
|---|---|---|---|
| `user_agent` | `OSM_POI_USER_AGENT` | `--user-agent` | yok (zorunlu) |
| `overpass_url` | `OSM_POI_OVERPASS_URL` | `--overpass-url` | `https://overpass-api.de/api/interpreter` |
| `nominatim_url` | `OSM_POI_NOMINATIM_URL` | `--nominatim-url` | `https://nominatim.openstreetmap.org` |
| `timeout` | `OSM_POI_TIMEOUT` | `--timeout` | 90 saniye |
| `retries` | `OSM_POI_RETRIES` | `--retries` | 3 |
| `backoff` | `OSM_POI_BACKOFF` | | 2 saniye, her denemede ikiye katlanır |
| `overpass_interval` | `OSM_POI_OVERPASS_INTERVAL` | | istekler arası 1 saniye |
| `nominatim_interval` | `OSM_POI_NOMINATIM_INTERVAL` | | istekler arası 1 saniye |
| `cache_dir` | `OSM_POI_CACHE_DIR` | `--cache-dir` | kullanıcı önbellek dizini |
| `cache_ttl_hours` | `OSM_POI_CACHE_TTL_HOURS` | `--cache-ttl-hours` | 168 |
| `use_cache` | `OSM_POI_USE_CACHE` | `--no-cache` | açık |

Yapılandırma dosyası aynı anahtarlarla bir JSON'dur. Konumu `--config`, `OSM_POI_CONFIG` ya da
`~/.config/osm-poi/config.json` (Windows'ta `%APPDATA%\osm-poi\config.json`) olur.
`osm-poi cache path` önbellek dizinini gösterir, `osm-poi cache clear` boşaltır.

## Kullanım politikaları

- [Nominatim kullanım politikası](https://operations.osmfoundation.org/policies/nominatim/):
  saniyede en çok bir istek, gerçek bir User-Agent, önbelleğe alınmış sonuçlar, toplu
  coğrafi kodlama yok. osm-poi her `--area` için tek sorgu gönderir ve sonucu önbelleğe alır.
  Herkese açık sunucuyu büyük toplu işler için kullanmayın.
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances):
  herkese açık sunucular ortaktır. Alanları ve kategorileri makul tutun; yoğun kullanımda
  `--overpass-url` ile kendi sunucunuzu gösterin.

## Veri atfı ve lisansı

Veri OpenStreetMap'ten gelir ve
[Açık Veritabanı Lisansı (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/) altındadır.
"(c) OpenStreetMap contributors" ifadesiyle atıf yapmalısınız; bu veriden türetilen bir
veritabanı aynı lisansla paylaşılmalıdır. osm-poi her dosyanın yanına `<çıktı>.ATTRIBUTION.txt`
yazar ve GeoJSON çıktısına `attribution` ile `license` alanlarını ekler. Bkz.
[OSM telif sayfası](https://www.openstreetmap.org/copyright). Bu bir hukuki görüş değildir.

OpenStreetMap, gönüllülerin girdiği veriler içerir; bunların arasında işletmelerin telefon
numaraları ve adresleri bulunabilir. Birileriyle iletişime geçmeden önce kullanımınıza uygulanan
gizlilik ve pazarlama kurallarını (örneğin KVKK, GDPR ve istenmeyen ileti düzenlemeleri)
kontrol edin.

## Geliştirme

```
pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m mypy src
```

Testler gerçek ağa çıkmaz: HTTP davranışı yerel bir sahte sunucuya karşı sınanır.

## Lisans

MIT, bkz. [LICENSE](LICENSE). Telif (c) 2026 Yusuf Berat Zengin.
