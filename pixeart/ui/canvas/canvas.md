# Pixeart UI Canvas Modülü

`pixeart/ui/canvas` modülü, uygulamanın donanım hızlandırmalı ve optimize edilmiş görselleştirme motorudur. Qt'nin `QGraphicsView` ve `QGraphicsScene` mimarilerini piksel sanatı çizimine uygun şekilde yeniden tanımlar.

## Bileşenler

### 1. `CanvasScene` (`scene.py`)
Tuvalin (canvas) arka planını, katmanların görünümlerini ve piksel değişikliklerini yönetir.
- **`LayerGraphicsItem`**: Her katmanı bir `QImage` nesnesi olarak tutar. `update_pixel` çağrıldığında ekranı yeniden hesaplamak (full render) yerine, sadece değişen `(x, y, 1, 1)` lik alanı yeniden çizer (Partial Update/Blitting). Bu sayede devasa tuvallerde bile 60 FPS performans sağlar.
- **Event-Driven Yapı**: Çizim yapıldığında doğrudan iş mantığına müdahale etmez; bunun yerine `pixel_clicked` ve `pixel_dragged` sinyalleri (signal) fırlatarak Tools modülünün devreye girmesini bekler.
- **Checkerboard Pattern**: Saydamlık hissiyatını veren arka plan döşemesi.

### 2. `CanvasView` (`view.py`)
Kullanıcının sahneyi (Scene) nasıl gördüğünü (kamera hareketlerini) yönetir.
- **Pixel-Perfect Rendering**: Anti-aliasing özellikleri bilinçli olarak kapatılarak, yakınlaştırmalarda piksellerin bulanık (blurry) değil jilet gibi keskin görünmesi sağlanmıştır.
- **Cursor-Anchored Zoom**: Fare tekerleğiyle yakınlaştırma/uzaklaştırma yapılırken ekran ortasına değil, matematiksel hesaplamalar ile farenin imlecinin işaret ettiği spesifik koordinata odaklanılır.
- **Kusursuz Panning (Kaydırma)**: `Boşluk (Space)` tuşuna veya farenin orta tuşuna basılı tutarak ekran serbestçe ve akıcı şekilde sürüklenebilir.
- **Akıllı Izgara (Smart Grid)**: Ekrana %800'den fazla yaklaşıldığında "Kozmetik" (ekran donanımında her zoom seviyesinde sabit 1px kalan) bir ızgara çizgisini dinamik olarak çizer. Uzaktayken ekranı karartmamak için otomatik gizlenir.
