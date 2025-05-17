import pandas as pd
from datetime import datetime

def formatar_data(data):
    try:
        if pd.isna(data):
            return ''
        # Tenta converter para datetime se for string
        if isinstance(data, str):
            # Remove qualquer texto adicional e espaços
            data = data.strip()
            # Tenta diferentes formatos de data
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%y']:
                try:
                    data = datetime.strptime(data, fmt)
                    break
                except:
                    continue
        # Se já for datetime ou timestamp
        if isinstance(data, (datetime, pd.Timestamp)):
            return data.strftime('%d/%m/%Y')
        return ''
    except:
        return ''

def formatar_hora(hora):
    try:
        if pd.isna(hora):
            return ''
        if isinstance(hora, str):
            hora = hora.strip()
            # Remove qualquer texto adicional
            if ':' in hora:
                hora = hora.split(':')
                # Pega apenas hora e minuto
                return f"{int(hora[0])}:{hora[1].split()[0]}"
        return ''
    except:
        return ''

# Carregar a planilha
print("Carregando a planilha...")
df = pd.read_excel('clientes.xlsx')

# Identificar colunas de data e hora
colunas_data = ['Data AE', 'Data de contato']  # Adicione outras colunas de data se necessário
colunas_hora = ['Hora planejada AE']  # Adicione outras colunas de hora se necessário

# Formatar datas
print("Formatando datas...")
for coluna in colunas_data:
    if coluna in df.columns:
        df[coluna] = df[coluna].apply(formatar_data)

# Formatar horas
print("Formatando horas...")
for coluna in colunas_hora:
    if coluna in df.columns:
        df[coluna] = df[coluna].apply(formatar_hora)

# Salvar a planilha
print("Salvando alterações...")
df.to_excel('clientes.xlsx', index=False)
print("Concluído!") 