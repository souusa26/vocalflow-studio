"""
Testes unitários para o RingBuffer e a lógica de roteamento desacoplada.
"""

import pytest
import numpy as np
from app.audio.ring_buffer import AudioRingBuffer

def test_ring_buffer_write_and_read():
    buf = AudioRingBuffer(capacity=1024, channels=2)
    
    data = np.ones((256, 2), dtype=np.float32) * 0.75
    written = buf.write(data)
    assert written == 256
    assert buf.available_read() == 256
    
    read_chunk = buf.read(256)
    assert read_chunk.shape == (256, 2)
    assert np.allclose(read_chunk, 0.75)
    assert buf.available_read() == 0

def test_ring_buffer_underrun_returns_silence():
    buf = AudioRingBuffer(capacity=1024, channels=2)
    # Tenta ler sem nada escrito
    read_chunk = buf.read(128)
    assert read_chunk.shape == (128, 2)
    # Deve retornar zeros (silêncio) sem dar crash
    assert np.all(read_chunk == 0.0)

def test_ring_buffer_wraparound():
    buf = AudioRingBuffer(capacity=512, channels=2)
    
    # Escreve 400 frames
    buf.write(np.ones((400, 2), dtype=np.float32))
    # Lê 300 frames
    buf.read(300)
    
    # Agora a posição de escrita está em 400, e leitura em 300.
    # Escreve mais 200 frames -> força wrap-around além da capacidade de 512
    buf.write(np.ones((200, 2), dtype=np.float32) * 0.5)
    
    # Lê os restantes 100 do primeiro lote
    chunk1 = buf.read(100)
    assert np.allclose(chunk1, 1.0)
    
    # Lê os 200 do segundo lote (que passou pelo wrap-around)
    chunk2 = buf.read(200)
    assert np.allclose(chunk2, 0.5)
