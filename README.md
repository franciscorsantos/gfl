# Sistema GFL - Gestão Financeira Logística

## 1. Visão Geral

O **GFL** é um sistema ERP (Enterprise Resource Planning) monolítico, desenvolvido em Python com o microframework Flask, focado na gestão financeira e com módulos adaptados para o setor de logística. Ele oferece controle de fluxo de caixa, contas a pagar, gestão de faturas de cartão de crédito, relatórios gerenciais e muito mais.

## 2. Funcionalidades Principais

- **Dashboard Intuitivo**: Visualização rápida do saldo consolidado, saldos por conta e principais indicadores.
- **Gestão de Transações**: Lançamento de receitas e despesas com classificação por plano de contas e centro de custo.
- **Contas a Pagar**: Lançamento de notas fiscais com parcelamento dinâmico e controle de baixas (pagamentos).
- **Gestão de Cartões de Crédito**: Cadastro de despesas, visualização de faturas por período e pagamento desmembrado no extrato.
- **Transferências Atômicas**: Movimentação de valores entre contas internas com garantia de consistência.
- **Cadastros Auxiliares**: Gerenciamento de Portadores (contas), Plano de Contas hierárquico, Centros de Custo, Fornecedores e Formas de Pagamento.
- **Relatórios Gerenciais**:
    - Extrato dinâmico com múltiplos filtros e exportação para CSV.
    - DRE (Demonstrativo de Resultado do Exercício) simplificado.
    - Análise de custos por Centro de Custo (foco em frota).
- **Controle de Acesso**: Sistema de usuários com perfis (Admin, Operador) e autenticação.
- **Auditoria**: Registro de logs para todas as ações críticas realizadas no sistema.
- **Backups Automatizados**: Rotina diária para backup do banco de dados e interface para gerenciamento manual.

## 3. Stack Tecnológica

- **Back-end**:
  - **Framework**: Flask
  - **ORM**: SQLAlchemy
  - **Migrações**: Flask-Migrate
  - **Autenticação**: Flask-Login
  - **Tarefas Agendadas**: Flask-APScheduler
- **Front-end**:
  - **Estrutura**: HTML5, CSS3, Vanilla JS (sem jQuery)
  - **Framework CSS**: Bootstrap
  - **Componentes**: Tom Select (para selects pesquisáveis), Chart.js (para gráficos)
  - **Template Engine**: Jinja2
- **Banco de Dados**:
  - **Desenvolvimento**: SQLite
  - **Produção**: PostgreSQL

## 4. Estrutura do Projeto

O projeto segue uma arquitetura monolítica simplificada, ideal para aplicações de pequeno e médio porte.

```
gfl_sistema/
│
├── app.py                 # Arquivo principal (Rotas e lógica da aplicação)
├── models.py              # Modelos de dados (SQLAlchemy)
├── seed_db.py             # Popula o banco com dados iniciais
├── requirements.txt       # Dependências Python
├── .env                   # Variáveis de ambiente (local)
├── README.md              # Esta documentação
│
├── instance/              # Contém o banco de dados SQLite em dev
│
├── backups/               # Armazena os backups do banco
│
├── static/                # Arquivos de front-end
│   ├── css/style.css
│   └── js/main.js
│
└── templates/             # Templates HTML (Jinja2)
    ├── base.html
    └── ... (outras telas e componentes)
```

## 5. Instalação e Execução

Siga os passos abaixo para configurar e rodar o ambiente de desenvolvimento local.

### Pré-requisitos
- Python 3.8+
- Git

### Passos

1.  **Clone o repositório:**
    ```bash
    git clone <url-do-repositorio>
    cd gfl
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # Linux / macOS
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as variáveis de ambiente:**
    - Crie um arquivo chamado `.env` na raiz do projeto.
    - Copie o conteúdo do arquivo `.env.example` para o seu novo `.env`.
    - O `DATABASE_URL` para desenvolvimento com SQLite já vem pré-configurado.
    - Altere a `SECRET_KEY` para uma chave segura de sua preferência.

5.  **Execute as migrações do banco de dados:**
    ```bash
    # Aplica a migração ao banco de dados (as migrações já estão na pasta /migrations)
    flask db upgrade
    ```
    Isso criará o arquivo `gfl.db` dentro da pasta `instance/`.

6.  **Popule o banco com dados iniciais:**
    - O script `seed_db.py` cria o usuário admin, plano de contas, etc.
    ```bash
    python seed_db.py
    ```
    - O usuário padrão é configurável via `.env` (padrão: `admin@gfl.com` / `admin123`).

7.  **Execute a aplicação:**
    ```bash
    flask run
    ```
    O sistema estará acessível em `http://127.0.0.1:5000`.

## 6. Regras de Negócio e Padrões

1.  **Migrações de Banco**: Toda migração deve usar `render_as_batch=True` para suportar as limitações do SQLite em alterar tabelas.
2.  **Sanitização de Dados**: Campos de texto que são `unique` no banco (ex: CNPJ) e vêm vazios do front-end são convertidos para `None` no back-end para evitar violações de constraint.
3.  **Rateio 1:1**: A relação entre uma `ContaPagar` (NF) e um `CentroCusto` é de 1 para 1. As parcelas herdam o centro de custo da conta-mãe no momento da baixa.
4.  **Transferências Internas**: São sempre atômicas. Geram duas transações (`Despesa` na origem, `Receita` no destino) em um único commit. Falhas resultam em rollback completo.
5.  **Front-end**: Cálculos dinâmicos (como parcelamentos) são feitos em Vanilla JS. Layouts usam o grid do Bootstrap para responsividade. Listas longas usam Tom Select para UX.

## 7. Estratégia de Backup

- **Automático**: Uma tarefa agendada (via APScheduler) executa diariamente às 03:00, gerando um backup do banco de dados na pasta `/backups`.
- **Manual**: Administradores têm acesso a uma tela (`/admin/backups`) para gerar, listar e baixar backups a qualquer momento.
- **Retenção**: A política de retenção apaga backups com mais de 7 dias automaticamente.