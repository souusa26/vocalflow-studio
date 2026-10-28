# 🎙️ VocalFlow Studio - Live Voice FX

> **Processador Vocal em Tempo Real para Windows com Autotune Hip-Hop, Stem Player & Bloco de Letras.**

Desenvolvido especialmente para cantores e MCs iniciantes de rap, trap e hip-hop que desejam processar a própria voz ao vivo com baixa latência e transmiti-la para aplicativos como **Discord**, **OBS Studio** e gravadores.

---

## 🌟 Principais Recursos

### 1. Processamento Vocal em Tempo Real (Cadeia de Efeitos de Estúdio)
- **Noise Gate:** Elimina ruídos de fundo e respirações indesejadas antes da afinação.
- **Autotune de Alta Velocidade:** Motor YIN e pitch-shifter granular contínuo acelerados por **Numba JIT**, com suporte desde correção suave até o clássico *Hard Snap* estilo Travis Scott / T-Pain em escalas Pentatônica, Menor e Maior.
- **Equalizador Paramétrico de 3 Bandas + High-Pass:** Corte de graves subsônicos (<80Hz), reforço de presença (2.5kHz) e brilho de cápsula de condensador (9kHz).
- **Compressor Dinâmico:** Encorpa a voz, amortece picos e traz consistência de volume ("punch").
- **Delay / Eco:** Eco estéreo analógico com repetições suaves e filtro passa-baixas.
- **Reverb Estéreo:** Ambiência imersiva inspirada no modelo Freeverb / Schroeder.
- **Master Brickwall Limiter:** Impede estouros digitais (> 0dBFS) e distorções nas transmissões.

### 2. Roteamento Multi-Stream Desacoplado
- Transmissão prioritária para dispositivo de microfone virtual (**VB-Audio Virtual Cable** para Discord e OBS).
- Monitoramento com fones de ouvido (Monitor 1) e saídas secundárias (Monitor 2).
- **Alerta Inteligente de Microfonia:** Identifica saídas de caixas de som e avisa sobre o risco de realimentação acústica.

### 3. Stem Player & Separação de Músicas (Backing Track)
- Separe músicas locais (MP3, WAV, FLAC, OGG) em **Voz, Instrumental, Bateria e Baixo**.
- **Motor Duplo:** Separação espectral rápida nativa (0 MB de download) e integração opcional com o modelo neural **Demucs** da Meta AI.
- Toque o beat enquanto canta por cima com monitoramento e efeitos vocais.
- **Proteção de Transmissão:** O instrumental é ouvido apenas no seu fone por padrão, impedindo vazamento acidental para o microfone do Discord/OBS.
- Exporte stems isolados ou mixes personalizados em formato WAV.

### 4. Bloco de Notas para Letras & Rimas
- Crie, edite, organize e busque letras de músicas por título ou trecho.
- **Salvamento Automático (Autosave):** Nunca perca uma rima inspirada.
- Contador de versos e palavras em tempo real.
- Exportação para arquivos de texto `.txt`.

### 5. Presets de Fábrica Integrados
- `Voz Limpa (Studio Vocal)`
- `Rap Suave (Warm Rap)`
- `Trap Autotune (Travis Style)`
- `Efeito Rádio / Megafone`
- `Espaço Trap (Deep Reverb)`
- Salve, renomeie, exporte e importe seus próprios presets personalizados em JSON.

---

## 🚀 Como Executar a Partir do Código-Fonte

### Pré-requisitos
- Python 3.10 ou superior
- Pip e Virtualenv

### Instalação
```bash
# 1. Clone ou acesse a pasta do projeto
cd vocalflow-studio

# 2. Crie e ative um ambiente virtual
python -m venv .venv

# No Windows:
.venv\Scripts\activate
# No Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o aplicativo
python -m app.main
```

---

## 🧪 Executando os Testes Automatizados

```bash
PYTHONPATH=. pytest tests -v
```

---

## 📦 Como Gerar a Versão Portátil e o Instalador

### 1. Gerar Pacote Portátil Standalone (.zip)
```bash
python packaging/build.py
```
O executável e o arquivo `.zip` serão gerados na pasta `dist/`. O ZIP contém `portable.txt` e salva os dados ao lado do executável; o instalador usa `%APPDATA%/VocalFlowStudio`.

### 2. Gerar o Instalador para Windows (.exe)
1. Instale o [Inno Setup 6](https://jrsoftware.org/isdl.php) no Windows.
2. Abra o arquivo `packaging/installer.iss` no Inno Setup Compiler.
3. Clique em **Build ➔ Compile**.
4. O instalador traduzido em Português do Brasil será gerado em `dist_installer/`.

---

## 📖 Documentação Detalhada
- [Guia de Instalação e Roteamento no Discord/OBS](docs/GUIA_INSTALACAO.md)
- [Arquitetura de Engenharia de Áudio](docs/ARQUITETURA.md)
- [Roteiro de Testes e Validação](docs/ROTEIRO_TESTES.md)

---

## ⚖️ Licença
Distribuído sob a licença **MIT**. Veja o arquivo `LICENSE` para mais detalhes.

## Validação e limites do processamento ao vivo

- O autotune mantém memória e fase entre callbacks. Sua janela granular chega a 40 ms, além da análise de afinação e dos buffers/drivers; o tempo de um buffer isolado não representa a latência total.
- O algoritmo atual não preserva formantes como um afinador vocal de estúdio. Qualidade perceptiva e latência devem ser avaliadas com voz real no Windows.
- Arquivos a 44,1/48 kHz são reamostrados para a taxa da sessão antes da reprodução e exportação. O instrumental completo começa mutado quando seus componentes também estão carregados, evitando duplicação.
- O salvamento de letras é atômico e é concluído antes de trocar, exportar ou fechar. Uma falha mantém o texto no editor e impede o fechamento.
- Testes de streams usam dispositivos simulados; a validação de VB-Cable, Discord, OBS e estabilidade prolongada em hardware continua necessária.
