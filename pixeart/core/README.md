# Pixeart Core Module

`pixeart/core` modülü, Pixeart uygulamasının bel kemiğidir. Kullanıcı arayüzünden (Qt) tamamen bağımsız olarak veri yapılarını, iş mantığını ve durum (state) yönetimini idare eder.

## İçerik ve Mimari

### 1. `Color` (`color.py`)
RGBA renk modelini temsil eden değiştirilemez (`frozen`) bir veri sınıfıdır.
- **Değişmezlik (Immutable)**: Renkler bir kez oluşturulduktan sonra değiştirilemez, bu da undo/redo işlemlerinde referans hatalarını önler.
- **Özellikler**: Hex metinlerinden renk oluşturma, Alfa harmanlaması (Alpha compositing / `blend_with`) ve Qt arayüzüne kolay aktarım için Tuple çevirici metotlar içerir.

### 2. `Layer` (`layer.py`)
Tek bir çizim katmanını yönetir.
- **Seyrek Veri Yapısı (Sparse HashMap)**: Geleneksel 2D matrisler yerine, pikselleri sadece dolu oldukları noktalarda bir sözlük (`Dict`) içerisinde saklar. Bu sayede devasa oranda RAM tasarrufu sağlanır ve sınırsız büyüklükteki tuvaller desteklenebilir.
- **Bounding Box Optimizasyonu**: Sadece aktif piksellerin olduğu sınırları hesaplar. Render motoru (UI) bu sayede tüm ekranı değil, sadece çizilen bölgeyi güncelleyerek performansı katlar.

### 3. `Document` (`document.py`)
Üzerinde çalışılan piksel sanat dosyasının (projenin) ana durumunu tutar.
- **Katman Yönetimi**: `Layer` listesini, tuval boyutlarını ve aktif katmanın dizinini güvenli bir şekilde yönetir. (Katman silme, yer değiştirme).
- **Kirli Durum (Dirty State)**: Dosyada değişiklik yapıldığında arayüze "kaydetme gerekli" sinyalini verebilmek için durumu takip eder.

### 4. `History` ve `Command` (`history.py`)
Gelişmiş Geri Al (Undo) ve İleri Al (Redo) altyapısı.
- **Command Pattern**: Tüm çizim işlemleri `Command` arayüzünden (interface) türetilir ve `.execute()` / `.undo()` metotlarını barındırır.
- **RAM Koruması**: Belirlenen maksimum adım sayısı aşıldığında en eski geçmiş silinir.
- **Reaktif Arayüz**: Değişiklik anında `_notify()` ile kayıtlı UI fonksiyonlarını tetikler, böylece menüdeki butonlar dinamik olarak güncellenir.
