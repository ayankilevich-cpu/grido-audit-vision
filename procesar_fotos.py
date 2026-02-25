"""
Grido Audit Vision — Procesador de fotos
=========================================
Toma una carpeta con fotos crudas del celular, las comprime a calidad
de auditoría y las organiza por sección/ítem en una estructura limpia.

Uso:
  python procesar_fotos.py <carpeta_entrada> [--local NOMBRE] [--fecha YYYY-MM]

Ejemplo:
  python procesar_fotos.py ~/Desktop/fotos_crudo --local "Centro Córdoba" --fecha 2026-03

Nomenclatura esperada de archivos:
  Las fotos deben empezar con el código del ítem seguido de guión bajo.
  Ejemplos válidos:
    A1_01.jpg, A1_02.jpg          → Ítem A.1, fotos 1 y 2
    B4_matafuego.jpg              → Ítem B.4
    C10_licuadora_detalle.jpeg    → Ítem C.10
    a3_mesa.png                   → Ítem A.3 (case-insensitive)

  Si un archivo NO sigue la convención, se mueve a la carpeta "sin_clasificar/".

Estructura de salida:
  auditorias/
  └── 2026-03_Centro-Córdoba/
      ├── A_Infraestructura/
      │   ├── A1/
      │   │   ├── A1_01.jpg
      │   │   └── A1_02.jpg
      │   ├── A2/
      │   ...
      ├── B_Experiencia/
      ├── C_Operatoria/
      ├── D_Imagen/
      ├── E_Stock/
      ├── sin_clasificar/
      └── resumen.txt
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

MAX_DIMENSION = 1200
JPEG_QUALITY = 80
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}

SECTION_FOLDERS = {
    "A": "A_Infraestructura",
    "B": "B_Experiencia",
    "C": "C_Operatoria",
    "D": "D_Imagen",
    "E": "E_Stock",
}

ITEM_PATTERN = re.compile(
    r"^([A-Ea-e])(\d{1,2})",
)


def parse_item_code(filename: str) -> tuple[str, str] | None:
    """Extract section letter and item number from filename.
    Returns ('A', '1') for 'A1_foto.jpg' or None if no match.
    """
    stem = Path(filename).stem
    m = ITEM_PATTERN.match(stem)
    if m:
        return m.group(1).upper(), m.group(2)
    return None


def compress_image(src: Path, dst: Path, max_dim: int = MAX_DIMENSION, quality: int = JPEG_QUALITY):
    """Resize and compress image to audit quality."""
    try:
        img = Image.open(src)
    except Exception:
        shutil.copy2(src, dst)
        return None

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    exif = None
    try:
        exif_data = img.info.get("exif")
        if exif_data:
            exif = exif_data
    except Exception:
        pass

    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    save_kwargs = {"quality": quality, "optimize": True}
    if exif:
        save_kwargs["exif"] = exif

    dst = dst.with_suffix(".jpg")
    img.save(dst, "JPEG", **save_kwargs)
    return dst


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def main():
    parser = argparse.ArgumentParser(
        description="Comprime y organiza fotos de auditoría Grido"
    )
    parser.add_argument(
        "entrada",
        help="Carpeta con las fotos crudas del celular",
    )
    parser.add_argument(
        "--local",
        default="Local",
        help="Nombre del local (ej: 'Centro Córdoba')",
    )
    parser.add_argument(
        "--fecha",
        default=datetime.now().strftime("%Y-%m"),
        help="Año-mes de la auditoría (ej: 2026-03)",
    )
    parser.add_argument(
        "--salida",
        default="auditorias",
        help="Carpeta base de salida (default: auditorias/)",
    )
    parser.add_argument(
        "--max-px",
        type=int,
        default=MAX_DIMENSION,
        help=f"Dimensión máxima en px (default: {MAX_DIMENSION})",
    )
    parser.add_argument(
        "--calidad",
        type=int,
        default=JPEG_QUALITY,
        help=f"Calidad JPEG 1-100 (default: {JPEG_QUALITY})",
    )

    args = parser.parse_args()

    entrada = Path(args.entrada).expanduser().resolve()
    if not entrada.is_dir():
        print(f"Error: '{entrada}' no es una carpeta válida.")
        sys.exit(1)

    local_slug = args.local.replace(" ", "-")
    audit_folder_name = f"{args.fecha}_{local_slug}"
    base_salida = Path(args.salida) / audit_folder_name
    sin_clasificar = base_salida / "sin_clasificar"

    for folder in SECTION_FOLDERS.values():
        (base_salida / folder).mkdir(parents=True, exist_ok=True)
    sin_clasificar.mkdir(parents=True, exist_ok=True)

    max_dim = args.max_px
    jpeg_q = args.calidad

    all_files = []
    for ext in VALID_EXTENSIONS:
        all_files.extend(entrada.rglob(f"*{ext}"))
        all_files.extend(entrada.rglob(f"*{ext.upper()}"))
    all_files = sorted(set(all_files))

    if not all_files:
        print(f"No se encontraron fotos en '{entrada}'.")
        print(f"Extensiones buscadas: {', '.join(VALID_EXTENSIONS)}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Grido Audit Vision — Procesador de fotos")
    print(f"{'='*60}")
    print(f"  Entrada:    {entrada}")
    print(f"  Local:      {args.local}")
    print(f"  Fecha:      {args.fecha}")
    print(f"  Fotos:      {len(all_files)} encontradas")
    print(f"  Resolución: {args.max_px}px máximo")
    print(f"  Calidad:    {args.calidad}%")
    print(f"  Salida:     {base_salida}")
    print(f"{'='*60}\n")

    total_original = 0
    total_compressed = 0
    classified = 0
    unclassified = 0
    items_found: dict[str, int] = {}

    for i, src_file in enumerate(all_files, 1):
        original_size = src_file.stat().st_size
        total_original += original_size

        parsed = parse_item_code(src_file.name)

        if parsed:
            section, item_num = parsed
            item_code = f"{section}{item_num}"
            section_folder = SECTION_FOLDERS.get(section, "sin_clasificar")
            item_folder = base_salida / section_folder / item_code
            item_folder.mkdir(parents=True, exist_ok=True)

            dst_file = item_folder / src_file.name
            result_path = compress_image(src_file, dst_file, max_dim, jpeg_q)

            items_found[item_code] = items_found.get(item_code, 0) + 1
            classified += 1
        else:
            dst_file = sin_clasificar / src_file.name
            result_path = compress_image(src_file, dst_file, max_dim, jpeg_q)
            unclassified += 1

        if result_path and result_path.exists():
            compressed_size = result_path.stat().st_size
        else:
            compressed_size = dst_file.stat().st_size if dst_file.exists() else original_size
        total_compressed += compressed_size

        pct = i / len(all_files) * 100
        print(
            f"  [{pct:5.1f}%] {src_file.name:40s} "
            f"{format_size(original_size):>8s} → {format_size(compressed_size):>8s}"
        )

    savings = total_original - total_compressed
    savings_pct = (savings / total_original * 100) if total_original else 0

    summary_lines = [
        f"AUDITORÍA: {args.local} — {args.fecha}",
        f"Procesado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"FOTOS PROCESADAS: {len(all_files)}",
        f"  Clasificadas:     {classified}",
        f"  Sin clasificar:   {unclassified}",
        "",
        f"ESPACIO:",
        f"  Original:    {format_size(total_original)}",
        f"  Comprimido:  {format_size(total_compressed)}",
        f"  Ahorro:      {format_size(savings)} ({savings_pct:.0f}%)",
        "",
        f"ÍTEMS CON FOTOS ({len(items_found)}):",
    ]
    for code in sorted(items_found.keys(), key=lambda x: (x[0], int(x[1:]))):
        summary_lines.append(f"  {code}: {items_found[code]} fotos")

    if unclassified:
        summary_lines.extend([
            "",
            "ARCHIVOS SIN CLASIFICAR:",
            "  Revisar carpeta 'sin_clasificar/' y renombrar con el",
            "  código del ítem (ej: A1_01.jpg, B4_matafuego.jpg).",
        ])

    summary_text = "\n".join(summary_lines)
    (base_salida / "resumen.txt").write_text(summary_text, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"{'='*60}")
    print(f"  Fotos procesadas:  {len(all_files)}")
    print(f"  Clasificadas:      {classified}")
    print(f"  Sin clasificar:    {unclassified}")
    print(f"  Ítems cubiertos:   {len(items_found)}")
    print(f"{'─'*60}")
    print(f"  Tamaño original:   {format_size(total_original)}")
    print(f"  Tamaño comprimido: {format_size(total_compressed)}")
    print(f"  Ahorro:            {format_size(savings)} ({savings_pct:.0f}%)")
    print(f"{'─'*60}")
    print(f"  Salida: {base_salida}")
    print(f"{'='*60}\n")

    if unclassified:
        print(f"  ⚠ Hay {unclassified} fotos sin clasificar en:")
        print(f"    {sin_clasificar}")
        print(f"    Renombralas con el código del ítem y volvé a correr el script.\n")


if __name__ == "__main__":
    main()
