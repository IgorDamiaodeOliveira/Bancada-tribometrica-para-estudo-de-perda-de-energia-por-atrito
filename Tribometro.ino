#include <Servo.h>
#include <Wire.h>

Servo meuServo;

//  PINAGEM 
const int pinoServo = 10;   
const int pinoTrig = 7;     
const int pinoEcho = 6;     

// CALIBRAÇÃO DO SERVO (Rotação Contínua)
const int pontoMorto = 60;        
const int velocidadePositiva = 85; 
const int velocidadeNegativa = 40;

// Endereço do Giroscópio
const int MPU_ADDR = 0x68;

// Variáveis Globais
float anguloAtualX = 0;
float erroGiroX = 0; 
unsigned long tempoAnteriorGiro = 0;
unsigned long tempoAnteriorSonar = 0; 


// SETUP

void setup() {
  Serial.begin(9600);
  Wire.begin();
  
  // Configuração dos Pinos
  pinMode(pinoTrig, OUTPUT);
  pinMode(pinoEcho, INPUT);
  meuServo.attach(pinoServo);
  meuServo.write(pontoMorto); 

  // Inicializa MPU6050
  Serial.println("Iniciando MPU6050...");
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);
  Wire.write(0);    
  Wire.endTransmission(true);

  // Calibração do Giroscópio
  Serial.println("Calibrando Giroscopio... MANTENHA PARADO!");
  long soma = 0;
  // Precisamos da função lerGiroX_Raw aqui, ela está definida no fim do arquivo
  for(int i = 0; i < 1000; i++) {
    soma += lerGiroX_Raw();
    delay(3);
  }
  erroGiroX = soma / 1000.0;
  
  // MENSAGEM 
  Serial.println("--- Sistema Pronto: Digite o angulo ---"); 
  
  tempoAnteriorGiro = millis();
}


// LOOP PRINCIPAL

void loop() {
  // Mantém o ângulo atualizado o tempo todo
  atualizarAnguloX();

  if (Serial.available() > 0) {
    // Lê a string inteira até o 'Enter' para limpar o buffer corretamente
    String leitura = Serial.readStringUntil('\n');
    leitura.trim(); // Remove espaços extras

    if (leitura.length() > 0) {
      float anguloAlvo = leitura.toFloat();
      
      // Se recebeu um ângulo válido (diferente de zero), executa a sequência
      if (anguloAlvo != 0) {
        // 1. Move a rampa
        moverAteAngulo(anguloAlvo);
        
        // 2. Grava os dados da descida
        executarStreamingDados();
      }
    }
  }
}


// FUNÇÕES AUXILIARES 

// 1. Lógica do Giroscópio (Leitura RAW)
int16_t lerGiroX_Raw() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x43); // Registrador do Eixo X do Giroscópio
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 2, true);
  
  int16_t eixoX = Wire.read() << 8 | Wire.read();
  return eixoX;
}

// 2. Atualização do Ângulo (Integração no tempo)
void atualizarAnguloX() {
  unsigned long tempoAtual = millis();
  float dt = (tempoAtual - tempoAnteriorGiro) / 1000.0; 
  tempoAnteriorGiro = tempoAtual;

  float leituraRaw = lerGiroX_Raw();
  float velocidadeAngular = (leituraRaw - erroGiroX) / 131.0;

  // Zona morta para evitar drift quando parado
  if (abs(velocidadeAngular) < 1.5) { 
    velocidadeAngular = 0;
  }

  anguloAtualX += velocidadeAngular * dt;
}

// 3. Movimento do Motor
void moverAteAngulo(float grausDesejados) {
  anguloAtualX = 0; // Zera para movimento relativo
  
  Serial.print(">>> Movendo para: ");
  Serial.println(grausDesejados);

  if (grausDesejados > 0) {
    meuServo.write(velocidadePositiva); 
  } else {
    meuServo.write(velocidadeNegativa); 
  }

  bool chegou = false;
  
  while (!chegou) {
    atualizarAnguloX();
    
    if (abs(anguloAtualX) >= abs(grausDesejados)) {
      chegou = true;
    }
  }

  meuServo.write(pontoMorto); 
  delay(1000); // Espera 1s para estabilizar a rampa
  
  Serial.println(">>> Chegou"); // Avisa o Python
}

// 4. Leitura Ultrassônica Rápida (Para o Streaming)
float lerUltrassomRapido() {
  digitalWrite(pinoTrig, LOW);
  delayMicroseconds(2);
  digitalWrite(pinoTrig, HIGH);
  delayMicroseconds(10);
  digitalWrite(pinoTrig, LOW);
  
  // Timeout curto (25ms) para garantir alta taxa de quadros (fps)
  long duration = pulseIn(pinoEcho, HIGH, 25000); 
  
  if (duration == 0) return -1.0;
  return duration * 0.034 / 2;
}

// 5. Execução do Streaming (Envia dados para o Python)
void executarStreamingDados() {
  Serial.println("START_STREAM");
  
  unsigned long tempoInicial = millis();
  unsigned long tempoAtual = 0;
  
  // Grava por 3 segundos
  while (tempoAtual < 3000) { 
    atualizarAnguloX(); // Mantém o gyro vivo em background
    
    tempoAtual = millis() - tempoInicial;
    float dist = lerUltrassomRapido();
    
    // Formato CSV: TEMPO,DISTANCIA
    Serial.print(tempoAtual);
    Serial.print(",");
    Serial.println(dist);
    
    delay(35); // Controla a taxa de amostragem
  }
  
  Serial.println("END_STREAM");
}