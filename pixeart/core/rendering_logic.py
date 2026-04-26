import numpy as np
import scipy.ndimage as ndimage
from typing import Dict, Tuple
from pixeart.core.color import Color

def apply_lighting_pipeline(
    target_pixels: Dict[Tuple[int, int], Color],
    width: int,
    height: int,
    lx: float, ly: float, lz: float,
    kd: float, ks: float, shininess: float,
    num_bands: int
) -> Dict[Tuple[int, int], Color]:
    """
    Deterministik ve matematiksel piksel sanatı aydınlatma pipeline'ı.
    - Sobel ile normal hesabı
    - Lambertian + Specular ışık modeli
    - Deterministik banding kırıcı (Jitter)
    - Kuantizasyon (Bands)
    - MRF / ICM ile küme (cluster) koruma (ada temizleme)
    """
    if not target_pixels:
        return {}

    # Bounding Box bulalım
    min_x = min(x for x, y in target_pixels.keys())
    max_x = max(x for x, y in target_pixels.keys())
    min_y = min(y for x, y in target_pixels.keys())
    max_y = max(y for x, y in target_pixels.keys())
    
    bw = max_x - min_x + 1
    bh = max_y - min_y + 1
    
    intensity = np.zeros((bh, bw), dtype=np.float32)
    alpha_mask = np.zeros((bh, bw), dtype=bool)
    
    for (x, y), c in target_pixels.items():
        lx_idx = x - min_x
        ly_idx = y - min_y
        alpha_mask[ly_idx, lx_idx] = not c.is_transparent
        # Grayscale yoğunluk (Y = 0.299R + 0.587G + 0.114B)
        intensity[ly_idx, lx_idx] = (0.299 * c.r + 0.587 * c.g + 0.114 * c.b) / 255.0

    # 1. Kenar koruması ve Hacim (Volume) hesabı
    intensity_med = ndimage.median_filter(intensity, size=3)
    
    # 2D Sprite'a hacim kazandırmak için Alpha maskesi üzerinden mesafe haritası (Distance Transform)
    distance_map = ndimage.distance_transform_edt(alpha_mask)
    max_dist = distance_map.max()
    if max_dist > 0:
        distance_map /= max_dist  # 0 ile 1 arasına normalize et
        
    # Hacim haritası ile renk yoğunluğunu birleştir.
    # %80 hacim (yuvarlaklık), %20 renk detayı.
    height_map = distance_map * 0.8 + intensity_med * 0.2
    
    # Sobel ile height_map üzerinden gradyan (Normal) hesabı
    sobel_x = ndimage.sobel(height_map, axis=1) / 8.0
    sobel_y = ndimage.sobel(height_map, axis=0) / 8.0
    
    # Normaller: N(x,y) = normalize(-gx, -gy, 1)
    # Z eksenini (derinlik) ayarlamak için sobel_z çarpanı kullanabiliriz.
    # Ne kadar düşükse, o kadar keskin kenar olur.
    N_x = -sobel_x * 2.0 
    N_y = -sobel_y * 2.0
    N_z = np.ones_like(N_x) * 0.5
    
    norm = np.sqrt(N_x**2 + N_y**2 + N_z**2)
    norm[norm == 0] = 1.0
    N_x /= norm
    N_y /= norm
    N_z /= norm
    
    # 2. Aydınlatma Modeli
    L_vec = np.array([lx, ly, lz], dtype=np.float32)
    L_norm = np.linalg.norm(L_vec)
    if L_norm > 0:
        L_vec /= L_norm
    else:
        L_vec = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        
    # Lambertian (L_d)
    dot_NL = N_x * L_vec[0] + N_y * L_vec[1] + N_z * L_vec[2]
    L_d = np.clip(dot_NL, 0.0, 1.0)
    
    # Specular (L_s) - Half vector V=[0,0,1]
    V_vec = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    H_vec = L_vec + V_vec
    H_norm = np.linalg.norm(H_vec)
    if H_norm > 0:
        H_vec /= H_norm
        
    dot_NH = N_x * H_vec[0] + N_y * H_vec[1] + N_z * H_vec[2]
    L_s = np.power(np.clip(dot_NH, 0.0, 1.0), shininess)
    
    # Toplam aydınlatma (L_total'in aralığını biraz daha açalım ki banding daha iyi gözüksün)
    # Kd ve Ks kullanıcıdan 0.0-2.0 arası geliyor.
    L_total = np.clip(kd * L_d + ks * L_s, 0.0, 1.0)
    
    # Deterministik Jitter (Banding sınırlarını kırmak için)
    xx, yy = np.meshgrid(np.arange(bw), np.arange(bh))
    jitter = (np.sin(xx * 1.5 + yy * 2.3) + np.cos(xx * 2.7 - yy * 1.1)) * 0.02
    grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
    jitter_mask = np.exp(-grad_mag * 10.0) # Düşük gradyanda (düzlük) jitter fazla
    L_total = np.clip(L_total + jitter * jitter_mask, 0.0, 1.0)
    
    # 3. Kuantizasyon (Bantlara ayırma)
    if num_bands > 1:
        quantized_L = np.floor(L_total * 0.999 * num_bands)
    else:
        quantized_L = np.zeros_like(L_total)
        
    # 4. Cluster Koruma (ICM & Ada Temizleme)
    current_labels = quantized_L.copy()
    max_icm_iters = 3
    smoothness_weight = 1.2
    
    for _ in range(max_icm_iters):
        changed = False
        for i in range(1, bh-1):
            for j in range(1, bw-1):
                if not alpha_mask[i, j]: continue
                
                best_label = current_labels[i, j]
                min_energy = float('inf')
                
                neighbors = [
                    current_labels[i-1, j], current_labels[i+1, j],
                    current_labels[i, j-1], current_labels[i, j+1],
                    current_labels[i-1, j-1], current_labels[i-1, j+1],
                    current_labels[i+1, j-1], current_labels[i+1, j+1]
                ]
                unique_labels = np.unique(neighbors)
                if current_labels[i, j] not in unique_labels:
                    unique_labels = np.append(unique_labels, current_labels[i, j])
                    
                target_float = L_total[i, j] * 0.999 * num_bands
                
                for label in unique_labels:
                    data_cost = abs(label - target_float)
                    diff_count = sum(1 for n_l in neighbors if n_l != label)
                    smooth_cost = diff_count * smoothness_weight
                    
                    energy = data_cost + smooth_cost
                    if energy < min_energy:
                        min_energy = energy
                        best_label = label
                        
                if best_label != current_labels[i, j]:
                    current_labels[i, j] = best_label
                    changed = True
                    
        if not changed:
            break
            
    # Ada Temizleme (<3 piksel olan bağlı bileşenleri sil)
    labeled_array, num_features = ndimage.label(current_labels + 1)
    sizes = ndimage.sum(alpha_mask, labeled_array, range(num_features + 1))
    
    for comp_id in range(1, num_features + 1):
        if sizes[comp_id] > 0 and sizes[comp_id] < 3:
            coords = np.where(labeled_array == comp_id)
            neighbor_labels = []
            for r, c in zip(*coords):
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < bh and 0 <= nc < bw and alpha_mask[nr, nc]:
                        if labeled_array[nr, nc] != comp_id:
                            neighbor_labels.append(current_labels[nr, nc])
            if neighbor_labels:
                most_frequent = max(set(neighbor_labels), key=neighbor_labels.count)
                current_labels[coords] = most_frequent
                
    # 5. Sonuç Piksellerinin Hesaplanması (Renk Çarpımı)
    result_pixels = {}
    
    # quantized_L değerimiz [0, num_bands-1] aralığında
    for (x, y), original_c in target_pixels.items():
        if original_c.is_transparent:
            result_pixels[(x, y)] = original_c
            continue
            
        lx_idx = x - min_x
        ly_idx = y - min_y
        
        band_val = current_labels[ly_idx, lx_idx]
        
        # quantized_L'i tekrar 0-1 aralığına çevirelim
        if num_bands > 1:
            quantized_light = band_val / float(num_bands - 1)
        else:
            quantized_light = 0.5
            
        # Ortam ışığı (Ambient) + Işık şiddeti (quantized_light) * Işık Gücü
        # Işık yönüne ve specular'a göre kd/ks zaten L_total'i oluşturmuştu.
        # Biz burada L_total'in kuantize edilmiş halini (quantized_light) renk çarpanı olarak kullanıyoruz.
        
        # Temel gölge %40 karanlık, tam ışık %150 parlaklık olsun ama bu 
        # aslında L_total'in normalize halidir.
        shade = 0.4 + 1.1 * quantized_light
        
        new_r = int(np.clip(original_c.r * shade, 0, 255))
        new_g = int(np.clip(original_c.g * shade, 0, 255))
        new_b = int(np.clip(original_c.b * shade, 0, 255))
        
        result_pixels[(x, y)] = Color(new_r, new_g, new_b, original_c.a)
        
    return result_pixels
