"""
Script de Automação de Build e Empacotamento Portátil do VocalFlow Studio.
Gera a compilação standalone com PyInstaller e empacota em arquivo ZIP portátil.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
PORTABLE_ZIP = ROOT_DIR / "dist" / "VocalFlowStudio_Portatil_v1.0.0.zip"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def build():
    print("[Build] Limpando diretorios anteriores...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    spec_file = ROOT_DIR / "packaging" / "VocalFlowStudio.spec"
    print(f"[Build] Executando PyInstaller com {spec_file.name}...")

    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--noconfirm"]
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))

    if result.returncode != 0:
        print("[Build] ERRO: Falha ao compilar com PyInstaller.")
        sys.exit(result.returncode)

    target_app_dir = DIST_DIR / "VocalFlowStudio"
    if not target_app_dir.exists():
        print("[Build] ERRO: Diretorio gerado nao encontrado.")
        sys.exit(1)

    # Copia README e manuais
    shutil.copy(ROOT_DIR / "README.md", target_app_dir / "LEIAME.txt")
    if (ROOT_DIR / "docs" / "GUIA_INSTALACAO.md").exists():
        shutil.copy(ROOT_DIR / "docs" / "GUIA_INSTALACAO.md", target_app_dir / "GUIA_INSTALACAO.txt")

    print("[Build] Gerando arquivo ZIP portatil...")
    # Only the portable ZIP includes the marker; the installer uses this folder later.
    marker = target_app_dir / "portable.txt"
    try:
        marker.write_text("VocalFlowStudio Portable Mode\n", encoding="utf-8")
        shutil.make_archive(str(DIST_DIR / "VocalFlowStudio_Portatil_v1.0.0"), "zip", target_app_dir)
    finally:
        marker.unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print("[Build] SUCESSO: Compilacao concluida!")
    print(f"[Build] Pasta Standalone: {target_app_dir}")
    print(f"[Build] Pacote Portatil: {PORTABLE_ZIP}")
    print("=" * 60)

if __name__ == "__main__":
    build()
