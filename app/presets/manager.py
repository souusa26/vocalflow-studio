"""
Gerenciador de Presets do VocalFlow Studio.
Salva e recupera perfis de efeitos no disco em formato JSON, protege presets de fábrica
e suporta exportação e importação de configurações.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.config import get_presets_dir
from app.presets.factory_presets import FACTORY_PRESETS

class PresetManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.presets_dir = storage_dir or get_presets_dir()
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_factory_presets()

    def _ensure_factory_presets(self):
        """Grava os presets de fábrica se ainda não existirem."""
        for name, data in FACTORY_PRESETS.items():
            file_path = self._get_file_path(name)
            if not file_path.exists():
                try:
                    payload = dict(data)
                    payload["is_factory"] = True
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"[Presets] Erro ao gravar preset padrão '{name}': {e}")

    def _get_file_path(self, name: str) -> Path:
        # Sanitiza nome do arquivo
        safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", "(", ")")).strip()
        return self.presets_dir / f"{safe_name}.json"

    def list_presets(self) -> List[str]:
        """Retorna a lista de todos os nomes de presets disponíveis."""
        names = []
        for p in self.presets_dir.glob("*.json"):
            names.append(p.stem)
        # Ordena colocando os de fábrica primeiro
        factory_names = list(FACTORY_PRESETS.keys())
        user_names = [n for n in names if n not in factory_names]
        return factory_names + sorted(user_names)

    def load_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Carrega as configurações de um preset pelo nome."""
        path = self._get_file_path(name)
        if not path.exists():
            # Tenta busca exata pelo nome do arquivo
            cand = self.presets_dir / f"{name}.json"
            if cand.exists():
                path = cand
            else:
                return FACTORY_PRESETS.get(name)

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Presets] Erro ao carregar preset '{name}': {e}")
            return None

    def save_preset(self, name: str, state: Dict[str, Any], description: str = "") -> bool:
        """Salva ou atualiza um preset de usuário."""
        if not name.strip():
            return False

        path = self._get_file_path(name)
        payload = dict(state)
        payload["name"] = name.strip()
        payload["description"] = description
        payload["is_factory"] = False

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Presets] Erro ao salvar preset '{name}': {e}")
            return False

    def rename_preset(self, old_name: str, new_name: str) -> bool:
        """Renomeia um preset de usuário (não permite renomear de fábrica)."""
        if old_name in FACTORY_PRESETS:
            return False
        old_path = self._get_file_path(old_name)
        new_path = self._get_file_path(new_name)
        if not old_path.exists() or new_path.exists():
            return False
        try:
            old_path.rename(new_path)
            return True
        except Exception as e:
            print(f"[Presets] Erro ao renomear preset: {e}")
            return False

    def delete_preset(self, name: str) -> bool:
        """Exclui um preset (não permite excluir os de fábrica)."""
        if name in FACTORY_PRESETS:
            return False
        path = self._get_file_path(name)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as e:
                print(f"[Presets] Erro ao excluir preset: {e}")
                return False
        return False

    def export_preset(self, name: str, target_file_path: Path) -> bool:
        """Exporta um preset para um arquivo JSON externo."""
        data = self.load_preset(name)
        if not data:
            return False
        try:
            with open(target_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Presets] Erro ao exportar preset: {e}")
            return False

    def import_preset(self, source_file_path: Path) -> Optional[str]:
        """Importa um preset de arquivo JSON externo para a pasta do usuário."""
        try:
            with open(source_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name", source_file_path.stem)
            data["is_factory"] = False
            self.save_preset(name, data, data.get("description", ""))
            return name
        except Exception as e:
            print(f"[Presets] Erro ao importar preset: {e}")
            return None
