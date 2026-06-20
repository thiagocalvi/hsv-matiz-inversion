"""
Inversão de Valores de Matizes no modelo HSV.

Recebe uma imagem colorida e dois parâmetros H e d,
inverte os matizes h ∈ [H-d, H+d] aplicando h' = (h - 180) mod 360,
preservando S e V.

Uso: python main.py <imagem> <H> <d>
  <imagem>  caminho da imagem (jpg, png, bmp, webp, tiff)
  <H>       valor do matiz central (0 a 360)
  <d>       raio da faixa (0 a 180)

Exemplo: python main.py flores.jpg 0 30
"""

import os
import sys

import cv2
import numpy as np

def carregar_imagem(caminho):
    """Carrega imagem e valida existência."""
    img = cv2.imread(caminho)
    if img is None:
        print(f"Erro: não foi possível carregar '{caminho}'")
        print("Formatos suportados: jpg, png, bmp, webp, tiff")
        sys.exit(1)
    return img


def bgr_para_hsv_float(img_bgr):
    """
    Converte BGR (uint8) -> HSV com H em [0,360), S e V em [0,1].
    Usa conversão float para máxima precisão.
    """
    rgb_float = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    hsv = cv2.cvtColor(rgb_float, cv2.COLOR_RGB2HSV)
    return hsv  # H: [0,360), S: [0,1], V: [0,1]


def hsv_float_para_bgr(hsv):
    """
    Converte HSV (H em [0,360), S e V em [0 ,1]) -> BGR (uint8).
    """
    rgb_float = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    # Clipa para [0,1] antes de converter para uint8 (evita artefatos)
    rgb_float = np.clip(rgb_float, 0.0, 1.0)
    bgr = cv2.cvtColor((rgb_float * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
    return bgr


def construir_mascara(h, H, d):
    """
    Constrói máscara booleana dos pixels cujo matiz h pertence a [H-d, H+d] (mod 360).
    Trata o wrap-around no ponto 0°/360°.

    Parâmetros:
        h: array de matizes em [0, 360)
        H: matiz central
        d: raio da faixa
    Retorna:
        mask: array booleano com mesma forma de h
    """
    low = (H - d) % 360
    high = (H + d) % 360

    # Faixa cobre todo o círculo
    if d >= 180 or low == high:
        return np.ones_like(h, dtype=bool)

    if low <= high:
        mask = (h >= low) & (h <= high)
    else:
        # Faixa cruza 0°/360° (ex: H=10, d=30 -> [340,360) U [0,40])
        mask = (h >= low) | (h <= high)

    return mask


def distancia_circular(a, b, periodo=360.0):
    """Distância angular mínima entre dois ângulos."""
    diff = np.abs(a - b)
    return np.minimum(diff, periodo - diff)


def inverter_matizes(img_bgr, H, d):
    """
    Inverte os matizes da imagem que estão na faixa [H-d, H+d].

    Para cada pixel com matiz h na faixa, aplica: h' = (h - 180) mod 360.
    As bandas S e V são preservadas integralmente.

    Parâmetros:
        img_bgr: imagem BGR (uint8)
        H: matiz central (0 a 360)
        d: raio da faixa (0 a 180)

    Retorna:
        img_resultado_bgr: imagem resultado BGR (uint8)
        mask: máscara dos pixels afetados
        hsv_original: HSV float da imagem original (para verificação)
        hsv_modificado: HSV float do resultado (para verificação)
    """
    # Converte para HSV float (H em [0,360))
    hsv = bgr_para_hsv_float(img_bgr)

    # Extrai banda H como float64 para precisão
    h = hsv[:, :, 0].astype(np.float64)

    # Constrói máscara da faixa [H-d, H+d]
    mask = construir_mascara(h, H, d)

    # Aplica inversão: h' = (h - 180) mod 360
    h_invertido = np.where(mask, (h - 180.0) % 360.0, h)

    # Atualiza somente a banda H
    hsv[:, :, 0] = h_invertido.astype(np.float32)

    # Converte de volta para BGR
    img_resultado_bgr = hsv_float_para_bgr(hsv)

    return img_resultado_bgr, mask


def salvar_resultado(img_resultado, caminho_original, H, d):
    """Salva a imagem resultado com nome derivado da original."""
    nome, ext = os.path.splitext(caminho_original)
    caminho_saida = f"{nome}_H{int(H)}_d{int(d)}{ext}"
    cv2.imwrite(caminho_saida, img_resultado)
    print(f"  Imagem salva em: {caminho_saida}")
    return caminho_saida


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    caminho = sys.argv[1]
    H = float(sys.argv[2])
    d = float(sys.argv[3])

    if not (0 <= H <= 360):
        print("Erro: H deve estar entre 0 e 360")
        sys.exit(1)
    if not (0 <= d <= 180):
        print("Erro: d deve estar entre 0 e 180")
        sys.exit(1)

    print("=" * 52)
    print("  INVERSÃO DE VALORES DE MATIZES (HSV)")
    print("=" * 52)
    print(f"  Imagem:  {caminho}")
    print(f"  H = {H}°, d = {d}°")
    print(f"  Faixa:   [{(H - d) % 360:.1f}°, {(H + d) % 360:.1f}°]")
    print("  Inversão: h' = (h - 180) mod 360")
    print("=" * 52)

    img_original = carregar_imagem(caminho)
    print(
        f"\n  Imagem carregada: {img_original.shape[1]}×{img_original.shape[0]} pixels"
    )

    img_resultado, mask = inverter_matizes(img_original, H, d)
    print(
        f"  Pixels afetados: {mask.sum():,} de {mask.size:,} "
        f"({100.0 * mask.sum() / mask.size:.1f}%)"
    )

    salvar_resultado(img_resultado, caminho, H, d)

    print("\n  Processamento concluído com sucesso!")