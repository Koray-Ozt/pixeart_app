# Pixeart UI Widgets Modülü

`pixeart/ui/widgets` modülü, ekranın sol (araçlar) ve sağ (katman, renk panelleri) yanlarına yerleştirilen bağımsız arayüz panellerini içerir.

## Bileşenler

### 1. `ToolBarWidget` (`toolbar.py`)
Ekranın sol tarafındaki ana çizim araçlarını barındıran dikine bar.
- **QButtonGroup Altyapısı**: Seçilen aracın diğer araçların seçimini otomatik iptal etmesini sağlayan (Radyo Butonu Mantığı) sistem kullanılmıştır.
- **CSS Destekli Tasarım**: Okları gizlenmiş modern Fırça Kalınlığı seçicisi (`QSpinBox`) ve saydam seçilebilir ikon butonlar barındırır.
- İş akışını sağlamak için araç her değiştiğinde `tool_changed` sinyali fırlatır.

### 2. `ColorPalette` (`color_palette.py`)
Sol veya Sağ alt panelde yer alan ana renk kontrol arayüzü.
- **İkili Renk Yönetimi**: Kullanıcı, sol tıklamayla "Birincil (Fırça)" rengini, sağ tıklamayla "İkincil (Silgi/Alternatif)" rengini atayabilir. İç içe geçmiş iki kare, tamamen Qt'nin `QPainter` nesnesi ile özel olarak (Custom Paint) çizilmiştir.
- **DawnBringer 16**: Dünyanın en profesyonel piksel sanatçılarının standart olarak kabul ettiği `DB16` isimli renk dizisi kodun içerisine statik hazır palet olarak gömülmüştür. 

### 3. `LayerPanel` (`layer_panel.py`)
Sağ üst paneldeki Katman Yöneticisi arayüzü.
- **Ters (Top-Down) Mapping Algoritması**: Core yapısındaki 0 numaralı indeks (arka plan katmanı) her zaman UI listesinde en altta gösterilirken, en büyük indeks listenin en üstünde yer alır. Çeviri algoritmaları bu uyumu kusursuz sağlar.
- **Sinyal Hata Koruması (Bug Fix)**: Qt6'da `visibility_toggled` sinyali fırlatıldığında `checked` argümanını yutarak meydana gelen `TypeError: lambda takes 0 positional arguments but 1 was given` hatası lambda'nın içine `checked` yazılarak profesyonelce çözülmüştür.
- Olayları yakalamak için `layer_structure_changed` (ekleme/çıkarma/sıra değişimi) ve daha hafif render için `layer_visibility_changed` sinyalleri kullanılmıştır.
