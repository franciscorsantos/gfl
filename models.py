
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# Convenção de nomenclatura para todas as constraints (chaves, índices, etc.)
# Isso resolve o erro "ValueError: Constraint must have a name" no SQLite.
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Instância do banco de dados com a convenção de nomenclatura nos metadados
db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))

class LogAuditoria(db.Model):
    __tablename__ = 'log_auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    acao = db.Column(db.String(50), nullable=False) # 'CRIAR', 'EDITAR', 'EXCLUIR', 'PAGAR', 'LOGIN'
    modulo = db.Column(db.String(100), nullable=False) # 'Lançamentos', 'Contas a Pagar', etc.
    detalhes = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<Log {self.id} - {self.acao} em {self.modulo}>'

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default='Operador') # 'Admin' ou 'Operador'
    status = db.Column(db.String(10), nullable=False, default='Ativo') # 'Ativo' ou 'Inativo'

    transacoes = db.relationship('Transacao', backref='usuario', lazy=True)
    contas_a_pagar = db.relationship('ContaPagar', backref='usuario', lazy=True)
    logs = db.relationship('LogAuditoria', backref='usuario', lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def __repr__(self):
        return f'<Usuario {self.nome}>'

class Portador(db.Model):
    __tablename__ = 'portador'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False) # 'Banco', 'Caixa Físico', 'Adiantamento'
    saldo_inicial = db.Column(db.Numeric(10, 2), default=0.00)
    ativo = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    transacoes = db.relationship('Transacao', backref='portador', lazy=True)
    transferencias_origem = db.relationship('Transferencia', foreign_keys='Transferencia.origem_id', backref='conta_origem', lazy=True)
    transferencias_destino = db.relationship('Transferencia', foreign_keys='Transferencia.destino_id', backref='conta_destino', lazy=True)

    def __repr__(self):
        return f'<Portador {self.nome}>'

class PlanoConta(db.Model):
    __tablename__ = 'plano_conta'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), nullable=False) # Adicionado: Ex: 01.01.01
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), nullable=False) # 'Receita' ou 'Despesa'
    parent_id = db.Column(db.Integer, db.ForeignKey('plano_conta.id'), nullable=True)
    
    transacoes = db.relationship('Transacao', backref='categoria', lazy=True)

    def __repr__(self):
        return f'<PlanoConta {self.codigo} - {self.nome}>'

class CentroCusto(db.Model):
    __tablename__ = 'centro_custo'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False) # Ex: Placa ABC-1234, Rota SP-RJ
    tipo = db.Column(db.String(50), nullable=False) # 'Veículo', 'Rota', 'Geral'
    
    transacoes = db.relationship('Transacao', backref='centro_custo', lazy=True)

    def __repr__(self):
        return f'<CentroCusto {self.nome}>'

class FormaPagamento(db.Model):
    __tablename__ = 'forma_pagamento'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False) # Pix, Boleto, Dinheiro, etc.
    
    transacoes = db.relationship('Transacao', backref='forma_pagamento', lazy=True)

    def __repr__(self):
        return f'<FormaPagamento {self.nome}>'

class Transacao(db.Model):
    __tablename__ = 'transacao'
    
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False) # 'Receita' ou 'Despesa'
    descricao = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Previsto') # 'Previsto', 'Realizado'
    conciliado = db.Column(db.Boolean, default=False)
    anexo_url = db.Column(db.String(255), nullable=True)
    
    # Chaves Estrangeiras
    portador_id = db.Column(db.Integer, db.ForeignKey('portador.id'), nullable=False)
    plano_conta_id = db.Column(db.Integer, db.ForeignKey('plano_conta.id'), nullable=False)
    forma_pagto_id = db.Column(db.Integer, db.ForeignKey('forma_pagamento.id'), nullable=False)
    centro_custo_id = db.Column(db.Integer, db.ForeignKey('centro_custo.id'), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    def __repr__(self):
        return f'<Transacao {self.descricao} - {self.valor}>'

class Transferencia(db.Model):
    __tablename__ = 'transferencia'
    
    id = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    descricao = db.Column(db.String(255), nullable=True)
    
    # Chaves Estrangeiras indicando o fluxo do dinheiro
    origem_id = db.Column(db.Integer, db.ForeignKey('portador.id'), nullable=False)
    destino_id = db.Column(db.Integer, db.ForeignKey('portador.id'), nullable=False)

    def __repr__(self):
        return f'<Transferencia {self.origem_id} -> {self.destino_id} : {self.valor}>'

class CartaoCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    limite = db.Column(db.Numeric(10, 2), nullable=False)
    dia_fechamento = db.Column(db.Integer, nullable=False)
    dia_vencimento = db.Column(db.Integer, nullable=False)
    
    despesas = db.relationship('DespesaCartao', backref='cartao', lazy=True, cascade="all, delete-orphan")

class DespesaCartao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    data_compra = db.Column(db.Date, nullable=False)
    numero_parcelas = db.Column(db.Integer, nullable=False, default=1)
    valor_parcela = db.Column(db.Numeric(10, 2), nullable=False)
    parcela_atual = db.Column(db.Integer, nullable=False)
    fatura_mes = db.Column(db.Integer, nullable=False)
    fatura_ano = db.Column(db.Integer, nullable=False)
    cartao_id = db.Column(db.Integer, db.ForeignKey('cartao_credito.id'), nullable=False)
    plano_conta_id = db.Column(db.Integer, db.ForeignKey('plano_conta.id'), nullable=False)
    centro_custo_id = db.Column(db.Integer, db.ForeignKey('centro_custo.id'), nullable=False)
    transacao_pagamento_id = db.Column(db.Integer, db.ForeignKey('transacao.id'), nullable=True)
    categoria = db.relationship('PlanoConta', backref='despesas_cartao', lazy=True)
    centro_custo = db.relationship('CentroCusto', backref='despesas_cartao', lazy=True)

class Fornecedor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False, unique=True)
    cnpj_cpf = db.Column(db.String(20), nullable=True, unique=True)
    status = db.Column(db.String(10), nullable=False, default='Ativo') # Ativo/Inativo
    contas = db.relationship('ContaPagar', backref='fornecedor', lazy=True)

class ContaPagar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor_total = db.Column(db.Numeric(10, 2), nullable=False)
    tipo_documento = db.Column(db.String(50), nullable=True)
    numero_documento = db.Column(db.String(50), nullable=True)
    data_emissao = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, db.ForeignKey('fornecedor.id'), nullable=False)
    plano_conta_id = db.Column(db.Integer, db.ForeignKey('plano_conta.id'), nullable=False)
    centro_custo_id = db.Column(db.Integer, db.ForeignKey('centro_custo.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    parcelas = db.relationship('ParcelaConta', backref='conta_pagar', lazy=True, cascade="all, delete-orphan")
    centro_custo = db.relationship('CentroCusto', backref='contas_a_pagar', lazy=True)

class ParcelaConta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_parcela = db.Column(db.Integer, nullable=False)
    valor_parcela = db.Column(db.Numeric(10, 2), nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pendente') # Pendente/Pago
    conta_pagar_id = db.Column(db.Integer, db.ForeignKey('conta_pagar.id'), nullable=False)
    forma_pagto_id = db.Column(db.Integer, db.ForeignKey('forma_pagamento.id'), nullable=False)
    transacao_pagamento_id = db.Column(db.Integer, db.ForeignKey('transacao.id'), nullable=True)

    forma_pagamento = db.relationship('FormaPagamento', backref='parcelas_a_pagar')