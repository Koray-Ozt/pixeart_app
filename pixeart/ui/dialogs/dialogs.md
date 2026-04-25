# Pixeart Dialogs Modülü

`pixeart/ui/dialogs` klasörü, uygulama içerisindeki tüm açılır pencereleri (modal diyalogları) yönetir. Kullanıcı deneyimini artırmak için Qt bileşenleri özelleştirilmiştir.

## Bileşenler

### 1. `NewFileDialog` (`new_file_dialog.py`)
Yeni bir piksel sanat projesi başlatılırken kullanıcıdan çözünürlük ölçülerini alan pencere.
- **Kare Orantı Kilidi**: Piksel sanatında en çok kullanılan oran karedir (1:1). Bu kilit sayesinde genişlik veya yükseklik değiştirildiğinde diğeri eş zamanlı ayarlanır. Kilit devredeyken (Örn: asimetrik bir girdi yapılmışsa) anında kendini kare formuna çeker. Sonsuz olay döngüsünü (recursive signal block) önlemek için Qt'nin `blockSignals()` metodu kullanılmıştır.
- **Hazır Şablonlar**: 16x16, 32x32, 64x64 gibi endüstri standardı şablonlar eklidir.

### 2. `ExportDialog` (`export_dialog.py`)
Çizimleri diske PNG, JPG veya BMP formatlarında dışa aktarmaya yarar.
- **Nearest-Neighbor Scaling (Ölçekleme)**: 32x32 boyutundaki bir çalışmayı sosyal medyada paylaşmak için %1000 ölçekle (320x320) büyütmeye olanak tanır. Bulanıklaşmayı engellemek için kodun ilgili yerinde (İleride Core'a eklenecek) *Kayıpsız Büyütme* algoritmaları tetiklenir.
- **Format Kontrolü**: Şeffaflığı (Alfa kanalını) desteklemeyen JPG ve BMP gibi formatlar seçildiğinde, şeffaflık seçeneği otomatik devre dışı bırakılarak mantık hatası önlenir.
