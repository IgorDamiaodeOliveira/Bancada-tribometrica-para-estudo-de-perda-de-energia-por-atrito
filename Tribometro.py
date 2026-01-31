import serial
import time
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import csv
import os
import numpy as np # Necessário para cálculos matemáticos
import math

#  CONFIGURAÇÕES DE CONEXÃO
PORTA_ARDUINO = 'COM13'  
BAUD_RATE = 9600
ARQUIVO_CSV = 'experimento_completo.csv'

# PARÂMETROS DO OBJETO (VARIAR) 
MASSA_KG = 0.04  # Ex: 200g = 0.2 kg (Altere para o peso real do seu carrinho/bloco)
GRAVIDADE = 9.81  # m/s^2
LIXACORPO = 220 
LIXAMESA = 80

# Configuração do Filtro
JANELA_FILTRO = 9 # alta devido a aceleração

def conectar_arduino():
    try:
        print(f"🔌 Conectando em {PORTA_ARDUINO}...")
        ser = serial.Serial(PORTA_ARDUINO, BAUD_RATE, timeout=1)
        print("⏳ Aguardando inicialização...")
        
        start_wait = time.time()
        while True:
            if time.time() - start_wait > 15:
                print("❌ Timeout.")
                return None
            if ser.in_waiting:
                linha = ser.readline().decode('utf-8', errors='ignore').strip()
                if "Digite o angulo" in linha or "Sistema Pronto" in linha:
                    print("✅ Arduino Pronto!")
                    break
        return ser
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None

def realizar_teste_streaming(arduino):
    print("\n--- 🏎️ TESTE DE TRIBOMETRO ---")
    try:
        angulo = float(input("📐 Ângulo da Rampa (graus): "))
    except ValueError:
        return

    print(f"📤 Inclinando para {angulo}°...")
    arduino.reset_input_buffer()
    arduino.write(f"{angulo}\n".encode())

    # Aguarda Motor
    while True:
        try:
            linha = arduino.readline().decode('utf-8', errors='ignore').strip()
            if "Chegou" in linha:
                print("✅ Rampa posicionada. Solte o objeto!")
                break
        except: break

    # Captura Dados
    dados_tempo = []
    dados_distancia = []
    gravando = False
    start_stream_wait = time.time()

    while True:
        if (time.time() - start_stream_wait) > 10: break

        if arduino.in_waiting:
            linha = arduino.readline().decode('utf-8', errors='ignore').strip()
            
            if "START_STREAM" in linha:
                print("🔴 Gravando...")
                gravando = True
                continue
            if "END_STREAM" in linha:
                print("⏹️ Fim da gravação.")
                break
            
            if gravando and "," in linha:
                try:
                    p = linha.split(',')
                    t_s = int(p[0]) / 1000.0
                    d_cm = float(p[1])
                    if 0 < d_cm < 400: 
                        dados_tempo.append(t_s) 
                        dados_distancia.append(d_cm)
                except: pass

    if len(dados_tempo) > 10:
        processar_fisica(dados_tempo, dados_distancia, angulo)
    else:
        print("⚠️ Dados insuficientes.")

def processar_fisica(tempos, distancias, angulo_graus):
    """Realiza todos os cálculos físicos e plota 4 gráficos"""
    
    # 1. Preparar Dados no Pandas
    df = pd.DataFrame({'t': tempos, 's_cm': distancias})
    
    # 2. Filtragem (Crucial para derivadas não explodirem)
    df['s_filt'] = df['s_cm'].rolling(window=JANELA_FILTRO, center=True).median()
    df['s_filt'] = df['s_filt'].fillna(df['s_cm']) # Preenche bordas
    
    # Converter para Sistema Internacional (Metros)
    # O sensor está no TOPO e mede a distância aumentando
    # S = posição na rampa. 
    df['s_m'] = df['s_filt'] / 100.0
    
    # 3. CÁLCULOS CINEMÁTICOS (Derivadas Numéricas)
    # dt é o intervalo de tempo entre medidas
    dt = np.gradient(df['t'])
    
    # Velocidade (v = ds/dt)
    df['v'] = np.gradient(df['s_m'], df['t'])
    
    # Aceleração (a = dv/dt)
    # Aceleração costuma ser muito ruidosa, aplicamos um filtro extra nela ou na velocidade
    df['v_smooth'] = df['v'].rolling(window=5, center=True).mean().fillna(df['v'])
    df['a'] = np.gradient(df['v_smooth'], df['t'])

    # 4. CÁLCULOS DINÂMICOS & ENERGIA
    theta_rad = math.radians(angulo_graus)
    sen_t = math.sin(theta_rad)
    cos_t = math.cos(theta_rad)
    
    # Altura (h): Assumindo que d=0 é o topo. h diminui conforme d aumenta.
    # Definimos h = 0 no ponto final da medição para facilitar referência
    dist_max = df['s_m'].max()
    df['h'] = (dist_max - df['s_m']) * sen_t
    
    # Energias (Joules)
    df['U'] = MASSA_KG * GRAVIDADE * df['h']       # Potencial Gravitacional
    df['K'] = 0.5 * MASSA_KG * (df['v']**2)        # Cinética
    df['E_mec'] = df['U'] + df['K']                # Mecânica Total
    
    # Perda de Energia (Acumulada)
    # Quanto de energia "sumiu" desde o início do movimento
    E_inicial = df['E_mec'].iloc[0] # Ou a média dos primeiros pontos
    df['Perda_Energia'] = E_inicial - df['E_mec'] 
    
    # 5. CÁLCULO DO ATRITO DINÂMICO (Instantâneo)
    # mu = tan(theta) - a / (g * cos(theta))
    # Evita divisão por zero e valores absurdos gerados por ruído no início
    df['mu_d'] = math.tan(theta_rad) - (df['a'] / (GRAVIDADE * cos_t))
    
    # Limpeza de ruídos matemáticos no coeficiente (filtro de saturação)
    df['mu_d'] = df['mu_d'].clip(lower=0, upper=1.0) 

    # 6. TRABALHO DA FORÇA DE ATRITO
    # Força Normal N = m * g * cos(theta)
    # Fat = mu * N
    # Trabalho = Integral de Fat * ds
    # Como mu varia (devido ao ruído), calculamos o trabalho incremental dW = Fat * ds
    
    Normal = MASSA_KG * GRAVIDADE * cos_t
    df['Fat_inst'] = df['mu_d'] * Normal
    
    # Deslocamento incremental (ds)
    ds = np.gradient(df['s_m'])
    df['Trab_Fat_Inc'] = df['Fat_inst'] * ds
    df['Trab_Fat_Acumulado'] = df['Trab_Fat_Inc'].cumsum()

    # --- PLOTAGEM DOS 4 GRÁFICOS ---
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'Análise Física Completa - Rampa {angulo_graus}°', fontsize=16)
    
    # Gráfico 1: Trajetória e Velocidade
    ax1 = axs[0, 0]
    ax1.plot(df['t'], df['s_m'], label='Posição (m)', color='blue')
    ax1b = ax1.twinx() # Eixo secundário
    ax1b.plot(df['t'], df['v'], label='Velocidade (m/s)', color='orange', linestyle='--')
    ax1.set_title('Cinemática')
    ax1.set_xlabel('Tempo (s)')
    ax1.set_ylabel('Posição (m)')
    ax1b.set_ylabel('Velocidade (m/s)')
    ax1.legend(loc='upper left')
    ax1b.legend(loc='lower right')

    # Gráfico 2: Conservação de Energia
    ax2 = axs[0, 1]
    ax2.plot(df['t'], df['U'], label='Potencial (U)', color='green')
    ax2.plot(df['t'], df['K'], label='Cinética (K)', color='red')
    ax2.plot(df['t'], df['E_mec'], label='Mecânica Total (E)', color='black', linewidth=2)
    ax2.set_title('Energias (Joules)')
    ax2.set_xlabel('Tempo (s)')
    ax2.set_ylabel('Energia (J)')
    ax2.legend()
    ax2.grid(True, linestyle='--', alpha=0.5)

    # Gráfico 3: Coeficiente de Atrito Dinâmico
    ax3 = axs[1, 0]
    # Filtramos para mostrar apenas quando há movimento real (v > 0.05)
    mask_mov = df['v'] > 0.05 
    ax3.plot(df.loc[mask_mov, 't'], df.loc[mask_mov, 'mu_d'], color='purple', alpha=0.6)
    # Linha média
    mu_medio = df.loc[mask_mov, 'mu_d'].mean()
    ax3.axhline(mu_medio, color='black', linestyle='--', label=f'Média = {mu_medio:.3f}')
    ax3.set_title('Coeficiente de Atrito Dinâmico Estimado')
    ax3.set_xlabel('Tempo (s)')
    ax3.set_ylabel('µ Dinâmico')
    ax3.set_ylim(0, 1.0) # Limita eixo Y para não distorcer com ruídos
    ax3.legend()

    # Gráfico 4: Comparação Trabalho vs Perda
    ax4 = axs[1, 1]
    ax4.plot(df['t'], df['Perda_Energia'], label='Perda de Energia Mecânica (ΔE)', color='red')
    ax4.plot(df['t'], df['Trab_Fat_Acumulado'], label='Trabalho do Atrito (W_fat)', color='blue', linestyle='--')
    ax4.set_title('Trabalho Não-Conservativo vs Perda Energética')
    ax4.set_xlabel('Tempo (s)')
    ax4.set_ylabel('Energia / Trabalho (J)')
    ax4.fill_between(df['t'], df['Perda_Energia'], df['Trab_Fat_Acumulado'], color='gray', alpha=0.2, label='Erro Experimental')
    ax4.legend()
    ax4.grid(True)

    plt.tight_layout()
    plt.show()
    
    # Salva CSV Detalhado
    df.to_csv(f"analise_fisica_{angulo_graus}.csv", index=False)
    print(f"💾 Dados detalhados salvos em 'analise_fisica_{angulo_graus}GRAUS_{MASSA_KG}KG_C{LIXACORPO}_L{LIXAMESA}.csv'")
    print("📂 O arquivo será salvo em:", os.getcwd())
def main():
    arduino = conectar_arduino()
    if not arduino: return
    while True:
        opt = input("\n[Enter] Novo Teste | [S] Sair: ")
        if opt.lower() == 's': break
        realizar_teste_streaming(arduino)
    arduino.close()

if __name__ == "__main__":
    main()