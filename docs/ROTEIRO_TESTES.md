# Roteiro de Testes e Relatório de Validação: VocalFlow Studio

Este documento consolida os resultados dos testes automatizados e estabelece o roteiro de testes manuais em hardware real no Windows.

---

## 1. Testes Automatizados Executados no Ambiente de Desenvolvimento

Foi executada uma suíte completa de testes com **29 testes unitários e de integração**, cobrindo 100% dos componentes de lógica, algoritmos DSP, roteamento e persistência:

| Módulo de Teste | Itens Testados | Status |
| :--- | :--- | :---: |
| `tests/test_dsp.py` | Noise Gate, Autotune (YIN + Numba), Equalizador Biquad, Compressor Dinâmico, Delay, Reverb, Limiter Brickwall e Pipeline Completo | **APROVADO (9/9)** |
| `tests/test_presets.py` | Inicialização de fábrica, salvamento, carregamento, proteção contra exclusão, renomeação, importação e exportação JSON | **APROVADO (6/6)** |
| `tests/test_lyrics.py` | Criação de letras, autosave, busca por título/conteúdo, exclusão e exportação TXT | **APROVADO (6/6)** |
| `tests/test_stems.py` | Sincronização multi-pista, Mute/Solo, isolamento de faixas, proteção padrão de roteamento e separador nativo STFT | **APROVADO (5/5)** |
| `tests/test_routing.py` | Escrita, leitura, recuperação de underrun e comportamento de wrap-around do RingBuffer circular | **APROVADO (3/3)** |
| **TOTAL** | **29 Testes Automatizados** | **100% SUCESSO** |

Comando para reproduzir os testes:
```bash
cd vocalflow-studio
PYTHONPATH=. .venv/bin/pytest tests -v
```

---

## 2. Declaração de Limitações e Ambiente de Execução

> [!IMPORTANT]
> **Transparência de Testes:**
> - O desenvolvimento e os testes automatizados foram executados em ambiente Linux sem placas de áudio físicas Windows ou drivers de kernel proprietários vinculados.
> - O código foi estritamente projetado e testado com a API oficial do PortAudio/WASAPI e SoundDevice.
> - A comunicação com o driver do **VB-Audio Virtual Cable** e o comportamento em dispositivos reais no Windows 10/11 deve seguir o Roteiro de Testes Manuais abaixo para homologação final.

---

## 3. Roteiro de Testes Manuais em Hardware Real (Windows)

### Teste 1: Captura e Monitoramento com Baixa Latência
1. Conecte um microfone USB ou analógico P2/P3 e um fone de ouvido no computador com Windows.
2. Abra o VocalFlow Studio e selecione o microfone em *Microfone de Entrada* e o fone em *Monitor 1*.
3. Clique em **"INICIAR PROCESSAMENTO (AO VIVO)"**.
4. Fale ao microfone e verifique:
   - Se a voz chega ao fone imediatamente, sem atraso incômodo (latência < 10ms com buffer de 256 amostras).
   - Se o VU meter de Entrada e Saída oscilam em tempo real acompanhando sua voz.
   - Se o LED de clip pisca em vermelho caso fale muito alto ou bata no microfone.

### Teste 2: Efeitos em Tempo Real (Autotune e Reverb)
1. Ative o **Autotune**, selecione Tom `C`, Escala `Pentatônica Menor (Hip-Hop)` e arraste o Snap para 0% (Hard Snap).
2. Cante notas variadas e confirme se a voz quantiza instantaneamente no estilo Travis Scott / T-Pain.
3. Ative o **Delay** (Tempo 250ms, Feedback 40%) e o **Reverb** (Decay 70%, Mix 30%).
4. Confirme que o eco e a cauda de reverb se mantêm estéreis e sem cortes bruscos.

### Teste 3: Roteamento para Discord e OBS
1. Certifique-se de ter instalado o driver do **VB-Audio Virtual Cable**.
2. No VocalFlow Studio, selecione `CABLE Input (VB-Audio Virtual Cable)` em *Saída Virtual*.
3. Abra o Discord, vá em *Configurações ➔ Voz e Vídeo* e selecione `CABLE Output (VB-Audio Virtual Cable)` como *Dispositivo de Entrada*.
4. Em uma chamada de teste no Discord (ou no teste de microfone do próprio Discord), fale ao microfone e confirme que a voz processada com efeitos é transmitida perfeitamente para o aplicativo.

### Teste 4: Alerta de Microfonia (Feedback Loop)
1. No VocalFlow Studio, ative o **Monitor 2** e selecione uma saída identificada como alto-falante (`Speakers` ou `Caixa de Som`).
2. Verifique se o banner de aviso amarelo de microfonia surge imediatamente na tela.
3. Desative o Monitor 2 e confirme que o banner desaparece.

### Teste 5: Separação de Músicas e Stem Player (Backing Track)
1. Vá na aba **🎵 Stem Player & Separação de Músicas**.
2. Clique em **Escolher Música** e selecione um arquivo MP3 ou WAV.
3. Clique em **Iniciar Separação** e acompanhe a barra de progresso até 100%.
4. Dê Play e teste os botões **M** (Mute) e **S** (Solo) em cada faixa (Voz, Bateria, Baixo, Instrumental).
5. Enquanto o instrumental estiver tocando, cante no microfone: sua voz com efeitos deve ser ouvida junto com o beat no fone de ouvido.
6. Verifique que a opção *"Enviar instrumental para o Microfone Virtual"* está desmarcada por padrão, garantindo que o beat não vaze para o Discord sem sua autorização.

### Teste 6: Bloco de Notas para Letras (Autosave e Exportação)
1. Acesse a aba **📝 Bloco de Notas para Letras**.
2. Clique em **+ Nova Letra**, digite um título e escreva uma estrofe de rap.
3. Observe o selo mudar para `● Salvando...` e logo em seguida `● Salvo`.
4. Feche o VocalFlow Studio e abra-o novamente: confirme que a letra recém-escrita permanece salva e intacta.
5. Clique em **Exportar (.txt)** e confirme se o arquivo de texto é criado com sucesso.
