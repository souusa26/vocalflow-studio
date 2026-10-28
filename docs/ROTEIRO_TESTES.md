# Roteiro de Testes e Relatório de Validação: VocalFlow Studio

Este documento consolida os resultados dos testes automatizados e estabelece o roteiro de testes manuais em hardware real no Windows.

---

## 1. Testes automatizados

Execute `python -m pytest -q` com as dependências de `requirements.txt`. A suíte inclui os testes originais e regressões para formato do microfone, frequência de saída do autotune em streaming, continuidade entre blocos, buffers cheios, limite final de mixagem, reamostragem, autosave na interface e separação dos modos instalado e portátil.

Os testes de dispositivos simulam PortAudio; os testes Qt usam a plataforma `offscreen`. Testes aprovados não representam cobertura de 100% nem substituem o roteiro de hardware abaixo. O workflow também executa a suíte e gera os pacotes Windows nos pull requests.

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
   - Se a voz chega ao fone imediatamente, sem atraso incômodo (medir a latência real de ponta a ponta; 256 amostras a 48 kHz são apenas 5,3 ms de um buffer, e o autotune, as filas e os drivers acrescentam atraso).
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

### Teste 7: Regressões de uso diário
1. Digite uma letra e troque imediatamente para outra; volte e confirme que a edição permanece. Repita fechando a janela imediatamente após digitar.
2. Durante reprodução, altere 48 kHz para 44,1 kHz e confirme que os streams reiniciam, os efeitos mantêm parâmetros e o tom/tempo do beat permanecem corretos.
3. Verifique que o instrumental completo está mutado ao carregar bateria/baixo/outros; confirme visualmente os controles.
4. Inicie com uma saída indisponível e confirme que a interface informa a falha e não permanece indicando transmissão saudável.
5. Instale como usuário comum, salve uma letra, reabra e confira os dados em `%APPDATA%/VocalFlowStudio`. Na versão ZIP, confira os dados na pasta `data` ao lado do executável.
