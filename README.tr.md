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
- Kategori ön ayarları (`cafe`, `restaurant`, `pharmacy`, `dentist`, `real_estate_agent`, `estate_agent`,
  `hairdresser`, `hotel`, `stationery`, `notary`, `car_repair` ve daha fazlası) düz bir JSON dosyasında tutulur.
- Düğüm (node), yol (way) ve ilişki (relation) türlerinin hepsi sorgulanır; yol ve ilişkilerde
  merkez nokta kullanılır.
- Düzenlenmiş alanlar: ad, kategori, adres parçaları, telefon, web sitesi, e-posta, çalışma
  saatleri, OSM kimliği ve bağlantısı.
- Aynı OSM nesnesinin tekrarları ile yakın kopyalar (varsayılan olarak 75 m içinde aynı ad ve
  kategori; örneğin bina çizimi ile nokta) temizlenir.
- Alan boyutu güvenliği: aşırı yüklenmeyi önlemek amacıyla `--allow-large` seçeneği verilmedikçe
  0.25 derece kare üzerindeki alanları sorgulamayı durdurur; `--split N` ile kutular alt bölgelere ayrılabilir.
- Gizlilik ve uyumluluk: `--no-contact` seçeneği telefon, web sitesi ve e-posta sütunlarını çıktıdan
  kaldırır; `--fields` seçeneği ile yalnız istenen sütunlar dışa aktarılabilir.
- CSV, GeoJSON veya JSONL çıktısı. CSV hücreleri elektronik tabloda formül çalıştırmaya karşı korunur.
- Nazik çalışır: User-Agent zorunlu, istekler arasında bekleme, 429 ve 5xx hatalarında üstel
  geri çekilmeyle yeniden deneme (`Retry-After` dikkate alınır) ve disk önbelleği.
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

## Örnek çıktı

### Kadıköy uygulamalı örneği

Bu Kadıköy örneğinde kafe ve restoranlar sorgulandığında OpenStreetMap'ten 5 ham kayıt gelir:
birbirine 25 metre mesafede "Moda Kahvecisi"ne ait bir nokta (node) ile bir bina çevresi (way),
bir balık restoranı ("Kadıköy Balıkçısı"), bir kitap kafe ("Bahariye Kitap Kafe") ve adı olmayan
bir kafe noktası. İşleme aşamasında:

1. **İsimsiz kayıtların filtrelenmesi**: Adı olmayan kayıtlar varsayılan olarak atlanır ve isimsiz
   kafe elenir.
2. **Tekilleştirme (Deduplication)**: 75 metre mesafe içinde aynı düzenlenmiş ada ("moda kahvecisi")
   sahip bina çizimi ve nokta tespit edilir. Daha eksiksiz iletişim ve adres bilgisi içeren nokta
   kaydı muhafaza edilip kopya çizim birleştirilir.
3. **Temiz sonuç**: Sonuçta tam olarak 3 tekilleştirilmiş işletme kaydı üretilir.

### CSV çıktı kesiti

```csv
osm_type,osm_id,osm_url,name,category,lat,lon,street,housenumber,postcode,city,country,phone,website,email,opening_hours
node,101,https://www.openstreetmap.org/node/101,Moda Kahvecisi,cafe,40.99,29.03,Moda Caddesi,12,,Kadıköy,TR,+90 216 555 0101,https://example.org/moda,,Mo-Su 08:00-22:00
node,303,https://www.openstreetmap.org/node/303,Kadıköy Balıkçısı,restaurant,40.985,29.025,Balıkçı Sokak,5,,Kadıköy,TR,+90 216 555 0102,https://example.org/balik,,Tu-Su 12:00-23:00
node,404,https://www.openstreetmap.org/node/404,Bahariye Kitap Kafe,cafe,40.982,29.028,Bahariye Caddesi,42,,Kadıköy,TR,+90 216 555 0103,https://example.org/kitap,,Mo-Sa 09:00-21:00
```

### GeoJSON özellik kesiti

```json
{
  "type": "Feature",
  "id": "node/101",
  "geometry": {
    "type": "Point",
    "coordinates": [
      29.03,
      40.99
    ]
  },
  "properties": {
    "osm_type": "node",
    "osm_id": 101,
    "osm_url": "https://www.openstreetmap.org/node/101",
    "name": "Moda Kahvecisi",
    "category": "cafe",
    "street": "Moda Caddesi",
    "housenumber": "12",
    "postcode": "",
    "city": "Kadıköy",
    "country": "TR",
    "phone": "+90 216 555 0101",
    "website": "https://example.org/moda",
    "email": "",
    "opening_hours": "Mo-Su 08:00-22:00"
  }
}
```

## Python API

`osm-poi` paketini bir Python kütüphanesi olarak doğrudan kullanabilirsiniz:

```python
from osm_poi import Poi, fetch_pois

pois = fetch_pois(
    bbox="40.95,29.00,41.03,29.11",
    categories=["cafe", "restaurant"],
    user_agent="my-app/1.0 (contact@example.org)",
)

for poi in pois:
    print(f"{poi.name} ({poi.category}) - {poi.lat}, {poi.lon} - {poi.phone or 'no phone'}")
```

Dönen nesneler [`Poi`](src/osm_poi/models.py) sınıfının örnekleridir. Dışa açık fonksiyonlar ve sınıflar
`__all__` listesinde tanımlıdır: `fetch_pois`, `Poi`, `BBox`, `Polygon`, `Config` ve `load_config`.

## Sorumlu kullanım

OpenStreetMap verileri topluluk gönüllüleri tarafından girilmekte ve güncellenmektedir. İşletme
kayıtları çoğunlukla açık iletişim bilgileri içerse de şu hususlara dikkat edilmelidir:

- **Gizlilik seçenekleri**: `--no-contact` bayrağı ile `phone`, `website` ve `email` sütunlarını çıktıdan
  tamamen kaldırabilir veya `--fields name,category,lat,lon` ile yalnızca istediğiniz sütunları seçebilirsiniz.
- **Kişisel verilerin korunması (KVKK / GDPR)**: Şahıs şirketleri, serbest meslek mensupları veya
  bireysel uzmanlarla ilişkili iletişim bilgileri 6698 sayılı Kişisel Verilerin Korunması Kanunu (KVKK)
  ve Avrupa Genel Veri Koruma Tüzüğü (GDPR) kapsamında kişisel veri niteliği taşıyabilir.
- **Elektronik ticari ileti ve spam mevzuatı**: İstenmeyen ticari iletiler (onaysız soğuk e-posta,
  otomatik arama veya SMS) 6563 sayılı Elektronik Ticaretin Düzenlenmesi Hakkında Kanun ve Ticari
  Elektronik İleti Yönetim Sistemi (İYS) düzenlemelerine tabidir.
- **Yasal sorumluluk**: Bu dokümantasyon bir hukuki görüş değildir. Veri toplama ve iletişim
  süreçlerinizin yürürlükteki mevzuata uygunluğunu değerlendirmek kullanıcının sorumluluğundadır.

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
| `max_area` | `OSM_POI_MAX_AREA` | `--max-area` | 0.25 derece kare |

Ek komut satırı seçenekleri:
- `--no-contact`: telefon, web sitesi ve e-posta sütunlarını çıktıdan çıkarır.
- `--fields LIST`: dışa aktarılacak sütunların listesi (örn. `--fields name,category,lat,lon`).
- `--allow-large`: alan boyutu güvenlik sınırını devre dışı bırakır.
- `--split N`: sınırlayıcı kutuyu $N \times N$ parçaya bölerek sıralı ve aralıklı alt sorgular gönderir.

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
