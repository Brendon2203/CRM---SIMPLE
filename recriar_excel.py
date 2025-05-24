import pandas as pd
import sqlite3
import os
from datetime import datetime

def recriar_excel():
    try:
        print("Conectando ao banco SQLite...")
        conn = sqlite3.connect('crm.db')
        
        print("Lendo dados do banco...")
        df = pd.read_sql_query("SELECT * FROM leads", conn)
        
        print(f"Encontrados {len(df)} registros")
        
        # Cria backup do arquivo atual se existir
        if os.path.exists('clientes.xlsx'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.rename('clientes.xlsx', f'clientes_backup_{timestamp}.xlsx')
            print("Backup do arquivo Excel atual criado")
        
        print("Criando novo arquivo Excel...")
        df.to_excel('clientes.xlsx', index=False)
        
        print("Verificando se o arquivo foi criado corretamente...")
        df_verificar = pd.read_excel('clientes.xlsx')
        print(f"Arquivo criado com {len(df_verificar)} registros")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro ao recriar arquivo Excel: {str(e)}")
        return False

if __name__ == '__main__':
    if recriar_excel():
        print("\nArquivo Excel recriado com sucesso!")
    else:
        print("\nErro ao recriar arquivo Excel!") 