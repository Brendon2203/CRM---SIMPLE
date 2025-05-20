from flask import Flask, render_template, request, redirect, url_for, send_file, session, jsonify, flash
import pandas as pd
from datetime import datetime
import os
import re
import bcrypt
from config import USERNAME, PASSWORD
import locale
import requests
import shutil

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'

# Caminhos dos arquivos Excel
PLANILHA_PATH = 'clientes.xlsx'
USUARIOS_PATH = 'usuarios.xlsx'

# Configurar locale para português
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except:
        pass

# Configuração do Pipedrive
PIPEDRIVE_API_TOKEN = 'c608bd29e6637e1bd3bbfa641fa818c70abf3204'

def formatar_data(data_str):
    try:
        if pd.isna(data_str):
            return ''
            
        # Se já for datetime ou timestamp
        if isinstance(data_str, (datetime, pd.Timestamp)):
            data = data_str
        else:
            # Converter a string da data para objeto datetime
            try:
                data = datetime.strptime(str(data_str).strip(), '%d/%m/%Y')
            except:
                return "Data inválida"
        
        # Dicionário de dias da semana em português
        dias = {
            'Monday': 'Segunda',
            'Tuesday': 'Terça',
            'Wednesday': 'Quarta',
            'Thursday': 'Quinta',
            'Friday': 'Sexta',
            'Saturday': 'Sábado',
            'Sunday': 'Domingo'
        }
        
        # Obter o nome do dia em inglês e converter para português
        dia_semana = dias[data.strftime('%A')]
        # Formatar a data no padrão brasileiro
        data_formatada = data.strftime('%d/%m/%Y')
        return f"{dia_semana} - {data_formatada}"
    except Exception as e:
        print(f"Erro ao formatar data: {e}")
        return "Data inválida"

def carregar_dados():
    df = pd.read_excel(PLANILHA_PATH)
    # Garantir que a coluna de data está no formato correto
    if 'data' in df.columns:
        df['data'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    return df

def salvar_dados(df):
    # Garantir que a data seja salva no formato DD/MM/YYYY
    if 'data' in df.columns:
        df['data'] = df['data'].dt.strftime('%d/%m/%Y')
    df.to_excel(PLANILHA_PATH, index=False)

def inicializar_usuarios():
    """Função para criar o arquivo de usuários se não existir"""
    if not os.path.exists(USUARIOS_PATH):
        df = pd.DataFrame(columns=['usuario', 'senha', 'funcao'])
        # Cria o usuário admin padrão
        senha = bcrypt.hashpw('1234'.encode('utf-8'), bcrypt.gensalt())
        df.loc[0] = ['admin', senha.decode('utf-8'), 'admin']
        df.to_excel(USUARIOS_PATH, index=False)

def verificar_senha(senha_digitada, senha_hash):
    """Verifica se a senha está correta"""
    return bcrypt.checkpw(senha_digitada.encode('utf-8'), senha_hash.encode('utf-8'))

def usuario_atual():
    """Retorna os dados do usuário atual"""
    if 'usuario' in session:
        df = pd.read_excel(USUARIOS_PATH)
        usuario = df[df['usuario'] == session['usuario']].iloc[0]
        return {
            'usuario': usuario['usuario'],
            'funcao': usuario['funcao']
        }
    return None

def requer_admin(f):
    """Decorator para rotas que requerem privilégios de admin"""
    def decorated_function(*args, **kwargs):
        user = usuario_atual()
        if not user or user['funcao'] != 'admin':
            return redirect(url_for('menu'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def carregar_leads():
    """Função auxiliar para carregar os leads do arquivo Excel"""
    try:
        if not os.path.exists(PLANILHA_PATH):
            print(f"Arquivo {PLANILHA_PATH} não encontrado!")
            return []
        df = pd.read_excel(PLANILHA_PATH)
        
        # Garante que a coluna 'Tipo aluno' existe
        if 'Tipo aluno' not in df.columns:
            df['Tipo aluno'] = ''
            df.to_excel(PLANILHA_PATH, index=False)
            
        leads = df.to_dict('records')
        print(f"Carregados {len(leads)} leads com sucesso!")
        return leads
    except Exception as e:
        print(f"Erro ao carregar leads: {str(e)}")
        return []

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Verifica se o arquivo de usuários existe
        inicializar_usuarios()
        
        # Carrega os usuários
        df = pd.read_excel(USUARIOS_PATH)
        
        # Procura o usuário
        user = df[df['usuario'] == username]
        if not user.empty and verificar_senha(password, user.iloc[0]['senha']):
            session['usuario'] = username
            return redirect(url_for('menu'))
        else:
            return render_template('login.html', erro='Usuário ou senha incorretos.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('login'))

@app.route('/usuarios', methods=['GET', 'POST'])
@requer_admin
def usuarios():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            funcao = request.form['funcao']
            
            df = pd.read_excel(USUARIOS_PATH)
            
            # Verifica se o usuário já existe
            if username in df['usuario'].values:
                return render_template('usuarios.html', 
                    erro='Este usuário já existe.',
                    usuarios=df.to_dict('records'))
            
            # Criptografa a senha
            senha_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Adiciona o novo usuário
            novo_usuario = pd.DataFrame([{
                'usuario': username,
                'senha': senha_hash.decode('utf-8'),
                'funcao': funcao
            }])
            
            df = pd.concat([df, novo_usuario], ignore_index=True)
            df.to_excel(USUARIOS_PATH, index=False)
            
            return render_template('usuarios.html', 
                sucesso='Usuário criado com sucesso!',
                usuarios=df.to_dict('records'))
            
        except Exception as e:
            return render_template('usuarios.html', 
                erro=f'Erro ao criar usuário: {str(e)}',
                usuarios=df.to_dict('records'))
    
    df = pd.read_excel(USUARIOS_PATH)
    return render_template('usuarios.html', usuarios=df.to_dict('records'))

@app.route('/excluir_usuario/<username>')
@requer_admin
def excluir_usuario(username):
    try:
        df = pd.read_excel(USUARIOS_PATH)
        
        # Não permite excluir o próprio usuário
        if username == session['usuario']:
            return jsonify({'success': False, 'error': 'Você não pode excluir seu próprio usuário.'})
        
        # Remove o usuário
        df = df[df['usuario'] != username]
        df.to_excel(USUARIOS_PATH, index=False)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/menu')
def menu():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html', user=usuario_atual())

@app.route('/baixar')
def baixar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return send_file(PLANILHA_PATH, as_attachment=True)

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Validação do número de telefone (obrigatório)
            numero = request.form['numero'].strip()
            if not numero or not re.match(r'^\(\d{2}\)[9]?\d{4}-\d{4}$', numero):
                return render_template('adicionar.html', 
                    erro='Número de telefone inválido.',
                    dados=request.form)

            # Verifica se o número já existe
            df = pd.read_excel(PLANILHA_PATH)
            numeros_existentes = df['Número'].astype(str).str.strip().tolist()
            if numero in numeros_existentes:
                return render_template('adicionar.html', 
                    erro='Este número já existe no banco de dados.',
                    dados=request.form)

            # Processa a data de contato (obrigatório)
            data_contato = request.form['data_contato'].strip()
            if data_contato.lower() == 'hoje':
                data_contato = datetime.today().strftime("%d/%m/%Y")
            else:
                try:
                    # Valida o formato da data
                    datetime.strptime(data_contato, "%d/%m/%Y")
                except ValueError:
                    return render_template('adicionar.html', 
                        erro='Data de contato inválida. Use o formato DD/MM/AAAA ou a palavra "hoje".',
                        dados=request.form)

            # Validação do campo Lead (obrigatório)
            origem_lead = request.form['origem_lead'].strip()
            if not origem_lead or origem_lead not in ['Whatsapp', 'Instagram', 'Facebook', 'Google', 'Indicação']:
                return render_template('adicionar.html',
                    erro='Por favor, selecione uma origem válida para o lead.',
                    dados=request.form)

            # Validações opcionais
            responsavel = request.form['responsavel'].strip().title() if request.form['responsavel'].strip() else ''
            aluno = request.form['aluno'].strip().title() if request.form['aluno'].strip() else ''
            
            # Valida nome do responsável se fornecido
            if responsavel and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', responsavel):
                return render_template('adicionar.html', 
                    erro='O nome do responsável deve conter apenas letras e ter no mínimo 3 caracteres.',
                    dados=request.form)

            # Valida nome do aluno se fornecido
            if aluno and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', aluno):
                return render_template('adicionar.html', 
                    erro='O nome do aluno deve conter apenas letras e ter no mínimo 3 caracteres.',
                    dados=request.form)

            # Valida idade se fornecida
            idade = None
            if request.form['idade'].strip():
                try:
                    idade = int(request.form['idade'])
                    if idade < 4 or idade > 99:
                        return render_template('adicionar.html', 
                            erro='Idade inválida. Deve ser um número entre 4 e 99.',
                            dados=request.form)
                except ValueError:
                    return render_template('adicionar.html', 
                        erro='Idade inválida. Deve ser um número entre 4 e 99.',
                        dados=request.form)

            # Valida data da AE se fornecida
            data_ae = request.form['data_ae'].strip()
            if data_ae:
                try:
                    datetime.strptime(data_ae, "%d/%m/%Y")
                except ValueError:
                    return render_template('adicionar.html', 
                        erro='Data da AE inválida. Use o formato DD/MM/AAAA.',
                        dados=request.form)

            # Valida hora da AE se fornecida
            hora_ae = request.form['hora_ae'].strip()
            if hora_ae and not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', hora_ae):
                return render_template('adicionar.html', 
                    erro='Hora da AE inválida. Use o formato HH:MM.',
                    dados=request.form)

            # Prepara os dados para salvar
            dados = {
                "Nome do responsável": responsavel,
                "Número": numero,
                "Data de contato": data_contato,
                "Nome do aluno": aluno,
                "Idade do aluno": idade if idade is not None else '',
                "Curso": request.form['curso'].strip(),
                "Data AE": data_ae,
                "Hora planejada AE": hora_ae,
                "Observação": request.form['observacao'].strip(),
                "Chances de fechar": request.form['chance'].strip(),
                "Ligação": request.form['ligacao'].strip(),
                "Lead": origem_lead,
                "Tipo aluno": request.form['tipo_aluno'].strip()
            }
            
            df = pd.concat([df, pd.DataFrame([dados])], ignore_index=True)
            df.to_excel(PLANILHA_PATH, index=False)
            return render_template('adicionar.html', sucesso=True)
            
        except Exception as e:
            return render_template('adicionar.html', 
                erro=f'Erro ao salvar os dados: {str(e)}',
                dados=request.form)
            
    return render_template('adicionar.html')

@app.route('/alterar_dados', methods=['GET', 'POST'])
@requer_admin
def alterar_dados():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            dados = request.get_json()
            index = int(dados['index'])
            
            # Validação do número de telefone (obrigatório)
            numero = dados['numero'].strip()
            if not numero or not re.match(r'^\(\d{2}\)[9]?\d{4}-\d{4}$', numero):
                return jsonify({'success': False, 'error': 'Número de telefone inválido.'})

            # Verifica se o número já existe em outro registro
            df = pd.read_excel(PLANILHA_PATH)
            numeros_existentes = df['Número'].astype(str).str.strip().tolist()
            if numero in numeros_existentes and numeros_existentes.index(numero) != index:
                return jsonify({'success': False, 'error': 'Este número já existe no banco de dados.'})

            # Processa a data de contato (obrigatório)
            data_contato = dados['data_contato'].strip()
            if data_contato.lower() == 'hoje':
                data_contato = datetime.today().strftime("%d/%m/%Y")
            else:
                try:
                    # Valida o formato da data
                    datetime.strptime(data_contato, "%d/%m/%Y")
                except ValueError:
                    return jsonify({'success': False, 'error': 'Data de contato inválida. Use o formato DD/MM/AAAA ou a palavra "hoje".'})

            # Validação do campo Lead (obrigatório)
            origem_lead = dados['origem_lead'].strip()
            if not origem_lead or origem_lead not in ['Whatsapp', 'Instagram', 'Facebook', 'Google', 'Indicação']:
                return jsonify({'success': False, 'error': 'Por favor, selecione uma origem válida para o lead.'})

            # Validações opcionais
            responsavel = dados['responsavel'].strip().title()
            aluno = dados['aluno'].strip().title()
            
            # Valida nome do responsável se fornecido
            if responsavel and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', responsavel):
                return jsonify({'success': False, 'error': 'O nome do responsável deve conter apenas letras e ter no mínimo 3 caracteres.'})

            # Valida nome do aluno se fornecido
            if aluno and not re.match(r'^[A-Za-zÀ-ÿ\s]{3,}$', aluno):
                return jsonify({'success': False, 'error': 'O nome do aluno deve conter apenas letras e ter no mínimo 3 caracteres.'})

            # Valida idade se fornecida
            idade = None
            if dados['idade'].strip():
                try:
                    idade = int(dados['idade'])
                    if idade < 4 or idade > 99:
                        return jsonify({'success': False, 'error': 'Idade inválida. Deve ser um número entre 4 e 99.'})
                except ValueError:
                    return jsonify({'success': False, 'error': 'Idade inválida. Deve ser um número entre 4 e 99.'})

            # Valida data da AE se fornecida
            data_ae = dados['data_ae'].strip()
            if data_ae:
                try:
                    datetime.strptime(data_ae, "%d/%m/%Y")
                except ValueError:
                    return jsonify({'success': False, 'error': 'Data da AE inválida. Use o formato DD/MM/AAAA.'})

            # Valida hora da AE se fornecida
            hora_ae = dados['hora_ae'].strip()
            if hora_ae and not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', hora_ae):
                return jsonify({'success': False, 'error': 'Hora da AE inválida. Use o formato HH:MM.'})
            
            # Atualiza os dados do lead
            df.loc[index, 'Nome do responsável'] = responsavel
            df.loc[index, 'Número'] = numero
            df.loc[index, 'Data de contato'] = data_contato
            df.loc[index, 'Nome do aluno'] = aluno
            df.loc[index, 'Idade do aluno'] = idade if idade is not None else ''
            df.loc[index, 'Curso'] = dados['curso'].strip()
            df.loc[index, 'Data AE'] = data_ae
            df.loc[index, 'Hora planejada AE'] = hora_ae
            df.loc[index, 'Chances de fechar'] = dados['chance'].strip()
            df.loc[index, 'Observação'] = dados['observacao'].strip()
            df.loc[index, 'Ligação'] = dados['ligacao'].strip()
            df.loc[index, 'Lead'] = origem_lead
            df.loc[index, 'Tipo aluno'] = dados['tipo_aluno'].strip()
            
            # Salva as alterações
            df.to_excel(PLANILHA_PATH, index=False)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    # Lê os dados atuais para exibir na página
    leads = carregar_leads()
    return render_template('alterar_dados.html', leads=leads)

@app.route('/excluir_lead', methods=['POST'])
@requer_admin
def excluir_lead():
    if 'usuario' not in session:
        return jsonify({'success': False, 'error': 'Usuário não autenticado'})
    
    try:
        dados = request.get_json()
        index = int(dados['index'])
        df = pd.read_excel(PLANILHA_PATH)
        
        # Remove o lead pelo índice
        df = df.drop(index)
        
        # Reseta os índices
        df = df.reset_index(drop=True)
        
        # Salva as alterações
        df.to_excel(PLANILHA_PATH, index=False)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/mensagem_agendamento', methods=['GET', 'POST'])
def mensagem_agendamento():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    leads = carregar_leads()
    print(f"Enviando {len(leads)} leads para o template")
    return render_template('mensagem_agendamento.html', leads=leads)

@app.route('/mensagem_confirmacao', methods=['GET', 'POST'])
def mensagem_confirmacao():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    leads = carregar_leads()
    return render_template('mensagem_confirmacao.html', leads=leads)

@app.route('/analise_dados')
def analise_dados():
    try:
        # Lê o arquivo Excel
        df = pd.read_excel(PLANILHA_PATH)
        
        # Métricas principais
        total_leads = len(df)
        leads_convertidos = len(df[df['Tipo aluno'].isin(['cna', 'ctrlplay'])])
        alunos_cna = len(df[df['Tipo aluno'] == 'cna'])
        ligacoes_atendidas = len(df[df['Ligação'] == 'Atendeu'])
        
        # Cálculo das taxas
        taxa_conversao = round((leads_convertidos / total_leads * 100), 1) if total_leads > 0 else 0
        taxa_cna = round((alunos_cna / total_leads * 100), 1) if total_leads > 0 else 0
        taxa_atendimento = round((ligacoes_atendidas / total_leads * 100), 1) if total_leads > 0 else 0
        
        # Origem dos leads
        origem_leads = df['Lead'].value_counts().to_dict()
        
        # Status das ligações
        status_ligacoes = df['Ligação'].value_counts().to_dict()
        
        # Distribuição por curso
        distribuicao_cursos = df['Curso'].value_counts().to_dict()
        
        # Taxa de conversão por origem
        conversao_por_origem = {}
        for origem in origem_leads.keys():
            leads_origem = df[df['Lead'] == origem]
            convertidos_origem = len(leads_origem[leads_origem['Tipo aluno'].isin(['cna', 'ctrlplay'])])
            taxa = round((convertidos_origem / len(leads_origem) * 100), 1) if len(leads_origem) > 0 else 0
            conversao_por_origem[origem] = taxa
        
        return render_template('analise_dados.html',
                             total_leads=total_leads,
                             leads_convertidos=leads_convertidos,
                             alunos_cna=alunos_cna,
                             taxa_conversao=taxa_conversao,
                             taxa_cna=taxa_cna,
                             taxa_atendimento=taxa_atendimento,
                             origem_leads=origem_leads,
                             status_ligacoes=status_ligacoes,
                             distribuicao_cursos=distribuicao_cursos,
                             conversao_por_origem=conversao_por_origem)
    except Exception as e:
        flash(f'Erro ao carregar dados: {str(e)}', 'error')
        return redirect(url_for('menu'))

def criar_backup():
    """Cria um backup da planilha atual"""
    # Cria a pasta backups no mesmo diretório do script
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f'clientes_backup_{timestamp}.xlsx')
    
    # Copia o arquivo
    shutil.copy2(PLANILHA_PATH, backup_path)
    
    # Retorna o caminho completo
    return os.path.abspath(backup_path)

@app.route('/exportar_pipedrive')
@requer_admin
def exportar_pipedrive():
    try:
        # Verifica se o token do Pipedrive está configurado
        if not PIPEDRIVE_API_TOKEN:
            flash('Token do Pipedrive não configurado. Por favor, configure o token na variável PIPEDRIVE_API_TOKEN.', 'error')
            return redirect(url_for('menu'))

        df = pd.read_excel(PLANILHA_PATH)
        total_leads = len(df)
        sucessos = 0
        falhas = 0
        detalhes_erros = []

        # Testa a conexão com o Pipedrive
        test_resp = requests.get(f'https://api.pipedrive.com/v1/users/me?api_token={PIPEDRIVE_API_TOKEN}')
        if not test_resp.ok:
            flash(f'Erro ao conectar com o Pipedrive: {test_resp.text}', 'error')
            return redirect(url_for('menu'))

        for index, row in df.iterrows():
            try:
                # Limpa os dados antes de enviar
                nome = str(row['Nome do aluno'] if pd.notna(row['Nome do aluno']) else row['Nome do responsável']).strip()
                if not nome:
                    nome = "Lead sem nome"
                numero = str(row['Número']).strip()
                if not numero:
                    detalhes_erros.append(f"Lead {index + 1} não tem número de telefone")
                    falhas += 1
                    print(f"[ERRO] Lead {index + 1}: número de telefone ausente. Dados: {row.to_dict()}")
                    continue

                # Cria o lead (pessoa) no Pipedrive
                pessoa_payload = {
                    'name': nome,
                    'phone': numero,
                }
                print(f"[INFO] Enviando pessoa para Pipedrive: {pessoa_payload}")
                pessoa_resp = requests.post(
                    f'https://api.pipedrive.com/v1/persons?api_token={PIPEDRIVE_API_TOKEN}',
                    json=pessoa_payload
                )
                print(f"[INFO] Resposta da criação de pessoa: {pessoa_resp.status_code} {pessoa_resp.text}")
                pessoa_data = pessoa_resp.json()
                if not pessoa_data.get('success'):
                    erro = f"Erro ao criar pessoa para lead {index + 1}: {pessoa_data.get('error', 'Erro desconhecido')}"
                    detalhes_erros.append(erro)
                    falhas += 1
                    continue
                pessoa_id = pessoa_data['data']['id']

                # Cria o lead com campos obrigatórios
                lead_payload = {
                    'title': nome,
                    'person_id': pessoa_id,
                    'expected_close_date': datetime.now().strftime("%Y-%m-%d"),
                    'source': 'CRM',
                    'label_ids': [],
                    'visible_to': '3',
                    'add_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                print(f"[INFO] Enviando lead para Pipedrive: {lead_payload}")
                lead_resp = requests.post(
                    f'https://api.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_TOKEN}',
                    json=lead_payload
                )
                print(f"[INFO] Resposta da criação de lead: {lead_resp.status_code} {lead_resp.text}")
                lead_data = lead_resp.json()
                if not lead_data.get('success'):
                    erro = f"Erro ao criar lead para pessoa {pessoa_id}: {lead_data.get('error', 'Erro desconhecido')}"
                    detalhes_erros.append(erro)
                    falhas += 1
                    continue
                lead_id = lead_data['data']['id']

                # Prepara os dados para a nota
                nota_dados = {
                    'Responsável': str(row['Nome do responsável']).strip() if pd.notna(row['Nome do responsável']) else 'N/A',
                    'Idade do Aluno': str(row['Idade do aluno']).strip() if pd.notna(row['Idade do aluno']) else 'N/A',
                    'Curso': str(row['Curso']).strip() if pd.notna(row['Curso']) else 'N/A',
                    'Tipo de Aluno': str(row['Tipo aluno']).strip() if pd.notna(row['Tipo aluno']) else 'N/A',
                    'Data AE': str(row['Data AE']).strip() if pd.notna(row['Data AE']) else 'N/A',
                    'Hora AE': str(row['Hora planejada AE']).strip() if pd.notna(row['Hora planejada AE']) else 'N/A',
                    'Chances de Fechar': str(row['Chances de fechar']).strip() if pd.notna(row['Chances de fechar']) else 'N/A',
                    'Status da Ligação': str(row['Ligação']).strip() if pd.notna(row['Ligação']) else 'N/A',
                    'Origem do Lead': str(row['Lead']).strip() if pd.notna(row['Lead']) else 'N/A',
                    'Observações': str(row['Observação']).strip() if pd.notna(row['Observação']) else 'N/A'
                }
                note = "\n".join([f"{k}: {v}" for k, v in nota_dados.items()])
                note_payload = {
                    'content': note,
                    'lead_id': lead_id
                }
                print(f"[INFO] Enviando nota para Pipedrive: {note_payload}")
                note_resp = requests.post(
                    f'https://api.pipedrive.com/v1/notes?api_token={PIPEDRIVE_API_TOKEN}',
                    json=note_payload
                )
                print(f"[INFO] Resposta da criação de nota: {note_resp.status_code} {note_resp.text}")
                if note_resp.status_code in [200, 201]:
                    sucessos += 1
                else:
                    erro = f"Erro ao adicionar nota para lead {lead_id}: {note_resp.text}"
                    detalhes_erros.append(erro)
                    falhas += 1

            except Exception as e:
                erro = f"Erro ao processar lead {index + 1}: {str(e)}"
                detalhes_erros.append(erro)
                falhas += 1
                print(f"[ERRO] Exceção ao processar lead {index + 1}: {str(e)}")
                continue

        mensagem = f"""
Exportação concluída!
Total de leads processados: {total_leads}
Leads exportados com sucesso: {sucessos}
Falhas: {falhas}
"""
        if detalhes_erros:
            mensagem += "\nDetalhes dos erros:\n" + "\n".join(detalhes_erros)

        flash(mensagem, 'success' if falhas == 0 else 'warning')
    except Exception as e:
        flash(f'Erro ao exportar para o Pipedrive: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/importar_pipedrive')
@requer_admin
def importar_pipedrive():
    try:
        # Verifica se o token do Pipedrive está configurado
        if not PIPEDRIVE_API_TOKEN:
            flash('Token do Pipedrive não configurado. Por favor, configure o token na variável PIPEDRIVE_API_TOKEN.', 'error')
            return redirect(url_for('menu'))

        # Cria backup antes de importar
        backup_path = criar_backup()
        
        # Testa a conexão com o Pipedrive
        test_resp = requests.get(f'https://api.pipedrive.com/v1/users/me?api_token={PIPEDRIVE_API_TOKEN}')
        if not test_resp.ok:
            flash(f'Erro ao conectar com o Pipedrive: {test_resp.text}', 'error')
            return redirect(url_for('menu'))
        
        # Obtém todos os leads do Pipedrive
        leads_resp = requests.get(f'https://api.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_TOKEN}')
        leads = leads_resp.json()
        print(f"[IMPORTAÇÃO] Leads retornados pela API: {len(leads.get('data', []))}")
        if leads.get('data'):
            for l in leads['data']:
                person_id_raw = l.get('person_id')
                if isinstance(person_id_raw, dict):
                    person_id = person_id_raw.get('value')
                else:
                    person_id = person_id_raw
                print(f"[IMPORTAÇÃO] Lead ID: {l.get('id')}, Título: {l.get('title')}, Person ID: {person_id}")
        
        if not leads.get('success'):
            flash(f'Erro ao buscar leads do Pipedrive: {leads.get("error", "Erro desconhecido")}', 'error')
            return redirect(url_for('menu'))
            
        if not leads.get('data'):
            flash(f'Nenhum lead encontrado no Pipedrive. Backup criado em: {backup_path}', 'warning')
            return redirect(url_for('menu'))
        
        df = pd.read_excel(PLANILHA_PATH)
        # Garante que a coluna 'Lead' existe
        if 'Lead' not in df.columns:
            df['Lead'] = ''
        numeros_existentes = set(df['Número'].astype(str).str.strip())
        novos_leads = 0
        detalhes_importacao = []
        
        for lead in leads['data']:
            try:
                lead_id = lead['id']
                lead_title = lead.get('title', '')
                # Remover 'Lead ' do início do título, se existir
                if lead_title.lower().startswith('lead '):
                    lead_title = lead_title[5:].strip()
                person_id_raw = lead.get('person_id')
                if isinstance(person_id_raw, dict):
                    person_id = person_id_raw.get('value')
                else:
                    person_id = person_id_raw
                if not person_id:
                    detalhes_importacao.append(f"Lead {lead_id} não tem pessoa associada")
                    print(f"[IMPORTAÇÃO] Lead {lead_id} ignorado: sem pessoa associada.")
                    continue
                    
                # Busca dados da pessoa
                person_resp = requests.get(f'https://api.pipedrive.com/v1/persons/{person_id}?api_token={PIPEDRIVE_API_TOKEN}')
                person_data = person_resp.json()
                
                if not person_data.get('success'):
                    detalhes_importacao.append(f"Erro ao buscar pessoa {person_id}: {person_data.get('error', 'Erro desconhecido')}")
                    print(f"[IMPORTAÇÃO] Erro ao buscar pessoa {person_id}: {person_data.get('error', 'Erro desconhecido')}")
                    continue
                
                # Extrai telefone
                phones = person_data['data'].get('phone', [])
                if not phones or not isinstance(phones, list):
                    detalhes_importacao.append(f"Pessoa {person_id} não tem telefone")
                    print(f"[IMPORTAÇÃO] Pessoa {person_id} ignorada: sem telefone.")
                    continue
                phone = phones[0].get('value', '').strip()
                # NOVO: Remover 55 se for número brasileiro
                if phone.startswith('55'):
                    phone = phone[2:].strip()
                    # Remove espaços e formata para (xx)xxxxx-xxxx ou (xx)xxxx-xxxx
                    phone = phone.replace(' ', '').replace('-', '')
                    if len(phone) == 11:
                        phone = f'({phone[:2]}){phone[2:7]}-{phone[7:]}'
                    elif len(phone) == 10:
                        phone = f'({phone[:2]}){phone[2:6]}-{phone[6:]}'
                print(f"[IMPORTAÇÃO] Lead {lead_id} - Telefone encontrado: {phone}")
                if not phone:
                    detalhes_importacao.append(f"Telefone vazio para pessoa {person_id}")
                    print(f"[IMPORTAÇÃO] Pessoa {person_id} ignorada: telefone vazio.")
                    continue
                if phone in numeros_existentes:
                    detalhes_importacao.append(f"Telefone {phone} já existe no sistema")
                    print(f"[IMPORTAÇÃO] Lead {lead_id} ignorado: telefone já existe no sistema.")
                    continue
                
                # Busca notas
                notes_resp = requests.get(f'https://api.pipedrive.com/v1/notes?lead_id={lead_id}&api_token={PIPEDRIVE_API_TOKEN}')
                notes_data = notes_resp.json()
                
                if not notes_data.get('success'):
                    detalhes_importacao.append(f"Erro ao buscar notas do lead {lead_id}: {notes_data.get('error', 'Erro desconhecido')}")
                    continue
                
                note_content = ''
                if notes_data.get('data'):
                    note_content = notes_data['data'][0].get('content', '')
                
                # Extrai informações da nota
                info = {}
                for line in note_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                
                novo_lead = {
                    "Nome do responsável": lead_title,  # Agora o título vai para responsável sem 'Lead '
                    "Número": phone,
                    "Data de contato": datetime.now().strftime("%d/%m/%Y"),
                    "Nome do aluno": info.get('Responsável', ''),  # O que vier da nota vai para aluno
                    "Idade do aluno": info.get('Idade do Aluno', ''),
                    "Curso": info.get('Curso', ''),
                    "Data AE": info.get('Data AE', ''),
                    "Hora planejada AE": info.get('Hora AE', ''),
                    "Observação": info.get('Observações', ''),
                    "Chances de fechar": info.get('Chances de Fechar', ''),
                    "Ligação": info.get('Status da Ligação', ''),
                    "Lead": 'Pipedrive',
                    "Tipo aluno": info.get('Tipo de Aluno', '')
                }
                
                df = pd.concat([df, pd.DataFrame([novo_lead])], ignore_index=True)
                novos_leads += 1
                detalhes_importacao.append(f"Lead {lead_id} importado com sucesso")
                
            except Exception as e:
                detalhes_importacao.append(f"Erro ao processar lead {lead.get('id', 'desconhecido')}: {str(e)}")
                continue
        
        if novos_leads > 0:
            df.to_excel(PLANILHA_PATH, index=False)
            mensagem = f"""
Importação concluída!
Backup criado em: {backup_path}
Novos leads importados: {novos_leads}
Total de leads processados: {len(leads['data'])}
"""
            if detalhes_importacao:
                mensagem += "\nDetalhes da importação:\n" + "\n".join(detalhes_importacao)
            
            flash(mensagem, 'success')
        else:
            flash(f'Nenhum novo lead para importar. Backup criado em: {backup_path}', 'info')
            
    except Exception as e:
        flash(f'Erro ao importar do Pipedrive: {str(e)}', 'error')
    
    return redirect(url_for('menu'))

@app.route('/backups')
@requer_admin
def listar_backups():
    try:
        # Obtém o diretório de backups
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        
        # Lista todos os arquivos de backup
        backups = []
        if os.path.exists(backup_dir):
            for arquivo in os.listdir(backup_dir):
                if arquivo.endswith('.xlsx'):
                    caminho_completo = os.path.join(backup_dir, arquivo)
                    data_criacao = datetime.fromtimestamp(os.path.getctime(caminho_completo))
                    backups.append({
                        'nome': arquivo,
                        'data': data_criacao.strftime("%d/%m/%Y %H:%M:%S"),
                        'caminho': caminho_completo
                    })
        
        # Ordena por data (mais recente primeiro)
        backups.sort(key=lambda x: x['data'], reverse=True)
        
        return render_template('backups.html', backups=backups)
    except Exception as e:
        flash(f'Erro ao listar backups: {str(e)}', 'error')
        return redirect(url_for('menu'))

@app.route('/baixar_backup/<path:nome_arquivo>')
@requer_admin
def baixar_backup(nome_arquivo):
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
        caminho_arquivo = os.path.join(backup_dir, nome_arquivo)
        
        if os.path.exists(caminho_arquivo):
            return send_file(caminho_arquivo, as_attachment=True)
        else:
            flash('Arquivo de backup não encontrado.', 'error')
            return redirect(url_for('listar_backups'))
    except Exception as e:
        flash(f'Erro ao baixar backup: {str(e)}', 'error')
        return redirect(url_for('listar_backups'))

@app.route('/visualizar_importacao')
@requer_admin
def visualizar_importacao():
    try:
        # Busca os leads do Pipedrive (igual à importação, mas sem salvar)
        if not PIPEDRIVE_API_TOKEN:
            flash('Token do Pipedrive não configurado. Por favor, configure o token na variável PIPEDRIVE_API_TOKEN.', 'error')
            return redirect(url_for('menu'))
        leads_resp = requests.get(f'https://api.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_TOKEN}')
        leads = leads_resp.json()
        if not leads.get('success') or not leads.get('data'):
            flash('Nenhum lead encontrado no Pipedrive.', 'warning')
            return redirect(url_for('menu'))
        dados_importacao = []
        for lead in leads['data']:
            try:
                lead_id = lead['id']
                lead_title = lead.get('title', '')
                if lead_title.lower().startswith('lead '):
                    lead_title = lead_title[5:].strip()
                person_id_raw = lead.get('person_id')
                if isinstance(person_id_raw, dict):
                    person_id = person_id_raw.get('value')
                else:
                    person_id = person_id_raw
                if not person_id:
                    continue
                person_resp = requests.get(f'https://api.pipedrive.com/v1/persons/{person_id}?api_token={PIPEDRIVE_API_TOKEN}')
                person_data = person_resp.json()
                if not person_data.get('success'):
                    continue
                phones = person_data['data'].get('phone', [])
                if not phones or not isinstance(phones, list):
                    continue
                phone = phones[0].get('value', '').strip()
                if phone.startswith('55'):
                    phone = phone[2:].strip()
                    phone = phone.replace(' ', '').replace('-', '')
                    if len(phone) == 11:
                        phone = f'({phone[:2]}){phone[2:7]}-{phone[7:]}'
                    elif len(phone) == 10:
                        phone = f'({phone[:2]}){phone[2:6]}-{phone[6:]}'
                notes_resp = requests.get(f'https://api.pipedrive.com/v1/notes?lead_id={lead_id}&api_token={PIPEDRIVE_API_TOKEN}')
                notes_data = notes_resp.json()
                note_content = ''
                if notes_data.get('data'):
                    note_content = notes_data['data'][0].get('content', '')
                info = {}
                for line in note_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                dados_importacao.append({
                    "Nome do responsável": lead_title,
                    "Número": phone,
                    "Data de contato": datetime.now().strftime("%d/%m/%Y"),
                    "Nome do aluno": info.get('Responsável', ''),
                    "Idade do aluno": info.get('Idade do Aluno', ''),
                    "Curso": info.get('Curso', ''),
                    "Data AE": info.get('Data AE', ''),
                    "Hora planejada AE": info.get('Hora AE', ''),
                    "Observação": info.get('Observações', ''),
                    "Chances de fechar": info.get('Chances de Fechar', ''),
                    "Ligação": info.get('Status da Ligação', ''),
                    "Lead": 'Pipedrive',
                    "Tipo aluno": info.get('Tipo de Aluno', '')
                })
            except Exception as e:
                continue
        return render_template('visualizar_importacao.html', leads=dados_importacao)
    except Exception as e:
        flash(f'Erro ao visualizar importação: {str(e)}', 'error')
        return redirect(url_for('menu'))

@app.route('/baixar_importacao')
@requer_admin
def baixar_importacao():
    try:
        # Gera a planilha temporária com os dados da importação
        if not PIPEDRIVE_API_TOKEN:
            flash('Token do Pipedrive não configurado.', 'error')
            return redirect(url_for('menu'))
        leads_resp = requests.get(f'https://api.pipedrive.com/v1/leads?api_token={PIPEDRIVE_API_TOKEN}')
        leads = leads_resp.json()
        dados_importacao = []
        for lead in leads.get('data', []):
            try:
                lead_id = lead['id']
                lead_title = lead.get('title', '')
                if lead_title.lower().startswith('lead '):
                    lead_title = lead_title[5:].strip()
                person_id_raw = lead.get('person_id')
                if isinstance(person_id_raw, dict):
                    person_id = person_id_raw.get('value')
                else:
                    person_id = person_id_raw
                if not person_id:
                    continue
                person_resp = requests.get(f'https://api.pipedrive.com/v1/persons/{person_id}?api_token={PIPEDRIVE_API_TOKEN}')
                person_data = person_resp.json()
                if not person_data.get('success'):
                    continue
                phones = person_data['data'].get('phone', [])
                if not phones or not isinstance(phones, list):
                    continue
                phone = phones[0].get('value', '').strip()
                if phone.startswith('55'):
                    phone = phone[2:].strip()
                    phone = phone.replace(' ', '').replace('-', '')
                    if len(phone) == 11:
                        phone = f'({phone[:2]}){phone[2:7]}-{phone[7:]}'
                    elif len(phone) == 10:
                        phone = f'({phone[:2]}){phone[2:6]}-{phone[6:]}'
                notes_resp = requests.get(f'https://api.pipedrive.com/v1/notes?lead_id={lead_id}&api_token={PIPEDRIVE_API_TOKEN}')
                notes_data = notes_resp.json()
                note_content = ''
                if notes_data.get('data'):
                    note_content = notes_data['data'][0].get('content', '')
                info = {}
                for line in note_content.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                dados_importacao.append({
                    "Nome do responsável": lead_title,
                    "Número": phone,
                    "Data de contato": datetime.now().strftime("%d/%m/%Y"),
                    "Nome do aluno": info.get('Responsável', ''),
                    "Idade do aluno": info.get('Idade do Aluno', ''),
                    "Curso": info.get('Curso', ''),
                    "Data AE": info.get('Data AE', ''),
                    "Hora planejada AE": info.get('Hora AE', ''),
                    "Observação": info.get('Observações', ''),
                    "Chances de fechar": info.get('Chances de Fechar', ''),
                    "Ligação": info.get('Status da Ligação', ''),
                    "Lead": 'Pipedrive',
                    "Tipo aluno": info.get('Tipo de Aluno', '')
                })
            except Exception as e:
                continue
        import pandas as pd
        import tempfile
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        df = pd.DataFrame(dados_importacao)
        df.to_excel(temp.name, index=False)
        temp.seek(0)
        return send_file(temp.name, as_attachment=True, download_name='importacao_pipedrive.xlsx')
    except Exception as e:
        flash(f'Erro ao baixar planilha da importação: {str(e)}', 'error')
        return redirect(url_for('menu'))

if __name__ == '__main__':
    app.run(debug=True)