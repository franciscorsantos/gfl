from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response, send_from_directory
from sqlalchemy import func, case
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import shutil
import io
import csv
from flask_apscheduler import APScheduler
from flask_migrate import Migrate

from models import (
    db, Portador, PlanoConta, FormaPagamento, CentroCusto, Transacao,
    Fornecedor, ContaPagar, ParcelaConta, CartaoCredito, DespesaCartao, LogAuditoria,
    Usuario
)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa a aplicação Flask
app = Flask(__name__)

# Configurações do Banco de Dados
# A URL de conexão é carregada da variável de ambiente DATABASE_URL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# A chave secreta é carregada da variável de ambiente SECRET_KEY
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# --- CONFIGURAÇÃO DO AGENDADOR DE TAREFAS (APScheduler) ---
class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Vincula o SQLAlchemy à nossa aplicação Flask
db.init_app(app)

# Configuração do Flask-Migrate. A convenção de nomenclatura já está no objeto 'db' de models.py
migrate = Migrate(app, db,
                  render_as_batch=True,
                  compare_type=True)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "info"

# --- CONFIGURAÇÃO DE PATHS PARA BACKUP ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
DB_NAME = 'gfl.db'
DB_PATH = os.path.join(INSTANCE_DIR, DB_NAME)
LOG_FILE = os.path.join(BASE_DIR, 'backup_log.txt')

# Cria o diretório de backups se não existir
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# --- FILTRO JINJA2 PARA MOEDA BRASILEIRA ---
@app.template_filter('br_currency')
def format_brazilian_currency(value):
    """
    Formata um número (Decimal, float ou int) para o padrão de moeda brasileiro.
    Ex: 1234.56 -> '1.234,56'
    """
    if value is None:
        value = Decimal('0.0')
    # Garante que o valor é um Decimal para arredondamento correto
    valor_decimal = Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    # Formata com separador de milhar e vírgula decimal
    # A biblioteca padrão locale pode ser complexa de configurar em servidores.
    # Esta abordagem com replace é mais direta e independente de locale.
    valor_formatado = f"{valor_decimal:,.2f}"
    # Troca o padrão americano (1,234.56) pelo brasileiro (1.234,56)
    return valor_formatado.replace(",", "X").replace(".", ",").replace("X", ".")


# --- VARIÁVEIS GLOBAIS PARA OS TEMPLATES ---
@app.context_processor
def injetar_dados_globais():
    # Isso garante que todos os modais de lançamento tenham acesso às listas atualizadas
    return dict(
        opcoes_portadores=Portador.query.all(),
        opcoes_planos=PlanoConta.query.order_by(PlanoConta.codigo).all(),
        opcoes_centros=CentroCusto.query.all(),
        opcoes_formas=FormaPagamento.query.all(),
        opcoes_fornecedores=Fornecedor.query.filter_by(status='Ativo').order_by(Fornecedor.nome).all(),
        current_user=current_user
    )

@app.context_processor
def injetar_dados_cartoes():
    # Disponibiliza a lista de cartões para os formulários
    return dict(
        opcoes_cartoes=CartaoCredito.query.order_by(CartaoCredito.nome).all()
    )

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# --- FUNÇÃO AUXILIAR DE LOG ---
def registrar_log(acao, modulo, detalhes):
    """
    Registra uma ação no log de auditoria.
    Captura o usuário logado automaticamente.
    """
    try:
        log = LogAuditoria(
            usuario_id=current_user.id,
            acao=acao,
            modulo=modulo,
            detalhes=detalhes
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"ERRO AO REGISTRAR LOG: {e}")
        db.session.rollback()

# --- ROTINAS DE BACKUP ---
def _log_backup(message):
    """Função auxiliar para registrar logs de backup."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] - {message}\n")

def limpar_backups_antigos(dias_retencao=7):
    """Apaga arquivos de backup mais antigos que o período de retenção."""
    try:
        limite_tempo = datetime.now() - relativedelta(days=dias_retencao)
        arquivos_backup = os.listdir(BACKUP_DIR)
        for arquivo in arquivos_backup:
            caminho_completo = os.path.join(BACKUP_DIR, arquivo)
            if os.path.isfile(caminho_completo):
                data_modificacao = datetime.fromtimestamp(os.path.getmtime(caminho_completo))
                if data_modificacao < limite_tempo:
                    os.remove(caminho_completo)
                    _log_backup(f"LIMPEZA: Backup antigo '{arquivo}' foi excluído.")
    except Exception as e:
        _log_backup(f"ERRO na limpeza de backups antigos: {str(e)}")

def gerar_backup():
    """Gera uma cópia de segurança do banco de dados."""
    with app.app_context():
        if not os.path.exists(DB_PATH):
            _log_backup(f"ERRO: Arquivo do banco de dados não encontrado em '{DB_PATH}'.")
            return False, f"Arquivo do banco de dados não encontrado em '{DB_PATH}'."

        timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%M')
        backup_filename = f"backup_gfl_{timestamp}.db"
        backup_filepath = os.path.join(BACKUP_DIR, backup_filename)

        try:
            shutil.copy2(DB_PATH, backup_filepath)
            tamanho_mb = os.path.getsize(backup_filepath) / (1024 * 1024)
            _log_backup(f"SUCESSO: Backup gerado com sucesso: '{backup_filename}' ({tamanho_mb:.2f} MB).")
            
            limpar_backups_antigos(dias_retencao=7)
            return True, f"Backup '{backup_filename}' gerado com sucesso."
        except Exception as e:
            _log_backup(f"FALHA ao gerar backup: {str(e)}")
            return False, f"Falha ao gerar backup: {str(e)}"

# --- INICIALIZAÇÃO DO BANCO ---
with app.app_context():
    db.create_all() # Cria as tabelas fisicamente, caso não existam. A carga inicial será feita manualmente via seed_db.py

# --- TAREFA AGENDADA DE BACKUP ---
@scheduler.task('cron', id='job_backup_diario', hour=3, minute=0)
def backup_diario_agendado():
    print("Iniciando rotina de backup agendada...")
    gerar_backup()
    print("Rotina de backup agendada concluída.")

# Rota principal (Dashboard)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('painel'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        user = Usuario.query.filter_by(email=email).first()
        
        if user and user.check_senha(senha) and user.status == 'Ativo':
            login_user(user)
            registrar_log('LOGIN', 'Autenticação', f'Usuário "{user.nome}" realizou login com sucesso.')
            return redirect(url_for('painel'))
        else:
            # Usando flash para mensagens de erro no template de login
            flash('Credenciais inválidas ou usuário inativo.', 'danger')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/')
@login_required
def painel():
    if current_user.perfil == 'Operador':
        return redirect(url_for('lancamentos'))

    # --- 1. Refatoração do Saldo Global ---
    # Apenas transações 'Realizado' devem impactar o caixa.
    total_saldos_iniciais = db.session.query(func.sum(Portador.saldo_inicial)).scalar() or Decimal('0.0')
    total_receitas_realizadas = db.session.query(func.sum(Transacao.valor)).filter(
        Transacao.tipo == 'Receita', 
        Transacao.status == 'Realizado'
    ).scalar() or Decimal('0.0')
    total_despesas_realizadas = db.session.query(func.sum(Transacao.valor)).filter(
        Transacao.tipo == 'Despesa', 
        Transacao.status == 'Realizado'
    ).scalar() or Decimal('0.0')
    
    saldo_atual_consolidado = total_saldos_iniciais + total_receitas_realizadas - total_despesas_realizadas

    # --- 2. Cálculo Individual por Portador ---
    portadores = Portador.query.order_by(Portador.nome).all()
    saldos_portadores = []
    for portador in portadores:
        receitas_portador = db.session.query(func.sum(Transacao.valor)).filter(
            Transacao.portador_id == portador.id,
            Transacao.tipo == 'Receita',
            Transacao.status == 'Realizado'
        ).scalar() or Decimal('0.0')

        despesas_portador = db.session.query(func.sum(Transacao.valor)).filter(
            Transacao.portador_id == portador.id,
            Transacao.tipo == 'Despesa',
            Transacao.status == 'Realizado'
        ).scalar() or Decimal('0.0')

        saldo_final_portador = portador.saldo_inicial + receitas_portador - despesas_portador
        
        saldos_portadores.append({
            'nome': portador.nome,
            'tipo': portador.tipo,
            'saldo_final': saldo_final_portador
        })

    # --- 3. Dados para o template ---
    # Últimos lançamentos para a tabela do painel (pode manter todos os status aqui para visibilidade)
    ultimas_transacoes = Transacao.query.order_by(Transacao.data_vencimento.desc()).limit(5).all()
    
    return render_template(
        'painel.html', 
        saldo_atual=saldo_atual_consolidado, 
        total_receitas=total_receitas_realizadas, # Atualizado para mostrar apenas o realizado
        total_despesas=total_despesas_realizadas, # Atualizado para mostrar apenas o realizado
        transacoes=ultimas_transacoes,
        saldos_portadores=saldos_portadores # Nova variável
    )

@app.route('/conta/transferencia', methods=['POST'])
@login_required
def transferencia_entre_contas():
    """
    Processa a transferência de valores entre dois portadores (contas).
    Cria duas transações: uma despesa na origem e uma receita no destino.
    """
    dados = request.get_json()
    try:
        # 1. Captura e converte os dados
        origem_id = int(dados['conta_origem_id'])
        destino_id = int(dados['conta_destino_id'])
        valor_str = dados['valor']
 
        # 2. Valida se as contas são diferentes
        if origem_id == destino_id:
            return jsonify({'status': 'erro', 'mensagem': 'A conta de origem e destino não podem ser as mesmas.'}), 400
 
        # 3. Trata e valida o valor monetário
        valor_decimal = Decimal(valor_str.replace('.', '').replace(',', '.'))
        if valor_decimal <= 0:
            return jsonify({'status': 'erro', 'mensagem': 'O valor da transferência deve ser maior que zero.'}), 400
 
        # 4. Busca os objetos necessários no banco de dados
        portador_origem = Portador.query.get_or_404(origem_id)
        portador_destino = Portador.query.get_or_404(destino_id)
        categoria_saida = PlanoConta.query.filter_by(codigo='02.99').first()
        categoria_entrada = PlanoConta.query.filter_by(codigo='01.99').first()
        forma_pagto_transferencia = FormaPagamento.query.filter(FormaPagamento.nome.ilike('%transferência%')).first()
 
        # Valida se as categorias e forma de pagamento existem
        if not all([categoria_saida, categoria_entrada, forma_pagto_transferencia]):
            return jsonify({'status': 'erro', 'mensagem': 'As categorias ou a forma de pagamento para transferência não estão configuradas no sistema.'}), 400
 
        # 5. Cria as duas transações (saída e entrada)
        hoje = date.today()
 
        transacao_saida = Transacao(
            tipo='Despesa',
            descricao=f"Transferência enviada para {portador_destino.nome}",
            status='Realizado',
            valor=valor_decimal,
            data_vencimento=hoje,
            portador_id=origem_id,
            plano_conta_id=categoria_saida.id,
            forma_pagto_id=forma_pagto_transferencia.id,
            usuario_id=current_user.id
        )
 
        transacao_entrada = Transacao(
            tipo='Receita',
            descricao=f"Transferência recebida de {portador_origem.nome}",
            status='Realizado',
            valor=valor_decimal,
            data_vencimento=hoje,
            portador_id=destino_id,
            plano_conta_id=categoria_entrada.id,
            forma_pagto_id=forma_pagto_transferencia.id,
            usuario_id=current_user.id
        )
 
        # 6. Adiciona e comita na sessão de forma atômica
        db.session.add_all([transacao_saida, transacao_entrada])
        db.session.commit()
        
        detalhes = f"Transferiu R$ {valor_decimal:.2f} da conta '{portador_origem.nome}' para '{portador_destino.nome}'."
        registrar_log('CRIAR', 'Transferência', detalhes)

        return jsonify({'status': 'sucesso', 'mensagem': 'Transferência realizada com sucesso!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/lancamentos', methods=['POST'])
@login_required
def criar_lancamento():
    dados = request.get_json()
    
    try:
        data_lanc = datetime.strptime(dados['data_lancamento'], '%Y-%m-%d').date()
        
        centro_id = dados.get('centro_custo_id')
        centro_id = int(centro_id) if centro_id and centro_id.strip() != "" else None

        # --- TRATAMENTO DA MÁSCARA DE MOEDA ---
        # 1. Tira o ponto de milhar ('1.250,50' -> '1250,50')
        # 2. Troca a vírgula por ponto ('1250,50' -> '1250.50')
        valor_limpo = dados['valor'].replace('.', '').replace(',', '.')
        valor_final = Decimal(valor_limpo)

        nova_transacao = Transacao(
            tipo=dados['tipo_operacao'],
            descricao=dados['descricao'],
            status=dados['status'],
            valor=valor_final,
            data_vencimento=data_lanc,
            portador_id=int(dados['portador_id']),
            plano_conta_id=int(dados['plano_conta_id']),
            forma_pagto_id=int(dados['forma_pagto_id']),
            centro_custo_id=centro_id,
            usuario_id=current_user.id
        )
                
        db.session.add(nova_transacao)
        db.session.commit()

        detalhes = f"Criou o lançamento '{nova_transacao.descricao}' no valor de R$ {nova_transacao.valor:.2f}."
        registrar_log('CRIAR', 'Lançamentos', detalhes)
        
        return jsonify({'status': 'sucesso', 'mensagem': 'Registrado com sucesso!'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/lancamentos')
@login_required
def lancamentos():
    # Inicia a query base
    query = Transacao.query

    # Pega os parâmetros do filtro da URL (GET request)
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    portador_id_str = request.args.get('portador_id')

    # Converte as strings para datas e aplica os filtros se existirem
    if data_inicio_str:
        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            query = query.filter(Transacao.data_vencimento >= data_inicio)
        except ValueError:
            pass # Ignora data inválida
    if data_fim_str:
        try:
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
            query = query.filter(Transacao.data_vencimento <= data_fim)
        except ValueError:
            pass # Ignora data inválida

    # Filtra por conta (portador) se um ID for fornecido
    if portador_id_str:
        try:
            query = query.filter(Transacao.portador_id == int(portador_id_str))
        except ValueError:
            pass # Ignora ID inválido
    
    todas_transacoes = query.order_by(Transacao.data_vencimento.desc()).all()
    return render_template('lancamentos.html', transacoes=todas_transacoes)

@app.route('/cadastros')
@login_required
def cadastros():
    # Buscamos todos os registros de cada tabela para popular as abas
    portadores = Portador.query.all()
    planos = PlanoConta.query.all()
    formas = FormaPagamento.query.all()
    centros = CentroCusto.query.all()
    fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
    
    return render_template(
        'cadastros.html', 
        portadores=portadores, 
        planos=planos, 
        formas=formas, 
        centros=centros,
        fornecedores=fornecedores
    )

@app.route('/gestao_contas_a_pagar')
@login_required
def gestao_contas_a_pagar():
    # Inicia a query base
    query = ContaPagar.query.join(Fornecedor).join(ParcelaConta)

    # --- FILTROS ---
    mes_ano_str = request.args.get('mes_ano')
    status_filtro = request.args.get('status', 'pendentes') # Default to 'pendentes'
    fornecedor_id_str = request.args.get('fornecedor_id')

    # Filtro de Mês/Ano
    if mes_ano_str:
        try:
            ano, mes = map(int, mes_ano_str.split('-'))
            query = query.filter(func.extract('year', ParcelaConta.data_vencimento) == ano)\
                         .filter(func.extract('month', ParcelaConta.data_vencimento) == mes)
        except (ValueError, TypeError):
            pass

    # Filtro de Fornecedor
    if fornecedor_id_str:
        try:
            query = query.filter(ContaPagar.fornecedor_id == int(fornecedor_id_str))
        except (ValueError, TypeError):
            pass
            
    # Filtro de Status (mais complexo)
    hoje = date.today()
    if status_filtro == 'pendentes':
        query = query.filter(ParcelaConta.status == 'Pendente', ParcelaConta.data_vencimento >= hoje)
    elif status_filtro == 'atrasadas':
        query = query.filter(ParcelaConta.status == 'Pendente', ParcelaConta.data_vencimento < hoje)
    elif status_filtro == 'pagas':
        query = query.filter(ParcelaConta.status == 'Pago')
    # 'todas' não precisa de filtro de status extra

    # Distinct para não repetir as Contas a Pagar se múltiplas parcelas baterem no filtro.
    # A exceção `sqlalchemy.exc.ProgrammingError` ocorre no PostgreSQL porque, ao usar `SELECT DISTINCT`,
    # todas as colunas no `ORDER BY` devem também estar na lista do `SELECT`.
    # A query original seleciona `DISTINCT conta_pagar.*` mas tenta ordenar por `fornecedor.nome`, que não está na seleção.
    # A correção é adicionar `Fornecedor.nome` à seleção e depois extrair apenas o objeto `ContaPagar` do resultado.
    results = query.add_columns(Fornecedor.nome)\
                   .distinct()\
                   .order_by(Fornecedor.nome, ContaPagar.data_emissao.desc())\
                   .all()

    # Extrai o primeiro elemento de cada tupla do resultado (que é o objeto ContaPagar)
    contas = [result[0] for result in results]

    # Pós-processamento para adicionar dados dinâmicos
    contas_info = []
    for conta in contas:
        total_parcelas = len(conta.parcelas)
        parcelas_pagas = 0
        
        for p in conta.parcelas:
            if p.status == 'Pago':
                p.status_dinamico = 'Pago'
                parcelas_pagas += 1
            elif p.data_vencimento < hoje:
                p.status_dinamico = 'Atrasado'
            else:
                p.status_dinamico = 'Pendente'
        
        conta.progresso_pagas = parcelas_pagas
        conta.progresso_total = total_parcelas
        contas_info.append(conta)

    # Gera opções de Mês/Ano para o filtro
    meses_filtro = []
    data_base = date.today()
    for i in range(-6, 7): # Gera de 6 meses atrás até 6 meses no futuro
        d = data_base + relativedelta(months=i)
        meses_filtro.append({'valor': d.strftime('%Y-%m'), 'texto': d.strftime('%B/%Y').capitalize()})

    return render_template(
        'gerenciar_contas_a_pagar.html',
        contas=contas_info,
        meses_filtro=meses_filtro
    )

@app.route('/contas_a_pagar')
@login_required
def contas_a_pagar():
    return render_template('contas_a_pagar.html')

@app.route('/extrato')
@login_required
def extrato():
    if current_user.perfil == 'Operador':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('lancamentos'))

    # --- 1. CAPTURA DOS FILTROS ---
    hoje = date.today()
    data_inicio_str = request.args.get('data_inicio', hoje.replace(day=1).strftime('%Y-%m-%d'))
    data_fim_str = request.args.get('data_fim', (hoje.replace(day=1) + relativedelta(months=1, days=-1)).strftime('%Y-%m-%d'))
    portador_id = request.args.get('portador_id')
    plano_conta_id = request.args.get('plano_conta_id')
    centro_custo_id = request.args.get('centro_custo_id')
    visao = request.args.get('visao', 'cronologico')
    ignorar_transferencias = request.args.get('ignorar_transferencias') == 'true'

    # --- 2. CONSTRUÇÃO DA QUERY BASE ---
    query = Transacao.query.filter(Transacao.status == 'Realizado')
    
    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        query = query.filter(Transacao.data_vencimento.between(data_inicio, data_fim))
    except (ValueError, TypeError):
        data_inicio = hoje.replace(day=1)
        data_fim = hoje.replace(day=1) + relativedelta(months=1, days=-1)
        query = query.filter(Transacao.data_vencimento.between(data_inicio, data_fim))

    if portador_id and portador_id.isdigit():
        query = query.filter(Transacao.portador_id == int(portador_id))
    if plano_conta_id and plano_conta_id.isdigit():
        query = query.filter(Transacao.plano_conta_id == int(plano_conta_id))
    if centro_custo_id and centro_custo_id.isdigit():
        query = query.filter(Transacao.centro_custo_id == int(centro_custo_id))

    # Filtro para ignorar transferências
    if ignorar_transferencias:
        # Busca os IDs das categorias de transferência para excluí-las da query
        transfer_sent_cat = PlanoConta.query.filter_by(codigo='02.99').with_entities(PlanoConta.id).first()
        transfer_received_cat = PlanoConta.query.filter_by(codigo='01.99').with_entities(PlanoConta.id).first()
        transfer_cat_ids = [cat_id[0] for cat_id in [transfer_sent_cat, transfer_received_cat] if cat_id]
        if transfer_cat_ids:
            query = query.filter(Transacao.plano_conta_id.notin_(transfer_cat_ids))

    # --- 3. CÁLCULO DOS TOTALIZADORES DO PERÍODO ---
    subquery = query.subquery()
    total_entradas = db.session.query(func.sum(subquery.c.valor)).filter(subquery.c.tipo == 'Receita').scalar() or Decimal(0)
    total_saidas = db.session.query(func.sum(subquery.c.valor)).filter(subquery.c.tipo == 'Despesa').scalar() or Decimal(0)
    resultado_periodo = total_entradas - total_saidas

    # --- 4. PROCESSAMENTO BASEADO NA VISÃO ---
    resultados = []
    if visao == 'resumo_categorias':
        resultados = query.with_entities(
            PlanoConta.nome,
            func.sum(case((Transacao.tipo == 'Receita', Transacao.valor), else_=0)).label('entradas'),
            func.sum(case((Transacao.tipo == 'Despesa', Transacao.valor), else_=0)).label('saidas')
        ).join(PlanoConta, isouter=True).group_by(PlanoConta.id, PlanoConta.nome).order_by(PlanoConta.nome).all()

    elif visao == 'resumo_centros':
        resultados = query.with_entities(
            CentroCusto.nome,
            func.sum(case((Transacao.tipo == 'Receita', Transacao.valor), else_=0)).label('entradas'),
            func.sum(case((Transacao.tipo == 'Despesa', Transacao.valor), else_=0)).label('saidas')
        ).join(CentroCusto, isouter=True).group_by(CentroCusto.id, CentroCusto.nome).order_by(CentroCusto.nome).all()

    elif visao == 'frota_detalhado':
        # Query para obter despesas por veículo e por categoria
        despesas_frota_raw = query.with_entities(
            CentroCusto.nome,
            PlanoConta.nome,
            func.sum(Transacao.valor).label('total')
        ).join(CentroCusto, Transacao.centro_custo_id == CentroCusto.id)\
         .join(PlanoConta, Transacao.plano_conta_id == PlanoConta.id)\
         .filter(
            Transacao.tipo == 'Despesa',
            CentroCusto.tipo == 'Veículo' # Filtra apenas para centros de custo do tipo 'Veículo'
         ).group_by(CentroCusto.nome, PlanoConta.nome)\
           .order_by(CentroCusto.nome, PlanoConta.nome).all()

        # Processa os dados brutos para o dicionário aninhado desejado
        relatorio_frota = {}
        for veiculo, categoria, total in despesas_frota_raw:
            if veiculo not in relatorio_frota:
                relatorio_frota[veiculo] = {'Total_Veiculo': Decimal(0)}
            relatorio_frota[veiculo][categoria] = total
            relatorio_frota[veiculo]['Total_Veiculo'] += total
        resultados = relatorio_frota
    else: # 'cronologico'
        transacoes_filtradas = query.order_by(Transacao.data_vencimento.asc(), Transacao.id.asc()).all()
        
        if portador_id and portador_id.isdigit():
            portador = Portador.query.get(int(portador_id))
            saldo_anterior = db.session.query(
                func.sum(case((Transacao.tipo == 'Receita', Transacao.valor), (Transacao.tipo == 'Despesa', -Transacao.valor), else_=0))
            ).filter(
                Transacao.portador_id == portador.id,
                Transacao.status == 'Realizado',
                Transacao.data_vencimento < data_inicio
            ).scalar() or Decimal(0)
            
            saldo_acumulado = portador.saldo_inicial + saldo_anterior
            
            for t in transacoes_filtradas:
                if t.tipo == 'Receita':
                    saldo_acumulado += t.valor
                else:
                    saldo_acumulado -= t.valor
                t.saldo_parcial = saldo_acumulado
        
        resultados = transacoes_filtradas

    return render_template('extrato.html',
                           visao=visao,
                           resultados=resultados,
                           total_entradas=total_entradas,
                           total_saidas=total_saidas,
                           resultado_periodo=resultado_periodo,
                           data_inicio=data_inicio,
                           data_fim=data_fim,
                           ignorar_transferencias=ignorar_transferencias)

@app.route('/extrato/exportar_csv')
@login_required
def extrato_exportar_csv():
    # --- 1. CAPTURA E APLICAÇÃO DOS FILTROS (Lógica idêntica à da rota /extrato) ---
    hoje = date.today()
    data_inicio_str = request.args.get('data_inicio', hoje.replace(day=1).strftime('%Y-%m-%d'))
    data_fim_str = request.args.get('data_fim', (hoje.replace(day=1) + relativedelta(months=1, days=-1)).strftime('%Y-%m-%d'))
    portador_id = request.args.get('portador_id')
    plano_conta_id = request.args.get('plano_conta_id')
    centro_custo_id = request.args.get('centro_custo_id')
    visao = request.args.get('visao', 'cronologico')
    ignorar_transferencias = request.args.get('ignorar_transferencias') == 'true'

    query = Transacao.query.filter(Transacao.status == 'Realizado')
    try:
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        query = query.filter(Transacao.data_vencimento.between(data_inicio, data_fim))
    except (ValueError, TypeError):
        pass

    if portador_id and portador_id.isdigit(): query = query.filter(Transacao.portador_id == int(portador_id))
    if plano_conta_id and plano_conta_id.isdigit(): query = query.filter(Transacao.plano_conta_id == int(plano_conta_id))
    if centro_custo_id and centro_custo_id.isdigit(): query = query.filter(Transacao.centro_custo_id == int(centro_custo_id))

    # Filtro para ignorar transferências (lógica idêntica à da rota principal)
    if ignorar_transferencias:
        transfer_sent_cat = PlanoConta.query.filter_by(codigo='02.99').with_entities(PlanoConta.id).first()
        transfer_received_cat = PlanoConta.query.filter_by(codigo='01.99').with_entities(PlanoConta.id).first()
        transfer_cat_ids = [cat_id[0] for cat_id in [transfer_sent_cat, transfer_received_cat] if cat_id]
        if transfer_cat_ids:
            query = query.filter(Transacao.plano_conta_id.notin_(transfer_cat_ids))

    # --- 2. GERAÇÃO DO CSV ---
    si = io.StringIO()
    cw = csv.writer(si, delimiter=';')
    
    if visao == 'resumo_categorias':
        resultados = query.with_entities(PlanoConta.nome, func.sum(case((Transacao.tipo == 'Receita', Transacao.valor), else_=0)).label('entradas'), func.sum(case((Transacao.tipo == 'Despesa', Transacao.valor), else_=0)).label('saidas')).join(PlanoConta, isouter=True).group_by(PlanoConta.id, PlanoConta.nome).order_by(PlanoConta.nome).all()
        cw.writerow(['Categoria', 'Entradas', 'Saidas', 'Resultado'])
        for r in resultados: cw.writerow([r.nome or "Sem Categoria", str(r.entradas).replace('.', ','), str(r.saidas).replace('.', ','), str(r.entradas - r.saidas).replace('.', ',')])

    elif visao == 'resumo_centros':
        resultados = query.with_entities(CentroCusto.nome, func.sum(case((Transacao.tipo == 'Receita', Transacao.valor), else_=0)).label('entradas'), func.sum(case((Transacao.tipo == 'Despesa', Transacao.valor), else_=0)).label('saidas')).join(CentroCusto, isouter=True).group_by(CentroCusto.id, CentroCusto.nome).order_by(CentroCusto.nome).all()
        cw.writerow(['Centro de Custo', 'Entradas', 'Saidas', 'Resultado'])
        for r in resultados: cw.writerow([r.nome or "Nao Alocado", str(r.entradas).replace('.', ','), str(r.saidas).replace('.', ','), str(r.entradas - r.saidas).replace('.', ',')])

    else: # 'cronologico'
        transacoes_filtradas = query.order_by(Transacao.data_vencimento.asc(), Transacao.id.asc()).all()
        cw.writerow(['Data', 'Conta', 'Descricao', 'Categoria', 'Centro de Custo', 'Tipo', 'Valor'])
        for t in transacoes_filtradas:
            cw.writerow([
                t.data_vencimento.strftime('%d/%m/%Y'),
                t.portador.nome if t.portador else '',
                t.descricao,
                t.categoria.nome if t.categoria else '',
                t.centro_custo.nome if t.centro_custo else '',
                t.tipo,
                str(t.valor).replace('.', ',')
            ])

    output = si.getvalue().encode('utf-8-sig') # utf-8-sig para compatibilidade com Excel
    si.close()

    return Response(output, mimetype="text/csv", headers={"Content-disposition": f"attachment; filename=extrato_{visao}_{date.today().strftime('%Y-%m-%d')}.csv"})

# --- FUNÇÃO AUXILIAR PARA CÁLCULO DE FATURA ---
def get_fatura_atual_periodo(dia_fechamento):
    hoje = date.today()
    # Se o dia de hoje for maior que o dia do fechamento, a fatura atual é a do próximo mês
    if hoje.day > dia_fechamento:
        proximo_mes = hoje + relativedelta(months=1)
        return proximo_mes.month, proximo_mes.year
    # Senão, a fatura atual ainda é a do mês corrente
    else:
        return hoje.month, hoje.year

@app.route('/cartoes')
@login_required
def cartoes():
    todos_cartoes = CartaoCredito.query.order_by(CartaoCredito.nome).all()
    cartoes_info = []

    for cartao in todos_cartoes:
        # 1. Calcula o período da fatura que está aberta no momento
        mes_fatura, ano_fatura = get_fatura_atual_periodo(cartao.dia_fechamento)

        # 2. Soma o valor das parcelas que compõem a fatura atual
        total_fatura_atual = db.session.query(func.sum(DespesaCartao.valor_parcela))\
            .filter(DespesaCartao.cartao_id == cartao.id)\
            .filter(DespesaCartao.fatura_mes == mes_fatura)\
            .filter(DespesaCartao.fatura_ano == ano_fatura)\
            .filter(DespesaCartao.transacao_pagamento_id == None)\
            .scalar() or Decimal('0.0')

        # 3. Soma TODAS as parcelas futuras (incluindo a fatura atual) para saber o limite consumido
        total_a_pagar_futuro = db.session.query(func.sum(DespesaCartao.valor_parcela))\
            .filter(DespesaCartao.cartao_id == cartao.id)\
            .filter(DespesaCartao.transacao_pagamento_id == None)\
            .scalar() or Decimal('0.0')
        
        limite_disponivel = cartao.limite - total_a_pagar_futuro

        cartoes_info.append({
            'cartao': cartao,
            'total_fatura_atual': total_fatura_atual,
            'limite_disponivel': limite_disponivel,
            'percentual_uso': (total_a_pagar_futuro / cartao.limite) * 100 if cartao.limite > 0 else 0,
            'mes_fatura_atual': mes_fatura,
            'ano_fatura_atual': ano_fatura
        })

    # Gera opções de Mês/Ano para o filtro de extrato
    meses_filtro = []
    data_base = date.today()
    for i in range(-12, 2): # Gera de 12 meses atrás até 1 mês no futuro
        d = data_base + relativedelta(months=i)
        meses_filtro.append({'valor': d.strftime('%Y-%m'), 'texto': d.strftime('%B/%Y').capitalize()})

    return render_template('cartoes.html', cartoes_info=cartoes_info, meses_filtro=reversed(meses_filtro))

@app.route('/usuarios')
@login_required
def usuarios():
    if current_user.perfil != 'Admin':
        flash('Acesso negado. Apenas administradores podem gerenciar usuários.', 'danger')
        return redirect(url_for('painel'))

    todos_usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template('usuarios.html', usuarios=todos_usuarios)


@app.route('/api/cartoes', methods=['POST'])
@login_required
def criar_cartao():
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    dados = request.get_json()

    try:
        novo_cartao = CartaoCredito(
            nome=dados['nome'],
            limite=Decimal(dados['limite'].replace('.', '').replace(',', '.')),
            dia_fechamento=int(dados['dia_fechamento']),
            dia_vencimento=int(dados['dia_vencimento'])
        )
        db.session.add(novo_cartao)
        db.session.commit()

        detalhes = f"Criou o cartão de crédito '{novo_cartao.nome}' com limite de R$ {novo_cartao.limite:.2f}."
        registrar_log('CRIAR', 'Cartões de Crédito', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Cartão cadastrado com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/despesas_cartao', methods=['POST'])
@login_required
def criar_despesa_cartao():
    dados = request.get_json()
    try:
        cartao = CartaoCredito.query.get_or_404(int(dados['cartao_id']))
        data_compra = datetime.strptime(dados['data_compra'], '%Y-%m-%d').date()
        valor_total = Decimal(dados['valor_total'].replace('.', '').replace(',', '.'))
        numero_parcelas = int(dados['numero_parcelas'])
        valor_parcela = (valor_total / Decimal(numero_parcelas)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Validação para garantir que o rateio é obrigatório
        centro_custo_id = dados.get('centro_custo_id')
        if not centro_custo_id or not dados.get('plano_conta_id'):
             return jsonify({'status': 'erro', 'mensagem': 'Os campos Plano de Contas e Centro de Custo são obrigatórios.'}), 400

        # Lógica para determinar a data da primeira fatura
        if data_compra.day > cartao.dia_fechamento:
            data_primeira_fatura = data_compra + relativedelta(months=1)
        else:
            data_primeira_fatura = data_compra

        # Cria um registro de despesa para cada parcela
        for i in range(numero_parcelas):
            data_fatura_parcela = data_primeira_fatura + relativedelta(months=i)
            
            nova_despesa = DespesaCartao(
                descricao=dados['descricao'],
                valor_total=valor_total,
                data_compra=data_compra,
                numero_parcelas=numero_parcelas,
                valor_parcela=valor_parcela,
                parcela_atual=i + 1,
                fatura_mes=data_fatura_parcela.month,
                fatura_ano=data_fatura_parcela.year,
                cartao_id=cartao.id,
                plano_conta_id=int(dados['plano_conta_id']),
                centro_custo_id=int(centro_custo_id)
            )
            db.session.add(nova_despesa)
        
        db.session.commit()

        detalhes = f"Lançou a despesa '{dados['descricao']}' no valor de R$ {valor_total:.2f} no cartão '{cartao.nome}'."
        registrar_log('CRIAR', 'Cartões de Crédito', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Despesa lançada com sucesso!'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/faturas', methods=['GET'])
@login_required
def get_fatura():
    cartao_id = request.args.get('cartao_id', type=int)
    periodo = request.args.get('periodo') # Formato 'YYYY-MM'

    if not all([cartao_id, periodo]):
        return jsonify({'status': 'erro', 'mensagem': 'Parâmetros inválidos.'}), 400

    ano, mes = map(int, periodo.split('-'))

    despesas = DespesaCartao.query.filter_by(cartao_id=cartao_id, fatura_mes=mes, fatura_ano=ano).order_by(DespesaCartao.data_compra.asc()).all()
    total_fatura = sum(d.valor_parcela for d in despesas)
    paga = despesas[0].transacao_pagamento_id is not None if despesas else False

    despesas_json = [{
        'data_compra': d.data_compra.strftime('%d/%m/%Y'),
        'descricao': d.descricao,
        'parcela_info': f"{d.parcela_atual}/{d.numero_parcelas}",
        'valor_parcela': f"{d.valor_parcela:.2f}".replace('.', ',')
    } for d in despesas]

    return jsonify({'status': 'sucesso', 'despesas': despesas_json, 'total_fatura': f"{total_fatura:.2f}".replace('.', ','), 'paga': paga})

@app.route('/api/portadores', methods=['POST'])
@login_required
def criar_portador():
    dados = request.get_json()
    
    try:
        novo_portador = Portador(
            nome=dados['nome'],
            tipo=dados['tipo'],
            saldo_inicial=Decimal(dados['saldo_inicial'].replace('.', '').replace(',', '.'))
        )
        
        db.session.add(novo_portador)
        db.session.commit()

        detalhes = f"Criou o portador '{novo_portador.nome}' do tipo '{novo_portador.tipo}'."
        registrar_log('CRIAR', 'Cadastros (Portadores)', detalhes)
        
        return jsonify({'status': 'sucesso', 'mensagem': 'Portador cadastrado!'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/planocontas', methods=['POST'])
@login_required
def criar_plano_conta():
    dados = request.get_json()
    try:
        if current_user.perfil != 'Admin':
            return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403
        novo_plano = PlanoConta(
            codigo=dados['codigo'],
            nome=dados['nome'],
            tipo=dados['tipo'],
            parent_id=dados.get('parent_id') or None
        )
        db.session.add(novo_plano)
        db.session.commit()

        detalhes = f"Criou a conta '{novo_plano.nome}' com código '{novo_plano.codigo}'."
        registrar_log('CRIAR', 'Cadastros (Plano de Contas)', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Plano de conta cadastrado!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/centroscusto', methods=['POST'])
@login_required
def criar_centro_custo():
    dados = request.get_json()
    try:
        if current_user.perfil != 'Admin':
            return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403
        novo_centro = CentroCusto(
            nome=dados['nome'],
            tipo=dados['tipo']
        )
        db.session.add(novo_centro)
        db.session.commit()

        detalhes = f"Criou o centro de custo '{novo_centro.nome}'."
        registrar_log('CRIAR', 'Cadastros (Centros de Custo)', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Centro de custo cadastrado!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/formaspagamento', methods=['POST'])
@login_required
def criar_forma_pagamento():
    dados = request.get_json()
    try:
        if current_user.perfil != 'Admin':
            return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403
        nova_forma = FormaPagamento(nome=dados['nome'])
        db.session.add(nova_forma)
        db.session.commit()

        detalhes = f"Criou a forma de pagamento '{nova_forma.nome}'."
        registrar_log('CRIAR', 'Cadastros (Formas de Pagamento)', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Forma de pagamento cadastrada!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/contas_pagar', methods=['POST'])
@login_required
def criar_conta_pagar():
    dados = request.get_json()
    try:
        nova_conta = ContaPagar(
            fornecedor_id=int(dados['fornecedor_id']),
            plano_conta_id=int(dados['plano_conta_id']),
            centro_custo_id=int(dados['centro_custo_id']),
            descricao=dados['descricao'],
            tipo_documento=dados['tipo_documento'],
            numero_documento=dados['numero_documento'],
            data_emissao=datetime.strptime(dados['data_emissao'], '%Y-%m-%d').date(),
            valor_total=Decimal(dados['valor_total'].replace('.', '').replace(',', '.')),
            usuario_id=current_user.id
        )
        db.session.add(nova_conta)
        db.session.flush()

        for p in dados['parcelas']:
            nova_parcela = ParcelaConta(
                conta_pagar_id=nova_conta.id,
                numero_parcela=int(p['numero_parcela']),
                valor_parcela=Decimal(p['valor_parcela'].replace('.', '').replace(',', '.')),
                data_vencimento=datetime.strptime(p['data_vencimento'], '%Y-%m-%d').date(),
                forma_pagto_id=int(p['forma_pagto_id'])
            )
            db.session.add(nova_parcela)
        db.session.commit()

        detalhes = f"Registrou a conta a pagar '{nova_conta.descricao}' no valor total de R$ {nova_conta.valor_total:.2f}."
        registrar_log('CRIAR', 'Contas a Pagar', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Conta a pagar registrada com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/lancamentos/<int:id>', methods=['DELETE'])
@login_required
def deletar_lancamento(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    try:
        # Busca a transação pelo ID. Se não achar, dá erro 404 automaticamente
        transacao = Transacao.query.get_or_404(id)
        
        detalhes = f"Excluiu o lançamento '{transacao.descricao}' no valor de R$ {transacao.valor:.2f} (ID: {transacao.id})."
        registrar_log('EXCLUIR', 'Lançamentos', detalhes)

        db.session.delete(transacao)
        db.session.commit()
        
        return jsonify({'status': 'sucesso', 'mensagem': 'Lançamento excluído com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/portadores/<int:id>', methods=['DELETE'])
@login_required
def deletar_portador(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    try:
        item = Portador.query.get_or_404(id)
        if item.transacoes:
            return jsonify({'status': 'erro', 'mensagem': 'Existem lançamentos associados a este portador.'}), 400
        
        detalhes = f"Excluiu o portador '{item.nome}' (ID: {item.id})."
        registrar_log('EXCLUIR', 'Cadastros (Portadores)', detalhes)

        db.session.delete(item)
        db.session.commit()
        return jsonify({'status': 'sucesso', 'mensagem': 'Portador excluído!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/planocontas/<int:id>', methods=['DELETE'])
@login_required
def deletar_plano_conta(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    try:
        item = PlanoConta.query.get_or_404(id)
        if item.transacoes:
            return jsonify({'status': 'erro', 'mensagem': 'Existem lançamentos associados a este item.'}), 400
        
        detalhes = f"Excluiu a conta '{item.nome}' (ID: {item.id})."
        registrar_log('EXCLUIR', 'Cadastros (Plano de Contas)', detalhes)

        db.session.delete(item)
        db.session.commit()
        return jsonify({'status': 'sucesso', 'mensagem': 'Plano de conta excluído!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/centroscusto/<int:id>', methods=['DELETE'])
@login_required
def deletar_centro_custo(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    try:
        item = CentroCusto.query.get_or_404(id)
        if item.transacoes:
            return jsonify({'status': 'erro', 'mensagem': 'Existem lançamentos associados a este item.'}), 400
        
        detalhes = f"Excluiu o centro de custo '{item.nome}' (ID: {item.id})."
        registrar_log('EXCLUIR', 'Cadastros (Centros de Custo)', detalhes)

        db.session.delete(item)
        db.session.commit()
        return jsonify({'status': 'sucesso', 'mensagem': 'Centro de custo excluído!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/formaspagamento/<int:id>', methods=['DELETE'])
@login_required
def deletar_forma_pagamento(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    item = FormaPagamento.query.get_or_404(id)
    if item.transacoes:
        return jsonify({'status': 'erro', 'mensagem': 'Existem lançamentos associados a este item.'}), 400
    
    detalhes = f"Excluiu a forma de pagamento '{item.nome}' (ID: {item.id})."
    registrar_log('EXCLUIR', 'Cadastros (Formas de Pagamento)', detalhes)

    db.session.delete(item)
    db.session.commit()
    return jsonify({'status': 'sucesso', 'mensagem': 'Forma de pagamento excluída!'})

@app.route('/api/fornecedores/<int:id>', methods=['DELETE'])
@login_required
def deletar_fornecedor(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    try:
        item = Fornecedor.query.get_or_404(id)
        if item.contas:
            return jsonify({'status': 'erro', 'mensagem': 'Este fornecedor possui contas a pagar associadas.'}), 400
        
        detalhes = f"Excluiu o fornecedor '{item.nome}' (ID: {item.id})."
        registrar_log('EXCLUIR', 'Cadastros (Fornecedores)', detalhes)

        db.session.delete(item)
        db.session.commit()
        return jsonify({'status': 'sucesso', 'mensagem': 'Fornecedor excluído!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

# 1. ROTA PARA BUSCAR OS DADOS (Preencher o Modal)
@app.route('/api/lancamentos/<int:id>', methods=['GET'])
@login_required
def get_lancamento(id):
    t = Transacao.query.get_or_404(id)
    return jsonify({
        'id': t.id,
        'tipo_operacao': t.tipo,
        'valor': f"{t.valor:.2f}".replace('.', ','), # Envia com vírgula para a nossa máscara JS
        'data_lancamento': t.data_vencimento.strftime('%Y-%m-%d'),
        'portador_id': t.portador_id,
        'plano_conta_id': t.plano_conta_id,
        'centro_custo_id': t.centro_custo_id or "",
        'forma_pagto_id': t.forma_pagto_id,
        'descricao': t.descricao,
        'status': t.status
    })

@app.route('/api/portadores/<int:id>', methods=['GET'])
@login_required
def get_portador(id):
    item = Portador.query.get_or_404(id)
    return jsonify({'id': item.id, 'nome': item.nome, 'tipo': item.tipo, 'saldo_inicial': f"{item.saldo_inicial:.2f}"})

@app.route('/api/planocontas/<int:id>', methods=['GET'])
@login_required
def get_plano_conta(id):
    item = PlanoConta.query.get_or_404(id)
    return jsonify({
        'id': item.id,
        'codigo': item.codigo,
        'nome': item.nome,
        'tipo': item.tipo,
        'parent_id': item.parent_id or ""
    })

@app.route('/api/centroscusto/<int:id>', methods=['GET'])
@login_required
def get_centro_custo(id):
    item = CentroCusto.query.get_or_404(id)
    return jsonify({
        'id': item.id,
        'nome': item.nome,
        'tipo': item.tipo
    })

@app.route('/api/formaspagamento/<int:id>', methods=['GET'])
@login_required
def get_forma_pagamento(id):
    item = FormaPagamento.query.get_or_404(id)
    return jsonify({'id': item.id, 'nome': item.nome})

@app.route('/api/fornecedores/<int:id>', methods=['GET'])
@login_required
def get_fornecedor(id):
    item = Fornecedor.query.get_or_404(id)
    return jsonify({
        'id': item.id,
        'nome': item.nome,
        'cnpj_cpf': item.cnpj_cpf or "",
        'status': item.status
    })

# 2. ROTA PARA SALVAR A EDIÇÃO (Update)
@app.route('/api/lancamentos/<int:id>', methods=['PUT'])
@login_required
def editar_lancamento(id):
    dados = request.get_json()
    try:
        t = Transacao.query.get_or_404(id)
        
        t.tipo = dados['tipo_operacao']
        t.descricao = dados['descricao']
        t.status = dados['status']
        
        # Reutiliza a lógica de tratamento da máscara de moeda
        valor_limpo = dados['valor'].replace('.', '').replace(',', '.')
        t.valor = Decimal(valor_limpo)
        
        t.data_vencimento = datetime.strptime(dados['data_lancamento'], '%Y-%m-%d').date()
        t.portador_id = int(dados['portador_id'])
        t.plano_conta_id = int(dados['plano_conta_id'])
        t.forma_pagto_id = int(dados['forma_pagto_id'])
        
        centro_id = dados.get('centro_custo_id')
        t.centro_custo_id = int(centro_id) if centro_id and centro_id.strip() != "" else None
        
        db.session.commit()

        detalhes = f"Editou o lançamento ID {id}."
        registrar_log('EDITAR', 'Lançamentos', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Lançamento atualizado com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/lancamentos/<int:id>/status', methods=['PUT'])
@login_required
def atualizar_status_lancamento(id):
    dados = request.get_json()
    novo_status = dados.get('status')

    if not novo_status or novo_status not in ['Previsto', 'Realizado']:
        return jsonify({'status': 'erro', 'mensagem': 'Status inválido fornecido.'}), 400

    try:
        transacao = Transacao.query.get_or_404(id)
        # Adiciona uma trava: se já estiver "Realizado", não permite alteração.
        if transacao.status == 'Realizado':
            return jsonify({'status': 'erro', 'mensagem': 'Este lançamento já foi realizado e não pode ser alterado.'}), 400

        transacao.status = novo_status
        db.session.commit()

        detalhes = f"Alterou o status do lançamento ID {id} para '{novo_status}'."
        registrar_log('EDITAR', 'Lançamentos', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': f'Status atualizado para {novo_status}!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500

@app.route('/api/portadores/<int:id>', methods=['PUT'])
@login_required
def editar_portador(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    dados = request.get_json()
    try:
        item = Portador.query.get_or_404(id)
        item.nome = dados['nome']
        item.tipo = dados['tipo']
        item.saldo_inicial = Decimal(dados['saldo_inicial'].replace('.', '').replace(',', '.'))
        db.session.commit()

        detalhes = f"Editou o portador ID {id}."
        registrar_log('EDITAR', 'Cadastros (Portadores)', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Portador atualizado!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/planocontas/<int:id>', methods=['PUT'])
@login_required
def editar_plano_conta(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    dados = request.get_json()
    try:
        item = PlanoConta.query.get_or_404(id)
        item.codigo = dados['codigo']
        item.nome = dados['nome']
        item.tipo = dados['tipo']
        item.parent_id = dados.get('parent_id') or None
        db.session.commit()

        detalhes = f"Editou a conta ID {id}."
        registrar_log('EDITAR', 'Cadastros (Plano de Contas)', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Plano de conta atualizado!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/centroscusto/<int:id>', methods=['PUT'])
@login_required
def editar_centro_custo(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    dados = request.get_json()
    try:
        item = CentroCusto.query.get_or_404(id)
        item.nome = dados['nome']
        item.tipo = dados['tipo']
        db.session.commit()

        detalhes = f"Editou o centro de custo ID {id}."
        registrar_log('EDITAR', 'Cadastros (Centros de Custo)', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Centro de custo atualizado!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/formaspagamento/<int:id>', methods=['PUT'])
@login_required
def editar_forma_pagamento(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    dados = request.get_json()
    item = FormaPagamento.query.get_or_404(id)
    item.nome = dados['nome']
    db.session.commit()

    detalhes = f"Editou a forma de pagamento ID {id}."
    registrar_log('EDITAR', 'Cadastros (Formas de Pagamento)', detalhes)
    return jsonify({'status': 'sucesso', 'mensagem': 'Forma de pagamento atualizada!'})

@app.route('/api/fornecedores/<int:id>', methods=['PUT'])
@login_required
def editar_fornecedor(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    dados = request.get_json()
    try:
        item = Fornecedor.query.get_or_404(id)
        item.nome = dados['nome']
        item.cnpj_cpf = dados.get('cnpj_cpf')
        item.status = dados['status']
        db.session.commit()

        detalhes = f"Editou o fornecedor ID {id}."
        registrar_log('EDITAR', 'Cadastros (Fornecedores)', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Fornecedor atualizado!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

# --- API PARA GESTÃO DE USUÁRIOS ---

@app.route('/api/usuarios', methods=['POST'])
@login_required
def criar_usuario():
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403
    
    dados = request.get_json()
    
    if not all([dados.get('nome'), dados.get('email'), dados.get('senha'), dados.get('perfil'), dados.get('status')]):
        return jsonify({'status': 'erro', 'mensagem': 'Todos os campos são obrigatórios para criar um usuário.'}), 400

    if Usuario.query.filter_by(email=dados['email']).first():
        return jsonify({'status': 'erro', 'mensagem': 'Este e-mail já está em uso.'}), 400

    try:
        novo_usuario = Usuario(
            nome=dados['nome'],
            email=dados['email'],
            perfil=dados['perfil'],
            status=dados['status']
        )
        novo_usuario.set_senha(dados['senha'])
        
        db.session.add(novo_usuario)
        db.session.commit()

        detalhes = f"Criou o usuário '{novo_usuario.nome}' (E-mail: {novo_usuario.email}) com perfil '{novo_usuario.perfil}'."
        registrar_log('CRIAR', 'Usuários', detalhes)
        
        return jsonify({'status': 'sucesso', 'mensagem': 'Usuário criado com sucesso!'}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/usuarios/<int:id>', methods=['GET'])
@login_required
def get_usuario(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    usuario = Usuario.query.get_or_404(id)
    return jsonify({
        'id': usuario.id,
        'nome': usuario.nome,
        'email': usuario.email,
        'perfil': usuario.perfil,
        'status': usuario.status
    })

@app.route('/api/usuarios/<int:id>', methods=['PUT'])
@login_required
def editar_usuario(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    dados = request.get_json()
    usuario = Usuario.query.get_or_404(id)

    if usuario.id == current_user.id and (dados.get('status') == 'Inativo' or dados.get('perfil') != 'Admin'):
        return jsonify({'status': 'erro', 'mensagem': 'Você não pode desativar ou alterar o perfil da sua própria conta de administrador.'}), 403

    if 'email' in dados and dados['email'] != usuario.email:
        if Usuario.query.filter(Usuario.email == dados['email'], Usuario.id != id).first():
            return jsonify({'status': 'erro', 'mensagem': 'Este e-mail já está em uso por outro usuário.'}), 400

    try:
        usuario.nome = dados.get('nome', usuario.nome)
        usuario.email = dados.get('email', usuario.email)
        usuario.perfil = dados.get('perfil', usuario.perfil)
        usuario.status = dados.get('status', usuario.status)

        if 'senha' in dados and dados['senha']:
            usuario.set_senha(dados['senha'])
        
        db.session.commit()

        detalhes = f"Editou o usuário '{usuario.nome}' (ID: {id})."
        registrar_log('EDITAR', 'Usuários', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Usuário atualizado com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/usuarios/<int:id>', methods=['DELETE'])
@login_required
def deletar_usuario(id):
    if current_user.perfil != 'Admin':
        return jsonify({'status': 'erro', 'mensagem': 'Acesso negado.'}), 403

    if id == current_user.id:
        return jsonify({'status': 'erro', 'mensagem': 'Você não pode excluir sua própria conta de administrador.'}), 403

    try:
        usuario = Usuario.query.get_or_404(id)
        
        detalhes = f"Excluiu o usuário '{usuario.nome}' (ID: {usuario.id})."
        registrar_log('EXCLUIR', 'Usuários', detalhes)

        db.session.delete(usuario)
        db.session.commit()
        
        return jsonify({'status': 'sucesso', 'mensagem': 'Usuário excluído com sucesso!'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/faturas/pagar', methods=['POST'])
@login_required
def pagar_fatura():
    dados = request.get_json()
    try:
        cartao_id = int(dados['cartao_id'])
        periodo = dados['periodo'] # Formato 'YYYY-MM'
        portador_id = int(dados['portador_id'])
        # Captura a data do pagamento do request, com fallback para a data atual
        data_pagamento_str = dados.get('data_pagamento', date.today().strftime('%Y-%m-%d'))
        data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()
        
        ano, mes = map(int, periodo.split('-'))
        cartao = CartaoCredito.query.get_or_404(cartao_id)

        despesas_fatura = DespesaCartao.query.filter_by(cartao_id=cartao_id, fatura_mes=mes, fatura_ano=ano, transacao_pagamento_id=None).all()

        if not despesas_fatura:
            return jsonify({'status': 'erro', 'mensagem': 'Fatura não encontrada ou já está paga.'}), 400

        # Busca uma forma de pagamento padrão para a transação de baixa
        forma_pagto_padrao = FormaPagamento.query.filter(FormaPagamento.nome.ilike('%transferência%')).first()
        if not forma_pagto_padrao:
            forma_pagto_padrao = FormaPagamento.query.first()
            if not forma_pagto_padrao:
                 return jsonify({'status': 'erro', 'mensagem': 'Nenhuma Forma de Pagamento encontrada no sistema.'}), 500

        total_pago = Decimal('0.0')
        # --- INÍCIO DA NOVA LÓGICA DE DESMEMBRAMENTO ---
        for despesa in despesas_fatura:
            # Para cada item da fatura, cria uma transação de saída individual
            transacao_pagamento = Transacao(
                tipo='Despesa',
                descricao=f"Pgto Fatura {cartao.nome}: {despesa.descricao}",
                status='Realizado',
                valor=despesa.valor_parcela,
                data_vencimento=data_pagamento, # Usa a data do pagamento informada
                portador_id=portador_id,
                plano_conta_id=despesa.plano_conta_id,      # Preserva a categoria original
                centro_custo_id=despesa.centro_custo_id,  # Preserva o centro de custo original
                forma_pagto_id=forma_pagto_padrao.id,
                usuario_id=current_user.id
            )
            db.session.add(transacao_pagamento)
            db.session.flush() # Obtém o ID da transação antes do commit

            # Vincula a despesa do cartão à sua transação de pagamento correspondente
            despesa.transacao_pagamento_id = transacao_pagamento.id
            total_pago += despesa.valor_parcela
        
        db.session.commit()

        detalhes = f"Pagou a fatura do cartão '{cartao.nome}' (período {mes:02d}/{ano}) no valor de R$ {total_pago:.2f}, gerando {len(despesas_fatura)} lançamentos individuais."
        registrar_log('PAGAR', 'Cartões de Crédito', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Fatura paga com sucesso! Os lançamentos foram desmembrados no extrato.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/api/parcelas/pagar/<int:id>', methods=['POST'])
@login_required
def pagar_parcela(id):

    dados = request.get_json()
    try:
        portador_id = int(dados['portador_id'])
        data_pagamento_str = dados['data_pagamento']
        data_pagamento = datetime.strptime(data_pagamento_str, '%Y-%m-%d').date()

        parcela = ParcelaConta.query.get_or_404(id)

        if parcela.status == 'Pago' or parcela.transacao_pagamento_id is not None:
            return jsonify({'status': 'erro', 'mensagem': 'Esta parcela já foi paga.'}), 400

        # 1. Cria a transação de despesa real
        transacao_pagamento = Transacao(
            tipo='Despesa',
            descricao=f"Pgto Parcela {parcela.numero_parcela}/{len(parcela.conta_pagar.parcelas)} - {parcela.conta_pagar.descricao}",
            status='Realizado',
            valor=parcela.valor_parcela,
            data_vencimento=data_pagamento, # Data em que o pagamento foi efetuado
            portador_id=portador_id,
            plano_conta_id=parcela.conta_pagar.plano_conta_id,
            centro_custo_id=parcela.conta_pagar.centro_custo_id,
            forma_pagto_id=parcela.forma_pagto_id,
            usuario_id=current_user.id
        )
        db.session.add(transacao_pagamento)
        db.session.flush() # Para obter o ID da transação

        # 2. Vincula a transação à parcela e atualiza o status
        parcela.transacao_pagamento_id = transacao_pagamento.id
        parcela.status = 'Pago'
        
        db.session.commit()

        detalhes = f"Pagou a parcela {parcela.numero_parcela} da conta '{parcela.conta_pagar.descricao}' no valor de R$ {parcela.valor_parcela:.2f}."
        registrar_log('PAGAR', 'Contas a Pagar', detalhes)
        return jsonify({'status': 'sucesso', 'mensagem': 'Parcela paga com sucesso!'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 400

@app.route('/logs')
@login_required
def logs():
    if current_user.perfil != 'Admin':
        flash('Acesso negado. Apenas administradores podem ver os logs.', 'danger')
        return redirect(url_for('painel'))

    query = LogAuditoria.query

    # Filtros
    usuario_id = request.args.get('usuario_id')
    modulo = request.args.get('modulo')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    if usuario_id:
        query = query.filter(LogAuditoria.usuario_id == usuario_id)
    if modulo:
        query = query.filter(LogAuditoria.modulo == modulo)
    if data_inicio:
        query = query.filter(LogAuditoria.data_hora >= datetime.strptime(data_inicio, '%Y-%m-%d'))
    if data_fim:
        data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + relativedelta(days=1)
        query = query.filter(LogAuditoria.data_hora < data_fim_dt)

    logs_resultado = query.order_by(LogAuditoria.data_hora.desc()).all()
    
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    modulos = db.session.query(LogAuditoria.modulo).distinct().order_by(LogAuditoria.modulo).all()

    return render_template('logs.html', 
                           logs=logs_resultado, 
                           usuarios=usuarios, 
                           modulos=[m[0] for m in modulos])

@app.route('/relatorios')
@login_required
def relatorios():
    if current_user.perfil != 'Admin':
        flash('Acesso negado. Apenas administradores podem ver os relatórios.', 'danger')
        return redirect(url_for('painel'))

    hoje = date.today()
    # Usa o mês atual como padrão se nenhuma data for fornecida
    data_inicio_str = request.args.get('data_inicio', hoje.replace(day=1).strftime('%Y-%m-%d'))
    data_fim_str = request.args.get('data_fim', (hoje.replace(day=1) + relativedelta(months=1, days=-1)).strftime('%Y-%m-%d'))

    data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
    data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

    # --- 1. DRE Simplificado ---
    base_query = db.session.query(
        PlanoConta.codigo,
        PlanoConta.nome,
        func.sum(Transacao.valor).label('total')
    ).join(Transacao, Transacao.plano_conta_id == PlanoConta.id)\
     .filter(
        Transacao.status == 'Realizado',
        Transacao.data_vencimento.between(data_inicio, data_fim),
        PlanoConta.codigo.notin_(['01.99', '02.99']) # Exclui transferências do DRE
     ).group_by(PlanoConta.codigo, PlanoConta.nome).all()

    # Estrutura do DRE
    dre = {
        'receita_bruta': {'total': Decimal(0), 'items': []},
        'custos_variaveis': {'total': Decimal(0), 'items': []},
        'custos_fixos': {'total': Decimal(0), 'items': []},
        'despesas_admin': {'total': Decimal(0), 'items': []},
        'impostos': {'total': Decimal(0), 'items': []},
    }

    for item in base_query:
        if item.codigo.startswith('01'):
            dre['receita_bruta']['items'].append(item)
            dre['receita_bruta']['total'] += item.total
        elif item.codigo.startswith('02.01'):
            dre['custos_variaveis']['items'].append(item)
            dre['custos_variaveis']['total'] += item.total
        elif item.codigo.startswith('02.02'):
            dre['custos_fixos']['items'].append(item)
            dre['custos_fixos']['total'] += item.total
        elif item.codigo.startswith('02.03'):
            dre['despesas_admin']['items'].append(item)
            dre['despesas_admin']['total'] += item.total
        elif item.codigo.startswith('02.04'):
            dre['impostos']['items'].append(item)
            dre['impostos']['total'] += item.total
    
    dre['margem_contribuicao'] = dre['receita_bruta']['total'] - dre['custos_variaveis']['total']
    dre['resultado_operacional'] = dre['margem_contribuicao'] - dre['custos_fixos']['total'] - dre['despesas_admin']['total']
    dre['lucro_liquido'] = dre['resultado_operacional'] - dre['impostos']['total']

    # --- 2. Análise de Frota (Centros de Custo) ---
    despesas_por_centro_query = db.session.query(
        CentroCusto.nome, func.sum(Transacao.valor).label('total')
    ).join(Transacao, Transacao.centro_custo_id == CentroCusto.id)\
     .join(PlanoConta, Transacao.plano_conta_id == PlanoConta.id)\
     .filter(
        Transacao.tipo == 'Despesa', 
        Transacao.status == 'Realizado', 
        Transacao.data_vencimento.between(data_inicio, data_fim),
        PlanoConta.codigo != '02.99' # Exclui despesas de transferência da análise
    ).group_by(CentroCusto.nome).order_by(func.sum(Transacao.valor).desc()).all()

    # Converte o resultado da query (que são objetos Row) para uma lista de dicionários.
    # Isso é mais seguro para passar para templates, especialmente se os dados forem ser usados em JavaScript (gráficos).
    despesas_por_centro = [{'nome': centro.nome, 'total': float(centro.total)} for centro in despesas_por_centro_query]

    # --- 3. Gráfico de Despesas por Categoria (Donut) ---
    dados_donut = {
        'labels': ['Custos Variáveis', 'Custos Fixos', 'Despesas Admin', 'Impostos'],
        'valores': [float(dre['custos_variaveis']['total']), float(dre['custos_fixos']['total']), float(dre['despesas_admin']['total']), float(dre['impostos']['total'])]
    }

    return render_template('relatorios.html', data_inicio=data_inicio, data_fim=data_fim, dre=dre, despesas_por_centro=despesas_por_centro, dados_donut_json=json.dumps(dados_donut))

@app.route('/admin/backups')
@login_required
def backups():
    if current_user.perfil != 'Admin':
        flash('Acesso negado. Apenas administradores podem gerenciar backups.', 'danger')
        return redirect(url_for('painel'))

    lista_backups = []
    try:
        arquivos = sorted(os.listdir(BACKUP_DIR), reverse=True)
        for arquivo in arquivos:
            caminho_completo = os.path.join(BACKUP_DIR, arquivo)
            if os.path.isfile(caminho_completo):
                lista_backups.append({
                    'nome': arquivo,
                    'data_criacao': datetime.fromtimestamp(os.path.getmtime(caminho_completo)).strftime('%d/%m/%Y %H:%M:%S'),
                    'tamanho': os.path.getsize(caminho_completo) / (1024 * 1024) # em MB
                })
    except Exception as e:
        flash(f"Erro ao listar backups: {str(e)}", "danger")

    return render_template('backups.html', backups=lista_backups)

@app.route('/admin/backups/gerar')
@login_required
def gerar_backup_manual():
    if current_user.perfil != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))
    
    sucesso, mensagem = gerar_backup()
    if sucesso:
        flash(mensagem, 'success')
    else:
        flash(mensagem, 'danger')
    
    return redirect(url_for('backups'))

@app.route('/admin/backups/download/<path:filename>')
@login_required
def download_backup(filename):
    if current_user.perfil != 'Admin':
        flash('Acesso negado.', 'danger')
        return redirect(url_for('painel'))
    
    try:
        return send_from_directory(BACKUP_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        flash('Arquivo de backup não encontrado.', 'danger')
        return redirect(url_for('backups'))

if __name__ == '__main__':
    # Roda o servidor em modo debug para facilitar o desenvolvimento
    app.run(debug=True)
    
    #Teste