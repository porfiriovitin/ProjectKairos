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
6. Ao terminar a chegada, a mesma janela passa automaticamente para `OnibusDandoEmbarque.mp4`.
7. YOLO acompanha ônibus e pessoas nas plataformas 63 e 62; o painel mostra os estados e as notificações de cada viagem.

No vídeo padrão, a chegada simulada ocorre a partir de aproximadamente **20 segundos**. O evento não é disparado apenas pelo tempo: também depende da confirmação da empresa e do prefixo por leituras repetidas.

## Demonstração rápida

Depois da instalação, execute na raiz do projeto:

```powershell
.\venv\Scripts\python.exe src/main.py
```

A janela mostrará o vídeo processado e o painel de identificação. Use `Espaço` para pausar ou retomar e `Q` ou `Esc` para encerrar.

Resultado esperado: identificação do `BUS-001` (Itapemirim, prefixo `40366`), na rota São Paulo → Rio de Janeiro, às 14:30, com os passageiros mockados associados à viagem.

Na segunda cena, os ônibus são outros: à esquerda, plataforma **63**, `BUS-003`, Gontijo `19360`, São Paulo → Maringá; à direita, plataforma **62**, `BUS-002`, Gontijo `14080`, São Paulo → Recife. Os dados vêm da programação e os destinatários são relacionados por `bus_code` em `passengers.json`.

## Monitoramento de embarque

A interface mantém as caixas rastreadas, o painel lateral e os avisos visuais. Cada plataforma tem estado independente e contagem de pessoas visíveis na região de acesso ao ônibus.

| Evento | Evidência usada |
| --- | --- |
| `BUS_AT_PLATFORM` | Ônibus presente na região da plataforma por pelo menos 1 segundo. |
| `BUS_PARKED` | Posição estável em relação à placa da plataforma por 2,5 segundos, após histórico de movimento. |
| `BOARDING_STARTED` | Presença persistente de pessoas junto ao acesso, após a parada; informa a contagem daquele momento. |
| `BOARDING_FINISHED` | Acesso sem pessoas detectadas durante 12 segundos, após início do embarque, ou saída observada do ônibus. |
| `BUS_DEPARTED` | Ônibus rastreado fora da região de parada durante 2,5 segundos. |

São **heurísticas visuais de demonstração**, não reconhecimento de abertura de portas ou confirmação individual de embarque. A contagem é instantânea e estimada, inclui funcionários e não representa total de passageiros embarcados. Oclusões podem reduzir a contagem. A perda da detecção do ônibus, sozinha, não confirma saída nem encerramento.

A associação entre plataforma e viagem foi configurada conforme os ônibus informados para este vídeo; não é apresentada como identidade reconhecida pelo OCR. A calibração fica em `config/platforms.json`. As placas são acompanhadas por correspondência visual para compensar movimentos da câmera; os textos OCR continuam sendo desenhados quando disponíveis. Outra câmera exige nova calibração e validação.

O prefixo frontal também recebe uma caixa própria: sua região é localizada pela numeração escura na faixa amarela e lida no frame de resolução original. O fluxo óptico acompanha a caixa entre leituras. A legenda mostra somente o número da programação. A caixa fica verde após a primeira leitura literal coincidente, com confiança mínima de 0,50, e mantém a confirmação enquanto o mesmo ônibus ocupa a plataforma, inclusive durante falhas temporárias de OCR ou troca do ID de rastreamento. A saída do ônibus, alteração do prefixo esperado ou troca de cena encerra essa confirmação. A geometria da caixa continua sendo atualizada e expira sem evidência visual; a confirmação não mantém uma caixa parada na tela. Leituras parciais e associação pela plataforma não confirmam o OCR. Leituras brutas podem ser conferidas com `--debug`.

O ônibus da plataforma 63 já aparece estacionado no início: a aplicação registra sua presença, parada e saída, sem inventar um embarque não observado. O ônibus da plataforma 62 permanece estacionado no fim do vídeo; não é emitida uma saída artificial. Cada tipo de evento é notificado uma vez por viagem/plataforma/data nesta execução; reaberturas de embarque e múltiplas viagens sucessivas na mesma plataforma ficam fora deste perfil de demonstração.

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

Ou copie toda a pasta `Backend` para a nova máquina. Ela precisa incluir `src`, `config`, `requirements.txt`, `requirements-cuda.txt`, `bus_schedules.json`, `passengers.json` e os dois vídeos em `src/videos/`.

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

# Executa somente o vídeo de chegada
.\venv\Scripts\python.exe src/main.py --single-video

# Executa somente a cena de embarque
.\venv\Scripts\python.exe src/main.py --source src/videos/OnibusDandoEmbarque.mp4

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

Na cena de embarque, o padrão é `--boarding-imgsz 640`, para melhorar a detecção de pessoas. `--max-seconds` limita a duração total da sequência. `--snapshot` salva a imagem da chegada e outra com sufixo `-boarding` após o início do embarque. O relatório reúne eventos e métricas das duas cenas. Para outra fonte de embarque, use `--scene boarding --source <fonte> --platform-config <calibracao.json>`.

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
    platform_geometry.py          Referências visuais das plataformas
    overlay.py                    Interface de visualização OpenCV
  services/
    bus_matcher.py                Leitura dos mocks e identificação
    arrival.py                    Estado da chegada e deduplicação
    boarding.py                   Estados de embarque e contagem por plataforma
    notification_service.py       Eventos e notificações no console
tests/
  test_boarding.py
  test_matching_and_arrival.py
  test_text_tracker.py
config/
  platforms.json                  Calibração da cena de embarque
```

O painel em `Frontend` recebe os eventos por WebSocket local em `ws://127.0.0.1:8765`. O transporte envia programação, passageiros, histórico e vídeo com as caixas de visão computacional, sem o painel lateral OpenCV. O limite padrão é 20 FPS (`--stream-fps`), condicionado à velocidade da inferência. A codificação JPEG ocorre em outra thread; imagens antigas são substituídas para não acumular atraso. Execute `src/main.py --headless --keep-dashboard` para manter o histórico acessível após o vídeo; `--ws-host` e `--ws-port` configuram o endereço, e `--no-websocket` desativa o transporte. Na raiz, `iniciar.bat` abre ambas as aplicações e exibe o vídeo no navegador. Consulte [a documentação do painel](../Frontend/README-PAINEL.md).

## Verificação

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
.\venv\Scripts\python.exe -m pip check
```

Os testes cobrem confirmação temporal, OCR aproximado, viagens ambíguas, isolamento do matching, passageiros, zona de chegada e deduplicação após troca de track.

Também cobrem estados de embarque, separação das plataformas, contagem, movimento da câmera, falhas de detecção e destinatários das notificações. A sequência completa foi validada sem janela na RTX 4060: aproximadamente 126,7 segundos de execução para 126,5 segundos de vídeo, 17,84 frames analisados por segundo e 758 MB de pico de memória alocada pelo PyTorch. Frames atrasados são descartados para manter o tempo real; isso não significa inferência em todos os 60 FPS do vídeo.

## Referências

- [Rastreamento no Ultralytics](https://docs.ultralytics.com/modes/track/)
- [Documentação do EasyOCR](https://www.jaided.ai/easyocr/documentation/)
- [PyTorch e CUDA](https://pytorch.org/get-started/previous-versions/)
