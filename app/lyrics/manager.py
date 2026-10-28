"""
Gerenciador de Letras e Bloco de Notas (Lyrics Manager).
Permite criar, editar, pesquisar, salvar automaticamente e exportar letras de rap/hip-hop em formato JSON e TXT.
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from app.config import get_lyrics_dir

class LyricsManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        self.lyrics_dir = storage_dir or get_lyrics_dir()
        self.lyrics_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_sample_lyrics()

    def _ensure_sample_lyrics(self):
        """Cria uma letra de exemplo inicial se o diretório estiver vazio."""
        existing = list(self.lyrics_dir.glob("*.json"))
        if not existing:
            sample_content = (
                "[Verso 1]\n"
                "Microfone ligado, a batida no fone\n"
                "Minha voz ecoando, construindo meu nome\n"
                "Cada barra que eu rimo reflete a verdade\n"
                "Gravando meu som no meio da cidade\n\n"
                "[Refrão]\n"
                "Flow calibrado no tom e na escala\n"
                "O grave batendo e a rima não para\n"
                "VocalFlow Studio guiando o compasso\n"
                "Deixo minha marca em cada pedaço\n\n"
                "[Verso 2]\n"
                "Autotune afinado, batida no talo\n"
                "Escrevendo meu verso onde eu nunca me calo\n"
            )
            self.create_lyric("Letra de Apresentação (Freestyle)", sample_content)

    def _get_file_path(self, lyric_id: str) -> Path:
        return self.lyrics_dir / f"{lyric_id}.json"

    def list_lyrics(self, search_query: str = "") -> List[Dict[str, Any]]:
        """Lista todas as letras salvas, com filtro opcional por busca no título/conteúdo."""
        results = []
        query_lower = search_query.lower().strip()

        for path in self.lyrics_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                title = data.get("title", "")
                content = data.get("content", "")
                if query_lower:
                    if query_lower not in title.lower() and query_lower not in content.lower():
                        continue
                results.append({
                    "id": data.get("id", path.stem),
                    "title": title,
                    "updated_at": data.get("updated_at", 0),
                    "lines_count": len([line for line in content.splitlines() if line.strip()]),
                    "words_count": len(content.split()),
                })
            except Exception as e:
                print(f"[Lyrics] Falha ao ler letra {path.name}: {e}")

        # Ordena por data de atualização decrescente
        results.sort(key=lambda x: x["updated_at"], reverse=True)
        return results

    def get_lyric(self, lyric_id: str) -> Optional[Dict[str, Any]]:
        """Carrega os dados completos de uma letra."""
        path = self._get_file_path(lyric_id)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Lyrics] Erro ao carregar letra {lyric_id}: {e}")
            return None

    def create_lyric(self, title: str, content: str = "") -> Dict[str, Any]:
        """Cria uma nova letra e a persiste no disco."""
        title = title.strip() or "Sem Título"
        unique_suffix = uuid.uuid4().hex[:8]
        lyric_id = f"lyric_{int(time.time() * 1000)}_{unique_suffix}"
        now = time.time()

        data = {
            "id": lyric_id,
            "title": title,
            "content": content,
            "created_at": now,
            "updated_at": now
        }

        path = self._get_file_path(lyric_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Lyrics] Erro ao salvar nova letra: {e}")

        return data

    def update_lyric(self, lyric_id: str, title: Optional[str] = None, content: Optional[str] = None) -> bool:
        """Atualiza o conteúdo ou título de uma letra existente (autosave)."""
        data = self.get_lyric(lyric_id)
        if not data:
            return False

        if title is not None:
            data["title"] = title.strip() or "Sem Título"
        if content is not None:
            data["content"] = content

        data["updated_at"] = time.time()

        path = self._get_file_path(lyric_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Lyrics] Erro ao atualizar letra {lyric_id}: {e}")
            return False

    def delete_lyric(self, lyric_id: str) -> bool:
        """Exclui permanentemente uma letra."""
        path = self._get_file_path(lyric_id)
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as e:
                print(f"[Lyrics] Erro ao excluir letra {lyric_id}: {e}")
                return False
        return False

    def export_lyric_txt(self, lyric_id: str, target_file_path: Path) -> bool:
        """Exporta a letra como arquivo .txt ou .md legível."""
        data = self.get_lyric(lyric_id)
        if not data:
            return False

        try:
            with open(target_file_path, "w", encoding="utf-8") as f:
                f.write(f"# {data.get('title', 'Letra')}\n\n")
                f.write(data.get("content", ""))
                f.write("\n\n---\nCriado com VocalFlow Studio - Live Voice FX\n")
            return True
        except Exception as e:
            print(f"[Lyrics] Erro ao exportar TXT: {e}")
            return False
