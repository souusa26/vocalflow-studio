"""
Testes unitários para o Bloco de Notas de Letras (Lyrics Manager).
"""

import pytest
from pathlib import Path
from app.lyrics.manager import LyricsManager

@pytest.fixture
def temp_lyrics_manager(tmp_path):
    mgr = LyricsManager(storage_dir=tmp_path)
    return mgr

def test_initial_sample_lyric(temp_lyrics_manager):
    lyrics = temp_lyrics_manager.list_lyrics()
    assert len(lyrics) >= 1
    assert "Apresentação" in lyrics[0]["title"]

def test_create_and_get_lyric(temp_lyrics_manager):
    item = temp_lyrics_manager.create_lyric("Minha Nova Rima", "Linha 1\nLinha 2\nLinha 3")
    assert item["id"] is not None
    assert item["title"] == "Minha Nova Rima"
    
    fetched = temp_lyrics_manager.get_lyric(item["id"])
    assert fetched["content"] == "Linha 1\nLinha 2\nLinha 3"

def test_update_lyric_autosave(temp_lyrics_manager):
    item = temp_lyrics_manager.create_lyric("Rascunho", "Ideia inicial")
    success = temp_lyrics_manager.update_lyric(item["id"], title="Título Final", content="Texto refinado")
    assert success is True
    
    updated = temp_lyrics_manager.get_lyric(item["id"])
    assert updated["title"] == "Título Final"
    assert updated["content"] == "Texto refinado"

def test_search_lyrics(temp_lyrics_manager):
    temp_lyrics_manager.create_lyric("Trap Nacional 2026", "Verso com autotune pesado")
    temp_lyrics_manager.create_lyric("Boombap Clássico", "Rimas na batida seca")
    
    found_trap = temp_lyrics_manager.list_lyrics(search_query="Trap")
    assert any(x["title"] == "Trap Nacional 2026" for x in found_trap)
    assert not any(x["title"] == "Boombap Clássico" for x in found_trap)

def test_delete_lyric(temp_lyrics_manager):
    item = temp_lyrics_manager.create_lyric("Para Excluir", "Conteudo descartavel")
    deleted = temp_lyrics_manager.delete_lyric(item["id"])
    assert deleted is True
    assert temp_lyrics_manager.get_lyric(item["id"]) is None

def test_export_lyric_txt(temp_lyrics_manager, tmp_path):
    item = temp_lyrics_manager.create_lyric("Letra Exportável", "Verso de teste para TXT")
    out_file = tmp_path / "letra_final.txt"
    exported = temp_lyrics_manager.export_lyric_txt(item["id"], out_file)
    assert exported is True
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "Verso de teste para TXT" in content
