import pandas as pd
import sqlite3
from datetime import datetime
import os

def sincronizar_dados():
    try:
        # Lê o arquivo Excel
        print("Lendo arquivo Excel...")
        df_excel = pd.read_excel('clientes.xlsx')
        print(f"Registros no Excel: {len(df_excel)}")

        # Conecta ao SQLite
        print("\nConectando ao banco SQLite...")
        conn = sqlite3.connect('crm.db')
        cursor = conn.cursor()

        # Verifica registros no SQLite
        cursor.execute('SELECT COUNT(*) FROM leads')
        count_sqlite = cursor.fetchone()[0]
        print(f"Registros no SQLite: {count_sqlite}")

        # Importa dados do Excel para o SQLite
        print("\nImportando dados do Excel para o SQLite...")
        df_excel.to_sql('leads', conn, if_exists='replace', index=False)
        
        # Verifica se a importação foi bem sucedida
        cursor.execute('SELECT COUNT(*) FROM leads')
        count_final = cursor.fetchone()[0]
        print(f"Registros após sincronização: {count_final}")

        conn.close()
        print("\nSincronização concluída com sucesso!")
        return True

    except Exception as e:
        print(f"\nErro durante a sincronização: {str(e)}")
        return False

if __name__ == '__main__':
    # Cria backup antes de sincronizar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs('backups_emergencia', exist_ok=True)
    
    print("Criando backups...")
    os.system(f'copy clientes.xlsx backups_emergencia\\clientes_backup_{timestamp}.xlsx')
    os.system(f'copy crm.db backups_emergencia\\crm_backup_{timestamp}.db')
    
    print("\nIniciando sincronização...")
    if sincronizar_dados():
        print("\nSincronização concluída com sucesso!")
    else:
        print("\nErro durante a sincronização. Verifique os backups em backups_emergencia/") 