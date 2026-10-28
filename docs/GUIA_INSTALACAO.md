# Guia de Instalação e Configuração: VocalFlow Studio

Este guia explica como instalar o **VocalFlow Studio - Live Voice FX**, configurar o microfone virtual no Windows e rotear sua voz com efeitos em tempo real para programas como **Discord**, **OBS Studio** e jogos.

---

## 1. Modos de Distribuição

O aplicativo pode ser utilizado de duas formas no Windows:

### A. Versão Portátil (Recomendada para Pen Drives ou Sem Instalação)
1. Baixe e extraia o arquivo `VocalFlowStudio_Portatil_v1.0.0.zip` em qualquer pasta (ex: `C:\Programas\VocalFlowStudio` ou na Área de Trabalho).
2. Execute o arquivo `VocalFlowStudio.exe`.
3. Todas as suas configurações, letras e presets serão salvos na subpasta `data\` dentro do próprio diretório do programa, sem espalhar arquivos pelo sistema.

> [!IMPORTANT]
> A aplicação em si é 100% portátil. No entanto, para que outros programas (como Discord e OBS) recebam sua voz processada como um microfone, é necessária a instalação do driver de cabo virtual no Windows (veja a Seção 2).

---

### B. Versão Instalador (`VocalFlowStudio_Instalador_v1.0.0.exe`)
1. Execute o instalador `VocalFlowStudio_Instalador_v1.0.0.exe`.
2. Siga as instruções na tela em Português do Brasil.
3. O instalador criará atalhos no Menu Iniciar e na Área de Trabalho, além de disponibilizar um desinstalador limpo no Painel de Controle.
4. Na tela final, marque a opção para abrir o site do **VB-Audio Cable** caso ainda não o tenha instalado.

---

## 2. Instalação do Dispositivo Virtual (VB-Audio Virtual Cable)

O Windows não possui um cabo de áudio virtual nativo para conectar a saída de um aplicativo à entrada de microfone de outro. Utilizamos a solução gratuita da **VB-Audio**:

1. Acesse o site oficial: [https://vb-audio.com/Cable/](https://vb-audio.com/Cable/)
2. Baixe o pacote **VBCABLE_Driver_Pack.zip**.
3. Extraia o arquivo zip.
4. Clique com o botão direito no arquivo `VBCABLE_Setup_x64.exe` e selecione **"Executar como Administrador"**.
5. Clique em **"Install Driver"**.
6. Quando a instalação terminar, reinicie o computador para que o Windows reconheça os novos dispositivos.

> [!NOTE]
> **Licença do VB-Audio Cable:** O software é gratuito para uso pessoal (Donationware). Não é permitida a redistribuição silenciosa de drivers sem acordo de licenciamento com a fabricante, motivo pelo qual a instalação deve ser realizada diretamente pelo usuário com consentimento explícito.

---

## 3. Configuração do Roteamento no VocalFlow Studio

Abra o VocalFlow Studio e na aba **🎙️ Processamento Vocal**:

1. **Microfone de Entrada:** Selecione seu microfone físico real (ex: `Microfone (Realtek Audio)` ou `USB Audio Device`).
2. **Saída Virtual (Discord / OBS):** Selecione **`CABLE Input (VB-Audio Virtual Cable)`**.
3. **Monitor 1 (Fone de Ouvido):** Ative a caixa e selecione seu **Fone de Ouvido** para escutar sua voz com efeitos sem atraso perceptível.
4. **Monitor 2 (Caixa de Som):** Se desejar ouvir em caixas de som externas, ative este monitor.
   > [!WARNING]
   > Ao ativar o monitoramento em caixas de som com o microfone ligado, mantenha distância para evitar **microfonia (feedback loop)**. Use preferencialmente fones de ouvido durante a gravação vocal.
5. Clique no botão verde **"INICIAR PROCESSAMENTO (AO VIVO)"**.

---

## 4. Configuração no Discord

Para que seus amigos escutem sua voz com Autotune, Reverb e efeitos:

1. No Discord, clique na engrenagem no canto inferior esquerdo (**Configurações de Usuário**).
2. No menu lateral, acesse **Voz e Vídeo**.
3. Configure:
   - **Dispositivo de Entrada:** Selecione **`CABLE Output (VB-Audio Virtual Cable)`**.
   - **Dispositivo de Saída:** Mantenha seu **`Fone de Ouvido (Speakers/Headphones)`**.
4. **Dica Importante para Hip-Hop:**
   - Role até a seção **Avançado**.
   - Defina o **Cancelamento de Ruído** para **Desativado** (ou remova o modo Krisp), pois filtros agressivos do Discord podem cortar a sustentação do Autotune e a cauda do Reverb.

---

## 5. Configuração no OBS Studio

Para lives na Twitch, YouTube ou gravações de videoclipes:

1. Abra o OBS Studio e acesse **Configurações ➔ Áudio**.
2. Em **Dispositivos Globais de Áudio**:
   - Defina **Áudio do Microfone/Auxiliar** para **`CABLE Output (VB-Audio Virtual Cable)`**.
3. Em **Áudio do Desktop**, selecione seu fone de ouvido normal.
4. Clique em **Aplicar** e depois em **OK**.

---

## 6. Ajuste de Latência e Desempenho

Na aba **⚙️ Latência & Guia Cabo Virtual**:

- **Buffer de 128 amostras:** Latência teórica de ~2.7 ms (ideal para computadores rápidos).
- **Buffer de 256 amostras (Padrão):** Latência teórica de ~5.3 ms (equilíbrio perfeito entre resposta imediata no fone e estabilidade).
- **Buffer de 512 amostras:** Latência teórica de ~10.6 ms (recomendado caso escute estalos ou pequenas falhas no áudio).

---

## 7. Desinstalação

- **Para a versão portátil:** Basta excluir a pasta onde o programa foi descompactado.
- **Para a versão instalada:** Acesse *Configurações do Windows ➔ Aplicativos ➔ Aplicativos Instalados*, localize **VocalFlow Studio** e clique em **Desinstalar**.
- **Para remover o VB-Audio Cable:** Execute o `VBCABLE_Setup_x64.exe` como Administrador e clique em **"Remove Driver"**.
