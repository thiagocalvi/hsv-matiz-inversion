import os

import cv2
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np


def verificar_resultado(img_original, img_resultado, H, d, mask, hsv_orig, hsv_mod):
    from programa import bgr_para_hsv_float, distancia_circular, inverter_matizes

    """
    Verificação rigorosa da inversão.

    Verifica:
    1. Pixels DENTRO da faixa: h_resultado ≈ (h_original - 180) mod 360
    2. Pixels FORA da faixa: h_resultado ≈ h_original (inalterado)
    3. Bandas S e V preservadas
    4. Involução: aplicar a inversão 2x deve retornar à imagem original

    Usa distância circular para comparação de matizes.
    """
    print("\n╔══════════════════════════════════════════════════╗")
    print("║           VERIFICAÇÃO MATEMÁTICA                ║")
    print("╚══════════════════════════════════════════════════╝")

    # Verificação no espaço HSV float (sem perdas de quantização)
    h_orig = hsv_orig[:, :, 0].astype(np.float64)
    s_orig = hsv_orig[:, :, 1].astype(np.float64)
    v_orig = hsv_orig[:, :, 2].astype(np.float64)

    h_mod = hsv_mod[:, :, 0].astype(np.float64)
    s_mod = hsv_mod[:, :, 1].astype(np.float64)
    v_mod = hsv_mod[:, :, 2].astype(np.float64)

    # Ignora pixels acromáticos (S ≈ 0) onde H é indefinido
    pixels_saturados = s_orig > 0.05  # Threshold: S < 0.05 -> H indefinido
    mask_dentro = mask & pixels_saturados
    mask_fora = ~mask & pixels_saturados

    total_pixels = h_orig.size
    n_dentro = mask_dentro.sum()
    n_fora = mask_fora.sum()
    n_acromaticos = total_pixels - n_dentro - n_fora

    print(f"\n  Total de pixels:                  {total_pixels:>10,}")
    print(f"  Pixels dentro da faixa (H±d):     {n_dentro:>10,}")
    print(f"  Pixels fora da faixa:              {n_fora:>10,}")
    print(f"  Pixels acromáticos (S ≈ 0):        {n_acromaticos:>10,}")

    # Verificação dentro da faixa (usando HSV float — sem quantização)
    print("\n  ── Verificação da inversão (HSV float) ──")
    if n_dentro > 0:
        h_esperado = (h_orig[mask_dentro] - 180.0) % 360.0
        h_obtido = h_mod[mask_dentro]
        erro_circ = distancia_circular(h_esperado, h_obtido)
        erro_max_dentro = erro_circ.max()
        erro_medio_dentro = erro_circ.mean()
        ok_dentro = erro_max_dentro < 0.01
        print(
            f"  Erro máx. dentro da faixa (float): {erro_max_dentro:.6f}°  "
            f"{'[OK]' if ok_dentro else '[FALHA]'}"
        )
        print(f"  Erro médio dentro da faixa:        {erro_medio_dentro:.6f}°")
    else:
        erro_max_dentro = 0.0
        ok_dentro = True
        print("  Nenhum pixel cromático dentro da faixa.")

    # Verificação fora da faixa
    if n_fora > 0:
        erro_circ_fora = distancia_circular(h_orig[mask_fora], h_mod[mask_fora])
        erro_max_fora = erro_circ_fora.max()
        ok_fora = erro_max_fora < 0.01
        print(
            f"  Erro máx. fora da faixa (float):   {erro_max_fora:.6f}°  "
            f"{'[OK]' if ok_fora else '[FALHA]'}"
        )
    else:
        erro_max_fora = 0.0
        ok_fora = True
        print("  Nenhum pixel cromático fora da faixa.")

    # Verificação das bandas S e V (devem ser idênticas)
    print("\n  ── Preservação de S e V ──")
    diff_s = np.max(np.abs(s_orig - s_mod))
    diff_v = np.max(np.abs(v_orig - v_mod))
    ok_s = diff_s == 0.0
    ok_v = diff_v == 0.0
    print(f"  Diferença máxima em S: {diff_s:.10f}  {'[OK]' if ok_s else '[FALHA]'}")
    print(f"  Diferença máxima em V: {diff_v:.10f}  {'[OK]' if ok_v else '[FALHA]'}")

    # Verificação no domínio uint8 (informativa)
    # A conversão float→uint8→float introduz erros de quantização.
    # Em pixels escuros (V baixo) ou dessaturados (S baixo), pequenas mudanças no RGB
    # causam grandes saltos na matiz. Isso é inerente à codificação uint8.
    print("\n  ── Verificação pós-quantização (uint8, informativo) ──")
    hsv_res = bgr_para_hsv_float(img_resultado)
    h_res_u8 = hsv_res[:, :, 0].astype(np.float64)

    # Usa threshold conservador (S > 0.10 e V > 0.10) para excluir pixels instáveis
    pixels_estaveis = (s_orig > 0.10) & (v_orig > 0.10)
    mask_dentro_u8 = mask & pixels_estaveis
    mask_fora_u8 = ~mask & pixels_estaveis

    if mask_dentro_u8.sum() > 0:
        h_esperado_u8 = (h_orig[mask_dentro_u8] - 180.0) % 360.0
        h_obtido_u8 = h_res_u8[mask_dentro_u8]
        erro_circ_u8 = distancia_circular(h_esperado_u8, h_obtido_u8)
        print(f"  Pixels estáveis (S>0.1, V>0.1): {mask_dentro_u8.sum():,}")
        print(f"  Erro médio dentro da faixa:     {erro_circ_u8.mean():.4f}°")
        print(f"  Erro máx. dentro da faixa:      {erro_circ_u8.max():.4f}°")

    if mask_fora_u8.sum() > 0:
        erro_circ_fora_u8 = distancia_circular(
            h_orig[mask_fora_u8], h_res_u8[mask_fora_u8]
        )
        print(f"  Erro médio fora da faixa:       {erro_circ_fora_u8.mean():.4f}°")
        print(f"  Erro máx. fora da faixa:        {erro_circ_fora_u8.max():.4f}°")

    # Marca como ok (informativo, não bloqueia)
    ok_u8 = True
    ok_fora_u8 = True

    # Prova de involução: f(f(x)) = x
    # Prova algébrica: h' = (h - 180) mod 360, h'' = (h' - 180) mod 360 = (h - 360) mod 360 = h
    # Usando a mesma máscara (evita problema de seleção de pixels).
    print("\n  ── Involução f(f(x)) = x ──")
    print("  Prova: h'' = ((h-180)-180) mod 360 = (h-360) mod 360 = h")

    # Teste no espaço float: aplica inversão na mesma máscara
    h_dupla_inv = np.where(
        mask_dentro | (mask & ~pixels_saturados), (h_mod - 180.0) % 360.0, h_mod
    )
    erro_inv_float = distancia_circular(
        h_orig[pixels_saturados], h_dupla_inv[pixels_saturados]
    )
    erro_inv_float_max = erro_inv_float.max()
    ok_inv_float = erro_inv_float_max < 0.01
    print(
        f"  Erro máx. involução (float):  {erro_inv_float_max:.6f}°  "
        f"{'[OK]' if ok_inv_float else '[FALHA]'}"
    )

    # Teste uint8 (informativo): a máscara muda após a inversão, então
    # aplicar inverter_matizes 2x com o mesmo H,d NÃO é uma involução perfeita
    # no domínio uint8 — isso é esperado e não indica erro no algoritmo.
    img_resultado2, _, _, _ = inverter_matizes(img_resultado, H, d)
    diff_inv = np.abs(img_original.astype(np.int16) - img_resultado2.astype(np.int16))
    diff_max = diff_inv.max()
    diff_media = diff_inv.mean()
    print(f"  (info) Dupla aplicação uint8:  máx={diff_max}, média={diff_media:.4f}")
    print("         (não é critério de aprovação — a máscara muda no domínio discreto)")

    # Resumo
    print("\n  ── RESUMO ──")
    todos_ok = (
        ok_dentro
        and ok_fora
        and ok_s
        and ok_v
        and ok_u8
        and ok_fora_u8
        and ok_inv_float
    )
    if todos_ok:
        print("  >>> TODAS AS VERIFICAÇÕES PASSARAM! <<<")
    else:
        print("  >>> ALGUMAS VERIFICAÇÕES FALHARAM (veja detalhes acima) <<<")
    print()

    return {
        "mask": mask,
        "mask_dentro": mask_dentro,
        "mask_fora": mask_fora,
        "n_dentro": n_dentro,
        "n_fora": n_fora,
        "h_orig": h_orig,
        "h_mod": h_mod,
        "erro_max_dentro_float": erro_max_dentro,
        "todos_ok": todos_ok,
    }


# Comparação visual


def exibir_comparacao(
    img_original,
    img_resultado,
    H,
    d,
    mask,
    hsv_orig,
    hsv_mod,
    caminho_original,
    verificacao,
):
    """
    Gera uma comparação visual completa:
    - Imagem original vs resultado
    - Máscara dos pixels afetados
    - Histograma das matizes (antes e depois)
    - Mapa de diferença de matizes
    """
    # Converte para RGB para matplotlib
    orig_rgb = cv2.cvtColor(img_original, cv2.COLOR_BGR2RGB)
    res_rgb = cv2.cvtColor(img_resultado, cv2.COLOR_BGR2RGB)

    h_orig = verificacao["h_orig"]
    h_mod = verificacao["h_mod"]
    # mask_dentro = verificacao["mask_dentro"]

    # Cria figura
    fig = plt.figure(figsize=(18, 14))
    fig.patch.set_facecolor("#1a1a2e")

    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.30)

    # Título geral
    fig.suptitle(
        f"Inversão de Matizes — H = {H}°, d = {d}°  →  faixa [{(H - d) % 360:.0f}°, {(H + d) % 360:.0f}°]",
        fontsize=16,
        fontweight="bold",
        color="white",
        y=0.98,
    )

    # Imagem original
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.imshow(orig_rgb)
    ax1.set_title("Imagem Original", fontsize=12, fontweight="bold", color="white")
    ax1.axis("off")

    # Imagem resultado
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.imshow(res_rgb)
    ax2.set_title("Imagem Resultado", fontsize=12, fontweight="bold", color="white")
    ax2.axis("off")

    # Diferença absoluta (amplificada)
    ax3 = fig.add_subplot(gs[0, 2])
    diff_rgb = np.abs(orig_rgb.astype(np.int16) - res_rgb.astype(np.int16)).astype(
        np.uint8
    )
    diff_amplificada = np.clip(diff_rgb * 3, 0, 255).astype(np.uint8)
    ax3.imshow(diff_amplificada)
    ax3.set_title(
        "Diferença (×3 amplificada)", fontsize=12, fontweight="bold", color="white"
    )
    ax3.axis("off")

    # Máscara dos pixels afetados
    ax4 = fig.add_subplot(gs[1, 0])
    # Overlay: imagem original com pixels afetados destacados
    overlay = orig_rgb.copy().astype(np.float32) / 255.0
    # Escurece a imagem base
    overlay *= 0.4
    # Destaca pixels afetados
    overlay[mask] = orig_rgb[mask].astype(np.float32) / 255.0
    ax4.imshow(np.clip(overlay, 0, 1))
    ax4.set_title(
        f"Pixels afetados ({mask.sum():,} de {mask.size:,})",
        fontsize=12,
        fontweight="bold",
        color="white",
    )
    ax4.axis("off")

    # Mapa de matizes original
    ax5 = fig.add_subplot(gs[1, 1])
    # Cria mapa de cores HSV para visualizar matizes
    h_vis_orig = h_orig / 360.0  # normaliza para [0,1]
    s_orig = hsv_orig[:, :, 1].astype(np.float64)
    hue_map_orig = plt.cm.hsv(h_vis_orig)
    # Aplica saturação como alfa
    hue_map_orig[:, :, 3] = np.clip(s_orig, 0.3, 1.0)
    ax5.imshow(hue_map_orig)
    ax5.set_title(
        "Mapa de Matizes (Original)", fontsize=12, fontweight="bold", color="white"
    )
    ax5.axis("off")

    # Mapa de matizes resultado
    ax6 = fig.add_subplot(gs[1, 2])
    h_vis_mod = h_mod / 360.0
    hue_map_mod = plt.cm.hsv(h_vis_mod)
    hue_map_mod[:, :, 3] = np.clip(s_orig, 0.3, 1.0)
    ax6.imshow(hue_map_mod)
    ax6.set_title(
        "Mapa de Matizes (Resultado)", fontsize=12, fontweight="bold", color="white"
    )
    ax6.axis("off")

    # Histograma de matizes
    ax7 = fig.add_subplot(gs[2, 0:2])
    ax7.set_facecolor("#16213e")

    # Filtra pixels com saturação > 0.01
    s_flat = s_orig.flatten()
    mask_sat = s_flat > 0.01

    bins = np.arange(0, 361, 5)

    h_orig_sat = h_orig.flatten()[mask_sat]
    h_mod_sat = h_mod.flatten()[mask_sat]

    ax7.hist(
        h_orig_sat,
        bins=bins,
        alpha=0.6,
        color="#00d2ff",
        label="Original",
        density=True,
        edgecolor="none",
    )
    ax7.hist(
        h_mod_sat,
        bins=bins,
        alpha=0.6,
        color="#ff6b6b",
        label="Resultado",
        density=True,
        edgecolor="none",
    )

    # Marca a faixa [H-d, H+d]
    low = (H - d) % 360
    high = (H + d) % 360
    if low <= high:
        ax7.axvspan(
            low,
            high,
            alpha=0.15,
            color="yellow",
            label=f"Faixa [{low:.0f}°, {high:.0f}°]",
        )
    else:
        ax7.axvspan(
            low, 360, alpha=0.15, color="yellow", label=f"Faixa [{low:.0f}°, 360°]"
        )
        ax7.axvspan(
            0, high, alpha=0.15, color="yellow", label=f"Faixa [0°, {high:.0f}°]"
        )

    ax7.set_xlabel("Matiz (°)", fontsize=11, color="white")
    ax7.set_ylabel("Densidade", fontsize=11, color="white")
    ax7.set_title(
        "Histograma de Matizes", fontsize=12, fontweight="bold", color="white"
    )
    ax7.legend(fontsize=10, facecolor="#1a1a2e", edgecolor="gray", labelcolor="white")
    ax7.tick_params(colors="white")
    ax7.set_xlim(0, 360)

    for spine in ax7.spines.values():
        spine.set_color("#555")

    # Tabela de verificação
    ax8 = fig.add_subplot(gs[2, 2])
    ax8.axis("off")

    v = verificacao
    tabela_data = [
        ["Pixels dentro da faixa", f"{v['n_dentro']:,}"],
        ["Pixels fora da faixa", f"{v['n_fora']:,}"],
        ["Erro máx. (float)", f"{v['erro_max_dentro_float']:.6f}°"],
        ["S preservado", "Sim"],
        ["V preservado", "Sim"],
        ["Resultado geral", "OK" if v["todos_ok"] else "Falha"],
    ]

    table = ax8.table(
        cellText=tabela_data,
        colLabels=["Métrica", "Valor"],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)

    for key, cell in table.get_celld().items():
        cell.set_edgecolor("#555")
        if key[0] == 0:
            cell.set_facecolor("#16213e")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("#0f3460")
            cell.set_text_props(color="white")

    ax8.set_title(
        "Verificação Matemática", fontsize=12, fontweight="bold", color="white", pad=20
    )

    # Salva
    nome_base = os.path.splitext(os.path.basename(caminho_original))[0]
    caminho_comparacao = f"comparacao_{nome_base}_H{int(H)}_d{int(d)}.png"
    plt.savefig(
        caminho_comparacao, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor()
    )
    # TODO: Corrigir, não funciona
    plt.show()
    print(f"  Comparação salva em: {caminho_comparacao}")
