# Projeto Kairos

O passageiro não deveria esperar no escuro, sem saber onde está o ônibus ou quando poderá embarcar. O **Projeto Kairos** ajuda aplicativos de venda de passagens a transformar esse momento em uma experiência mais tranquila, previsível e confortável.

Com visão computacional, a solução acompanha a chegada do ônibus no terminal, identifica o veículo no vídeo, lê informações visíveis com OCR e compara os dados com a programação. Quando a chegada é confirmada, o aplicativo pode informar o passageiro no momento certo. É uma base para oferecer mais transparência e suporte durante toda a jornada de viagem, desde a compra da passagem até o embarque.

## O momento certo

**Kairos** significa “o momento certo”. Aplicativos de venda de passagem dizem quando o ônibus **deveria** chegar; o Kairos identifica quando ele **realmente chegou** e leva essa informação ao passageiro em tempo real.

> **Sobre a demonstração:** os vídeos, a programação de viagens e os passageiros deste repositório são dados **mockados**, criados para apresentar o fluxo completo. A implementação, porém, é funcional: YOLO detecta e rastreia os ônibus, EasyOCR realiza as leituras e o sistema confirma a identidade antes de registrar a chegada. A fonte pode ser trocada por uma câmera local ou RTSP para integração com um cenário real.

## O que acontece na demonstração

1. O vídeo é analisado continuamente.
2. Os ônibus são detectados e recebem um ID de rastreamento.
3. A aplicação procura empresa, prefixo e letreiro no veículo.
4. As leituras são comparadas à programação disponível.
5. Após confirmações consecutivas, o evento `BUS_ARRIVED` é exibido com os passageiros que devem ser notificados.

No vídeo padrão, a chegada simulada ocorre a partir de aproximadamente **20 segundos**. O evento não é disparado apenas pelo tempo: também depende da confirmação da empresa e do prefixo por leituras repetidas.

## Demonstração rápida

Depois da instalação, execute na raiz do projeto:

```powershell
.\venv\Scripts\python.exe src/main.py
```

A janela mostrará o vídeo processado e o painel de identificação. Use `Espaço` para pausar ou retomar e `Q` ou `Esc` para encerrar.

Resultado esperado: identificação do `BUS-001` (Itapemirim, prefixo `40366`), na rota São Paulo → Rio de Janeiro, às 14:30, com os passageiros mockados associados à viagem.

## Instalação em outra máquina (Windows)

### 1. Pré-requisitos

Instale estes itens antes de copiar ou clonar o projeto:

- [Python 3.13](https://www.python.org/downloads/) — marque **Add Python to PATH** durante a instalação.
- Git, caso queira clonar o repositório. Também é possível copiar a pasta completa do projeto.
- Driver NVIDIA atualizado, somente se a máquina tiver uma GPU NVIDIA e você quiser usar aceleração CUDA.

Abra o PowerShell e confirme o Python:

```powershell
python --version
```

O comando deve mostrar `Python 3.13.x`.

### 2. Obtenha o projeto

Com Git:

```powershell
git clone <URL_DO_REPOSITORIO>
cd Backend
```

Ou copie toda a pasta `Backend` para a nova máquina. Ela precisa incluir `src`, `requirements.txt`, `requirements-cuda.txt`, `bus_schedules.json`, `passengers.json` e o vídeo em `src/videos/`.

### 3. Crie um ambiente virtual

Na raiz do projeto:

```powershell
python -m venv venv
```

### 4. Instale as dependências

Para qualquer máquina, inclusive sem GPU:

```powershell
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Para usar uma GPU NVIDIA compatível com CUDA, execute também:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-cuda.txt
```

Esse segundo arquivo instala a versão do PyTorch para CUDA 12.8. Em computadores sem NVIDIA, simplesmente não execute esse passo: o projeto funciona em CPU, com menor desempenho.

### 5. Baixe e valide os modelos

Na primeira execução, os modelos podem ser baixados. Prepare tudo antes de apresentar:

```powershell
.\venv\Scripts\python.exe src/main.py --prepare
```

Os arquivos ficam em `models/` e `.cache/`. Após esse preparo, não é preciso baixá-los novamente enquanto essas pastas forem mantidas.

### 6. Execute

```powershell
.\venv\Scripts\python.exe src/main.py
```

Se preferir ativar o ambiente virtual primeiro:

```powershell
.\venv\Scripts\Activate.ps1
python src/main.py
```

Caso o PowerShell bloqueie a ativação, use o primeiro formato com `venv\Scripts\python.exe`; ele não depende da política de execução.

## GPU ou CPU

O programa escolhe CUDA automaticamente quando há uma GPU NVIDIA compatível. Para conferir ou controlar a escolha:

```powershell
# Força a execução em CPU
.\venv\Scripts\python.exe src/main.py --device cpu

# Exige a primeira GPU NVIDIA
.\venv\Scripts\python.exe src/main.py --device 0

# Mantém OCR na CPU para economizar memória da GPU
.\venv\Scripts\python.exe src/main.py --ocr-device cpu
```

Como referência, o projeto foi testado com i5 de 12ª geração + GTX 1650 e Ryzen 5600 + RTX 4060 8 GB. O desempenho depende da máquina e deve ser medido no ambiente final.

## Comandos úteis

```powershell
# Exibe leituras OCR, candidatos e scores no console
.\venv\Scripts\python.exe src/main.py --debug

# Altera o instante da chegada simulada no MP4 padrão
.\venv\Scripts\python.exe src/main.py --arrival-seconds 18

# Executa sem abrir janela e salva relatório e imagem da chegada
.\venv\Scripts\python.exe src/main.py --headless --report outputs/report.json --snapshot outputs/arrival.png

# Processa todos os frames e exporta um vídeo anotado para auditoria
.\venv\Scripts\python.exe src/main.py --offline --headless --output outputs/demo.mp4 --report outputs/offline-report.json

# Usa câmera local ou uma fonte RTSP. Nesse modo, a chegada é definida por zona.
.\venv\Scripts\python.exe src/main.py --source 0 --date 15/09/2026
.\venv\Scripts\python.exe src/main.py --source rtsp://servidor/camera --date 15/09/2026
```

Para vídeos, a aplicação reduz a imagem para até 1280 px de largura e usa entrada YOLO de 480 px por padrão. Use `--imgsz 640` para maior resolução do detector, considerando o impacto no desempenho.

## Como a identificação funciona

- **YOLO11n** detecta os ônibus e **ByteTrack** mantém o ID de cada veículo entre os frames.
- **EasyOCR** lê os recortes do ônibus. As caixas de texto são acompanhadas por fluxo óptico enquanto a leitura permanece válida.
- Empresa e prefixo são comparados com todos os candidatos do JSON, usando normalização e similaridade textual.
- A confirmação exige ao menos três amostras OCR, evidências repetidas de empresa e prefixo e uma margem sobre o segundo candidato.
- A chave `(data, bus_code)` evita eventos duplicados, mesmo se o rastreador atribuir outro ID ao mesmo ônibus.

A zona de chegada considera o centro inferior da caixa do ônibus. O padrão é `--zone 0.35 0.65 0.95 0.98`, em coordenadas normalizadas de 0 a 1, e exige três observações consecutivas. Ajuste esses valores ao enquadramento de uma câmera real.

## Estrutura do projeto

```text
src/
  main.py                         Execução e métricas
  config.py                       Argumentos e caminhos do projeto
  vision/
    video_processor.py            Vídeo ou captura com buffer limitado
    detector.py                   YOLO + ByteTrack
    ocr_reader.py                 OCR assíncrono
    text_tracker.py               Fluxo óptico para textos
    overlay.py                    Interface de visualização OpenCV
  services/
    bus_matcher.py                Leitura dos mocks e identificação
    arrival.py                    Estado da chegada e deduplicação
    notification_service.py       Eventos e notificações no console
tests/
  test_matching_and_arrival.py
  test_text_tracker.py
```

Para uma integração futura, substitua a implementação de `NotificationService.notify` pelo transporte desejado, como API, fila ou WebSocket. Os módulos de visão não dependem desse transporte.

## Verificação

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
.\venv\Scripts\python.exe -m pip check
```

Os testes cobrem confirmação temporal, OCR aproximado, viagens ambíguas, isolamento do matching, passageiros, zona de chegada e deduplicação após troca de track.

## Referências

- [Rastreamento no Ultralytics](https://docs.ultralytics.com/modes/track/)
- [Documentação do EasyOCR](https://www.jaided.ai/easyocr/documentation/)
- [PyTorch e CUDA](https://pytorch.org/get-started/previous-versions/)
