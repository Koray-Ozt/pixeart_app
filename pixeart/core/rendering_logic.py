import numpy as np
import scipy.ndimage as ndimage
from typing import Dict, Tuple
from pixeart.core.color import Color


# ─── Sabitler ────────────────────────────────────────────────────────────────

# Klasik 4×4 Bayer Ordered Dithering Matrisi (normalize: 0..1 aralığı)
_BAYER_4x4 = np.array([
    [ 0,  8,  2, 10],
    [12,  4, 14,  6],
    [ 3, 11,  1,  9],
    [15,  7, 13,  5],
], dtype=np.float32) / 16.0


# ─── Yardımcı: Vektörel RGB ↔ HSV ────────────────────────────────────────────

def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """
    Vektörel RGB→HSV dönüşümü.  rgb shape: (N, 3) float32 [0..1]
    Döndürür: (N, 3) float32  H[0..1], S[0..1], V[0..1]
    """
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    diff = maxc - minc

    # Value
    v = maxc

    # Saturation
    s = np.where(maxc == 0, 0.0, diff / maxc)

    # Hue
    h = np.zeros_like(maxc)
    mask_r = (maxc == r) & (diff > 0)
    mask_g = (maxc == g) & (diff > 0) & ~mask_r
    mask_b = (diff > 0) & ~mask_r & ~mask_g

    h[mask_r] = (60.0 * ((g[mask_r] - b[mask_r]) / diff[mask_r]) % 360.0)
    h[mask_g] = (60.0 * ((b[mask_g] - r[mask_g]) / diff[mask_g]) + 120.0)
    h[mask_b] = (60.0 * ((r[mask_b] - g[mask_b]) / diff[mask_b]) + 240.0)

    h = (h / 360.0) % 1.0  # 0..1 aralığına normalize et

    return np.stack([h, s, v], axis=-1)


def _hsv_to_rgb(hsv: np.ndarray) -> np.ndarray:
    """
    Vektörel HSV→RGB dönüşümü.  hsv shape: (N, 3) float32
    H[0..1], S[0..1], V[0..1]  →  RGB [0..1]
    """
    h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]

    i = np.floor(h * 6.0).astype(np.int32) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    # Her olası sektör (0-5) için RGB değerleri
    r = np.where(i == 0, v, np.where(i == 1, q, np.where(i == 2, p,
        np.where(i == 3, p, np.where(i == 4, t, v)))))
    g = np.where(i == 0, t, np.where(i == 1, v, np.where(i == 2, v,
        np.where(i == 3, q, np.where(i == 4, p, p)))))
    b = np.where(i == 0, p, np.where(i == 1, p, np.where(i == 2, t,
        np.where(i == 3, v, np.where(i == 4, v, q)))))

    return np.stack([r, g, b], axis=-1)


# ─── Ana Pipeline ────────────────────────────────────────────────────────────

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
    - Blinn-Phong (Lambertian + Specular) + Rim Light ışık modeli
    - Deterministik 4×4 Bayer Ordered Dithering (banding kırıcı)
    - Kuantizasyon (Bands)
    - Checkerboard ICM ile küme (cluster) koruma (ada temizleme)
    - HSV uzayında ton korumalı renk çarpımı
    """
    if not target_pixels:
        return {}

    # ─── Bounding Box ────────────────────────────────────────────────────
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

    # ═══════════════════════════════════════════════════════════════════════
    # 1. Kenar koruması ve Hacim (Volume) hesabı
    # ═══════════════════════════════════════════════════════════════════════
    intensity_med = ndimage.median_filter(intensity, size=3)

    # 2D Sprite'a hacim kazandırmak için Alpha maskesi üzerinden mesafe haritası
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
    N_x = -sobel_x * 2.0
    N_y = -sobel_y * 2.0
    N_z = np.ones_like(N_x) * 0.5

    norm = np.sqrt(N_x**2 + N_y**2 + N_z**2)
    norm[norm == 0] = 1.0
    N_x /= norm
    N_y /= norm
    N_z /= norm

    # ═══════════════════════════════════════════════════════════════════════
    # 2. Aydınlatma Modeli — Blinn-Phong + Rim Light
    # ═══════════════════════════════════════════════════════════════════════
    L_vec = np.array([lx, ly, lz], dtype=np.float32)
    L_norm_val = np.linalg.norm(L_vec)
    if L_norm_val > 0:
        L_vec /= L_norm_val
    else:
        L_vec = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    # Lambertian Diffuse (L_d)
    dot_NL = N_x * L_vec[0] + N_y * L_vec[1] + N_z * L_vec[2]
    L_d = np.clip(dot_NL, 0.0, 1.0)

    # Blinn-Phong Specular (L_s) — Half vector V=[0,0,1]
    V_vec = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    H_vec = L_vec + V_vec
    H_norm_val = np.linalg.norm(H_vec)
    if H_norm_val > 0:
        H_vec /= H_norm_val

    dot_NH = N_x * H_vec[0] + N_y * H_vec[1] + N_z * H_vec[2]
    # Shininess'ı 2× yaparak daha keskin specular highlight elde ediyoruz
    L_s = np.power(np.clip(dot_NH, 0.0, 1.0), shininess * 2.0)

    # Rim Light (kenar aydınlatması) — distance_map tabanlı Fresnel yaklaşımı
    # Kenar pikselleri: distance_map ≈ 0, Merkez: distance_map ≈ 1
    rim_power = 3.0
    rim_strength = 0.25
    rim = np.power(np.clip(1.0 - distance_map, 0.0, 1.0), rim_power)
    rim_intensity = rim * rim_strength * alpha_mask.astype(np.float32)

    # Toplam aydınlatma
    L_total = np.clip(kd * L_d + ks * L_s + rim_intensity, 0.0, 1.0)

    # ═══════════════════════════════════════════════════════════════════════
    # 3. Deterministik 4×4 Bayer Ordered Dithering
    # ═══════════════════════════════════════════════════════════════════════
    # Bayer matrisini bounding box boyutuna tile et
    bayer_tiled = np.tile(_BAYER_4x4, (bh // 4 + 1, bw // 4 + 1))[:bh, :bw]

    # Dithering gücü: bant sayısı arttıkça azalır (doğal davranış)
    dither_strength = 1.0 / max(num_bands, 2)

    # Bayer eşiğini [-0.5, +0.5] * strength aralığına çevir
    threshold = (bayer_tiled - 0.5) * dither_strength
    L_total_dithered = np.clip(L_total + threshold, 0.0, 1.0)

    # ═══════════════════════════════════════════════════════════════════════
    # 4. Kuantizasyon (Bantlara ayırma)
    # ═══════════════════════════════════════════════════════════════════════
    if num_bands > 1:
        quantized_L = np.floor(L_total_dithered * 0.999 * num_bands)
    else:
        quantized_L = np.zeros_like(L_total_dithered)

    # ═══════════════════════════════════════════════════════════════════════
    # 5. Cluster Koruma — Checkerboard ICM (Vektörel)
    # ═══════════════════════════════════════════════════════════════════════
    current_labels = quantized_L.copy()
    max_icm_iters = 3
    smoothness_weight = 1.2

    # Checkerboard maskesi: dama tahtası deseni
    rows, cols = np.indices((bh, bw))
    checkerboard = (rows + cols) % 2  # 0 = beyaz kareler, 1 = siyah kareler

    # İç piksel maskesi (sınırlar hariç — komşu erişimi güvenli)
    interior_mask = np.zeros((bh, bw), dtype=bool)
    interior_mask[1:-1, 1:-1] = True

    # 8 yöne kaydırma tanımları (dr, dc)
    shift_defs = [(-1, 0), (1, 0), (0, -1), (0, 1),
                  (-1, -1), (-1, 1), (1, -1), (1, 1)]

    # Hedef float değerler (data cost hesabı için)
    target_float = L_total * 0.999 * num_bands

    for _ in range(max_icm_iters):
        old_labels = current_labels.copy()

        for phase in (0, 1):  # Önce beyaz, sonra siyah kareler
            # Bu fazda güncellenecek pikseller
            phase_mask = (checkerboard == phase) & alpha_mask & interior_mask

            if not np.any(phase_mask):
                continue

            # 8 komşu label'ı topla (np.roll ile)
            neighbor_stack = np.empty((8, bh, bw), dtype=current_labels.dtype)
            for k, (dr, dc) in enumerate(shift_defs):
                neighbor_stack[k] = np.roll(np.roll(current_labels, -dr, axis=0), -dc, axis=1)

            # Aday label'lar: mevcut label ± 1 aralığında 3 aday
            # (komşuların unique'ini almak yerine — deterministik ve çok daha hızlı)
            current_at_phase = current_labels[phase_mask]

            # 3 aday: (label - 1), (label), (label + 1)  — sınırlar dahilinde
            candidates = np.stack([
                np.maximum(current_at_phase - 1, 0),
                current_at_phase,
                np.minimum(current_at_phase + 1, num_bands - 1 if num_bands > 1 else 0),
            ], axis=0)  # shape: (3, num_phase_pixels)

            # Hedef float değerler (faz pikselleri)
            target_at_phase = target_float[phase_mask]  # shape: (num_phase_pixels,)

            # Komşu label'ları faz pikselleri için çek
            neighbors_at_phase = neighbor_stack[:, phase_mask]  # shape: (8, num_phase_pixels)

            # Her aday için enerji hesapla
            best_labels = current_at_phase.copy()
            best_energy = np.full_like(current_at_phase, np.inf, dtype=np.float64)

            for c_idx in range(3):
                candidate = candidates[c_idx]  # shape: (num_phase_pixels,)

                # Data cost: |candidate - target_float|
                data_cost = np.abs(candidate - target_at_phase)

                # Smoothness cost: komşulardan farklı olanların sayısı × ağırlık
                diff_count = np.sum(neighbors_at_phase != candidate[np.newaxis, :], axis=0)
                smooth_cost = diff_count.astype(np.float64) * smoothness_weight

                energy = data_cost + smooth_cost

                # Daha düşük enerjili olanı seç
                better = energy < best_energy
                best_energy[better] = energy[better]
                best_labels[better] = candidate[better]

            # Güncellenmiş label'ları geri yaz
            current_labels[phase_mask] = best_labels

        # Yakınsama kontrolü
        if np.array_equal(old_labels, current_labels):
            break

    # ═══════════════════════════════════════════════════════════════════════
    # 6. Ada Temizleme (<3 piksel olan bağlı bileşenleri sil)
    # ═══════════════════════════════════════════════════════════════════════
    labeled_array, num_features = ndimage.label(current_labels + 1)
    sizes = ndimage.sum(alpha_mask, labeled_array, range(num_features + 1))

    for comp_id in range(1, num_features + 1):
        if sizes[comp_id] > 0 and sizes[comp_id] < 3:
            coords = np.where(labeled_array == comp_id)
            neighbor_labels = []
            for r, c in zip(*coords):
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < bh and 0 <= nc < bw and alpha_mask[nr, nc]:
                        if labeled_array[nr, nc] != comp_id:
                            neighbor_labels.append(current_labels[nr, nc])
            if neighbor_labels:
                most_frequent = max(set(neighbor_labels), key=neighbor_labels.count)
                current_labels[coords] = most_frequent

    # ═══════════════════════════════════════════════════════════════════════
    # 7. Sonuç Piksellerinin Hesaplanması — HSV Ton Korumalı Renk Çarpımı
    # ═══════════════════════════════════════════════════════════════════════
    # Sıralı piksel listesi oluştur (vektörel işlem için)
    sorted_keys = []
    sorted_colors_r = []
    sorted_colors_g = []
    sorted_colors_b = []
    sorted_colors_a = []
    transparent_set = set()

    for (x, y), c in target_pixels.items():
        if c.is_transparent:
            transparent_set.add((x, y))
            continue
        sorted_keys.append((x, y))
        sorted_colors_r.append(c.r)
        sorted_colors_g.append(c.g)
        sorted_colors_b.append(c.b)
        sorted_colors_a.append(c.a)

    result_pixels = {}

    # Şeffaf pikselleri olduğu gibi kopyala
    for pos in transparent_set:
        result_pixels[pos] = target_pixels[pos]

    if not sorted_keys:
        return result_pixels

    # NumPy dizilerine dönüştür
    rgb_array = np.stack([
        np.array(sorted_colors_r, dtype=np.float32),
        np.array(sorted_colors_g, dtype=np.float32),
        np.array(sorted_colors_b, dtype=np.float32),
    ], axis=-1) / 255.0  # shape: (N, 3), [0..1]

    alpha_array = np.array(sorted_colors_a, dtype=np.int32)

    # Her piksel için shade çarpanı hesapla
    shade_values = np.empty(len(sorted_keys), dtype=np.float32)
    for idx, (x, y) in enumerate(sorted_keys):
        lx_idx = x - min_x
        ly_idx = y - min_y
        band_val = current_labels[ly_idx, lx_idx]
        if num_bands > 1:
            quantized_light = band_val / float(num_bands - 1)
        else:
            quantized_light = 0.5
        # Temel gölge %40 karanlık, tam ışık %150 parlaklık
        shade_values[idx] = 0.4 + 1.1 * quantized_light

    # RGB → HSV (vektörel)
    hsv_array = _rgb_to_hsv(rgb_array)

    # Sadece V (Value) kanalını shade ile çarp — H ve S korunur
    hsv_array[:, 2] = np.clip(hsv_array[:, 2] * shade_values, 0.0, 1.0)

    # HSV → RGB (vektörel)
    rgb_result = _hsv_to_rgb(hsv_array)

    # [0..1] → [0..255] dönüşümü
    rgb_result_int = np.clip(rgb_result * 255.0, 0, 255).astype(np.int32)

    # Sonuç sözlüğüne yaz
    for idx, (x, y) in enumerate(sorted_keys):
        result_pixels[(x, y)] = Color(
            int(rgb_result_int[idx, 0]),
            int(rgb_result_int[idx, 1]),
            int(rgb_result_int[idx, 2]),
            int(alpha_array[idx])
        )

    return result_pixels
