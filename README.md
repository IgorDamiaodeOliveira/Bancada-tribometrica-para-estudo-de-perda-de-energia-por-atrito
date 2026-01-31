# Bancada_tribom-trica_para_estudo_de_perda_de_energia_por_atrito
# Bancada de Análise Tribométrica Automatizada

![Badge Status](https://img.shields.io/badge/Status-Funcional-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Arduino](https://img.shields.io/badge/Hardware-Arduino-teal)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

Este repositório contém o código-fonte (Firmware e Software de Análise) para uma bancada experimental automatizada destinada ao estudo de **tribologia**. O sistema permite a análise precisa do coeficiente de atrito dinâmico e da conservação de energia em planos inclinados.

## Sobre o Projeto

O projeto integra hardware e software para eliminar erros humanos na medição de experimentos de física.
1.  **O Arduino** controla a inclinação da rampa usando um giroscópio para feedback preciso e coleta dados de distância via ultrassom.
2.  **O Python** recebe os dados, aplica filtros de processamento de sinal (Rolling Median), calcula derivadas numéricas (velocidade e aceleração) e plota gráficos físicos detalhados.

---

## Hardware e Pinagem

### Componentes Necessários
* **Microcontrolador:** Arduino Uno ou Nano.
* **Sensor Inercial:** MPU6050 (Acelerômetro e Giroscópio).
* **Sensor de Distância:** HC-SR04 (Ultrassônico).
* **Atuador:** Servo Motor de Rotação Contínua (360°).
* **Mecânica:** Estrutura de rampa basculante.

### Esquema de Ligação (Wiring)

| Componente | Pino Arduino | Função |
| :--- | :--- | :--- |
| **Servo Motor** | D10 | Controle PWM da inclinação |
| **HC-SR04 (Trig)** | D7 | Disparo do pulso ultrassônico |
| **HC-SR04 (Echo)** | D6 | Leitura do retorno (Echo) |
| **MPU6050 (SDA)** | A4 | Comunicação I2C (Dados) |
| **MPU6050 (SCL)** | A5 | Comunicação I2C (Clock) |
| **VCC/GND** | 5V/GND | Alimentação (Recomenda-se fonte externa para o Servo) |

---

## Instalação e Execução

### 1. Firmware (Arduino)
1.  Abra o arquivo `.ino` na **Arduino IDE**.
2.  Instale as bibliotecas necessárias:
    * `Wire.h` (Nativa)
    * `Servo.h` (Nativa)
3.  Carregue o código para a placa.
4.  **Calibração:** Ao ligar, mantenha a rampa parada para que o giroscópio calibre o "zero".

### 2. Software de Análise (Python)
1.  Certifique-se de ter o Python 3.x instalado.
2.  Instale as dependências executando o comando abaixo no terminal:
    ```bash
    pip install pyserial pandas seaborn matplotlib numpy
    ```
3.  Abra o arquivo `.py` e verifique a variável de porta:
    ```python
    PORTA_ARDUINO = 'COM13' # Ajuste para sua porta (ex: COM3 ou /dev/ttyUSB0)
    ```
4.  Execute o script:
    ```bash
    python main.py
    ```

---

## Como Utilizar

1.  Com o script Python rodando, o terminal mostrará: `✅ Arduino Pronto!`.
2.  Digite o **ângulo alvo** (ex: `25` graus) e pressione Enter.
3.  A rampa se ajustará automaticamente. Aguarde a mensagem: `>>> Chegou`.
4.  O terminal pedirá para soltar o objeto. **Solte o corpo de prova**.
5.  O sistema gravará o movimento por 3 segundos.
6.  Ao final, serão exibidos 4 gráficos de análise e gerado um arquivo `.csv` com os dados brutos e processados.

---

## Fundamentos Físicos

O software realiza o pós-processamento dos dados brutos $(t, s)$ baseando-se nas leis de Newton:

### 1. Coeficiente de Atrito Dinâmico ($\mu_d$)
Estimado a partir da aceleração média durante a descida:
$$\mu_d = \tan(\theta) - \frac{a}{g \cdot \cos(\theta)}$$

### 2. Conservação de Energia
Calcula-se a Energia Mecânica Total ($E_{mec}$) em cada instante:
$$E_{mec} = U + K = (mgh) + \left(\frac{1}{2}mv^2\right)$$

### 3. Trabalho de Forças Não-Conservativas
O código verifica se a variação da energia mecânica corresponde ao trabalho realizado pelo atrito:
$$W_{fat} = \int \vec{F}_{at} \cdot d\vec{s}$$



## 📝 Licença

Este projeto está licenciado sob a licença MIT.
