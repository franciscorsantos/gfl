from app import app, db
from models import (
    Portador, PlanoConta, FormaPagamento, CentroCusto, Fornecedor, Usuario
)
from datetime import datetime
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

def realizar_carga_inicial():
    """
    Função responsável por popular o banco de dados com dados iniciais
    se as tabelas estiverem vazias.
    """
    with app.app_context():
        # ==========================================
        # CARGA INICIAL: PLANO DE CONTAS
        # ==========================================
        if PlanoConta.query.first() is None:
            categorias = [
                # ==========================================
                # 01 - RECEITAS (Sintética)
                # ==========================================
                PlanoConta(codigo="01", nome="Receitas", tipo="Receita"),
                
                # Detalhamento de Receitas
                PlanoConta(codigo="01.01", nome="Fretes / Transportes", tipo="Receita"),
                PlanoConta(codigo="01.02", nome="Redespacho", tipo="Receita"),
                PlanoConta(codigo="01.03", nome="Armazenagem", tipo="Receita"),
                PlanoConta(codigo="01.04", nome="Venda de Ativos", tipo="Receita"),
                PlanoConta(codigo="01.05", nome="Taxas Adicionais (TRT, TDE, Ad Valorem / GRIS)", tipo="Receita"),
                PlanoConta(codigo="01.06", nome="Receita de Indenizações / Seguros", tipo="Receita"),

                # Categoria para transferências
                PlanoConta(codigo="01.99", nome="Transferência Recebida", tipo="Receita"),

                # ==========================================
                # 02 - DESPESAS E CUSTOS (Sintética Geral)
                # ==========================================
                PlanoConta(codigo="02", nome="Despesas e Custos", tipo="Despesa"),

                # --- 02.01 CUSTOS VARIÁVEIS (VEÍCULO) (Sintética) ---
                PlanoConta(codigo="02.01", nome="Custos Variáveis (Veículo)", tipo="Despesa"),
                
                # Detalhamento Custos Variáveis
                PlanoConta(codigo="02.01.01", nome="Combustível", tipo="Despesa"),
                PlanoConta(codigo="02.01.02", nome="Manutenção Preventiva", tipo="Despesa"),
                PlanoConta(codigo="02.01.03", nome="Manutenção Corretiva", tipo="Despesa"),
                PlanoConta(codigo="02.01.04", nome="Pneus", tipo="Despesa"),
                PlanoConta(codigo="02.01.05", nome="Pedágio / Estacionamento", tipo="Despesa"),
                PlanoConta(codigo="02.01.06", nome="Sinistro / Franquia", tipo="Despesa"),
                PlanoConta(codigo="02.01.07", nome="Diárias / Alimentação Motorista", tipo="Despesa"),
                PlanoConta(codigo="02.01.08", nome="Custo com Agregados / Terceiros", tipo="Despesa"),
                PlanoConta(codigo="02.01.09", nome="Óleo Lubrificante / Arla 32", tipo="Despesa"),
                PlanoConta(codigo="02.01.10", nome="Lavagem e Higienização da Frota", tipo="Despesa"),
                PlanoConta(codigo="02.01.11", nome="Chapa / Diárias de Carga e Descarga", tipo="Despesa"),

                # --- 02.02 CUSTOS FIXOS (OPERACIONAL) (Sintética) ---
                PlanoConta(codigo="02.02", nome="Custos Fixos (Operacional)", tipo="Despesa"),
                
                # Detalhamento Custos Fixos
                PlanoConta(codigo="02.02.01", nome="Folha de Pagamento", tipo="Despesa"),
                PlanoConta(codigo="02.02.02", nome="Encargos sobre a Folha", tipo="Despesa"),
                PlanoConta(codigo="02.02.03", nome="Seguros", tipo="Despesa"),
                PlanoConta(codigo="02.02.04", nome="Monitoramento / Rastreamento", tipo="Despesa"),
                PlanoConta(codigo="02.02.05", nome="Documentação Frota", tipo="Despesa"),
                PlanoConta(codigo="02.02.06", nome="Aluguel de Frota", tipo="Despesa"),
                PlanoConta(codigo="02.02.07", nome="Depreciação da Frota", tipo="Despesa"),
                PlanoConta(codigo="02.02.08", nome="Exames Médicos / Toxicológicos / Treinamentos", tipo="Despesa"),
                PlanoConta(codigo="02.02.09", nome="EPIs e Uniformes Operacionais", tipo="Despesa"),

                # --- 02.03 DESPESAS ADMINISTRATIVAS (Sintética) ---
                PlanoConta(codigo="02.03", nome="Despesas Administrativas", tipo="Despesa"),
                
                # Detalhamento Despesas Administrativas
                PlanoConta(codigo="02.03.01", nome="Energia Elétrica", tipo="Despesa"),
                PlanoConta(codigo="02.03.02", nome="Água e Esgoto", tipo="Despesa"),
                PlanoConta(codigo="02.03.03", nome="Internet", tipo="Despesa"),
                PlanoConta(codigo="02.03.04", nome="Telefonia Fixa / Móvel", tipo="Despesa"),
                PlanoConta(codigo="02.03.05", nome="Softwares e Sistemas", tipo="Despesa"),
                PlanoConta(codigo="02.03.06", nome="Contabilidade", tipo="Despesa"),
                PlanoConta(codigo="02.03.07", nome="Tarifas Bancárias", tipo="Despesa"),
                PlanoConta(codigo="02.03.08", nome="Pro-Labore", tipo="Despesa"),
                PlanoConta(codigo="02.03.09", nome="Encargos sobre o Pro-Labore", tipo="Despesa"),
                PlanoConta(codigo="02.03.10", nome="Material de Escritorio", tipo="Despesa"),
                PlanoConta(codigo="02.03.11", nome="Material de Limpeza", tipo="Despesa"),
                PlanoConta(codigo="02.03.12", nome="Brindes / Patricionios", tipo="Despesa"),
                PlanoConta(codigo="02.03.13", nome="Outras Despesas Administrativas", tipo="Despesa"),
                PlanoConta(codigo="02.03.14", nome="Salários Administrativos", tipo="Despesa"),
                PlanoConta(codigo="02.03.15", nome="Comissões sobre Vendas / Fretes", tipo="Despesa"),
                PlanoConta(codigo="02.03.16", nome="Marketing e Publicidade", tipo="Despesa"),
                PlanoConta(codigo="02.03.17", nome="Viagens e Representação Comercial", tipo="Despesa"),
                PlanoConta(codigo="02.03.18", nome="Licenças e Alvarás Administrativos", tipo="Despesa"),

                # --- 02.04 IMPOSTOS (Sintética) ---
                PlanoConta(codigo="02.04", nome="Impostos", tipo="Despesa"),
                
                # Detalhamento Impostos
                PlanoConta(codigo="02.04.01", nome="Simples Nacional", tipo="Despesa"),
                PlanoConta(codigo="02.04.02", nome="ICMS / ST ou Diferencial de Alíquota (Difal)", tipo="Despesa"),
                PlanoConta(codigo="02.04.03", nome="Taxas Regulatórias (ANTT / SEST SENAT)", tipo="Despesa"),

                # --- 02.05 INVESTIMENTOS / OUTRAS SAÍDAS (Sintética) ---
                PlanoConta(codigo="02.05", nome="Investimentos / Outras Saídas", tipo="Despesa"),
                
                # Detalhamento Investimentos
                PlanoConta(codigo="02.05.01", nome="Pgto. Emprestimos / Financiamentos", tipo="Despesa"),
                PlanoConta(codigo="02.05.02", nome="Reserva de Emergência", tipo="Despesa"),

                # Categoria para transferências
                PlanoConta(codigo="02.99", nome="Transferência Enviada", tipo="Despesa"),
            ]
            
            db.session.add_all(categorias)
            db.session.commit()
            print("✅ Carga inicial do Plano de Contas Logístico realizada com sucesso!")

        # ==========================================
        # CARGA INICIAL: FORMAS DE PAGAMENTO
        # ==========================================
        if FormaPagamento.query.first() is None:
            formas = [
                FormaPagamento(nome="Pix"),
                FormaPagamento(nome="Boleto Bancário"),
                FormaPagamento(nome="Cartão de Crédito"),
                FormaPagamento(nome="Cartão de Débito"),
                FormaPagamento(nome="Transferência (TED / DOC)"),
                FormaPagamento(nome="Dinheiro em Espécie"),
            ]
            
            db.session.add_all(formas)
            db.session.commit()
            print("✅ Carga inicial de Formas de Pagamento realizada com sucesso!")

        # ==========================================
        # CARGA INICIAL: FORNECEDORES
        # ==========================================
        if Fornecedor.query.first() is None:
            fornecedores = [
                Fornecedor(nome="Posto Shell - Rodovia", cnpj_cpf="11.222.333/0001-44", status="Ativo"),
                Fornecedor(nome="Pneumar Pneus e Peças", cnpj_cpf="44.555.666/0001-77", status="Ativo"),
                Fornecedor(nome="Oficina Diesel Rápido", cnpj_cpf="77.888.999/0001-00", status="Ativo"),
                Fornecedor(nome="Fornecedor Inativo Teste", cnpj_cpf="00.000.000/0001-00", status="Inativo"),
            ]
            db.session.add_all(fornecedores)
            db.session.commit()
            print("✅ Carga inicial de Fornecedores realizada com sucesso!")
            
        # ==========================================
        # CARGA INICIAL: CENTROS DE CUSTO (FROTA/ROTAS)
        # ==========================================
        if CentroCusto.query.first() is None:
            centros = [
                # Veículos Físicos
                CentroCusto(nome="Caminhão Scania R450 (Placa ABC-1234)", tipo="Veículo"),
                CentroCusto(nome="Caminhão Volvo FH540 (Placa XYZ-9876)", tipo="Veículo"),
                CentroCusto(nome="Veículo Leve / Apoio (Fiorino)", tipo="Veículo"),
                
                # Controle por Rotas
                CentroCusto(nome="Operação - Rota Caxias/MA x Teresina/PI", tipo="Rota"),
                CentroCusto(nome="Operação - Rota Caxias/MA x São Luís/MA", tipo="Rota"),
                
                # Despesas Gerais
                CentroCusto(nome="Administrativo - Meliá Transportes", tipo="Geral/Administrativo")
            ]
            
            db.session.add_all(centros)
            db.session.commit()
            print("✅ Carga inicial de Centros de Custo realizada com sucesso!")

        # ==========================================
        # CARGA INICIAL: USUÁRIO ADMIN
        # ==========================================
        if Usuario.query.first() is None:
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@gfl.com')
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')

            admin_user = Usuario(
                nome='Administrador',
                email=admin_email,
                perfil='Admin',
                status='Ativo'
            )
            admin_user.set_senha(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"✅ Usuário Administrador padrão criado com sucesso! (E-mail: {admin_email}, Senha: {admin_password})")

if __name__ == '__main__':
    print("Iniciando carga inicial do banco de dados...")
    realizar_carga_inicial()
    print("Carga inicial concluída.")