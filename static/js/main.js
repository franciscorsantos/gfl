// static/js/main.js

/**
 * Alterna a visualização das abas na tela de Cadastros
 */
function abrirAba(evento, idAba) {
    const conteudos = document.getElementsByClassName("tab-content");
    for (let i = 0; i < conteudos.length; i++) {
        conteudos[i].style.display = "none";
    }

    const botoes = document.getElementsByClassName("tab-btn");
    for (let i = 0; i < botoes.length; i++) {
        botoes[i].className = botoes[i].className.replace(" active", "");
    }

    document.getElementById(idAba).style.display = "block";
    evento.currentTarget.className += " active";
}

/**
 * Função para abrir qualquer modal baseado no seu ID
 */
function abrirModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    } else {
        console.error(`Modal com ID ${modalId} não encontrado.`);
    }
}

/**
 * Função para fechar qualquer modal baseado no seu ID
 */
function fecharModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

// Fechar o modal ao clicar fora dele (no fundo escuro)
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal-overlay')) {
        event.target.classList.remove('show');
    }
});

/**
 * Função reutilizável para aplicar máscara de moeda a um campo
 */
function inicializarMascaraMoeda(inputElement) {
    if (!inputElement) return;

    inputElement.addEventListener('input', function(e) {
        let valor = e.target.value.replace(/\D/g, "");
        if (valor === "") {
            e.target.value = "";
            return;
        }
        valor = (parseInt(valor, 10) / 100).toFixed(2) + "";
        valor = valor.replace(".", ",");
        valor = valor.replace(/(\d)(?=(\d{3})+(?!\d))/g, "$1.");
        e.target.value = valor;
    });
}

// --- FUNÇÕES GLOBAIS DE EDIÇÃO ---

function prepararEdicao(id) {
    fetch(`/api/lancamentos/${id}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('lancamento_id').value = data.id;
            
            const titulo = document.getElementById('tituloModalLancamento');
            if(titulo) titulo.textContent = 'Editar Lançamento';

            document.querySelector(`input[name="tipo_operacao"][value="${data.tipo_operacao}"]`).checked = true;
            document.getElementById('valor').value = data.valor;
            document.getElementById('data_lancamento').value = data.data_lancamento;
            document.getElementById('portador_id').value = data.portador_id;
            document.getElementById('plano_conta_id').value = data.plano_conta_id;
            document.getElementById('centro_custo_id').value = data.centro_custo_id || "";
            document.getElementById('forma_pagto_id').value = data.forma_pagto_id;
            document.getElementById('descricao').value = data.descricao;

            document.querySelector(`input[name="status"][value="${data.status}"]`).checked = true;

            abrirModal('modalNovoLancamento');
        })
        .catch(erro => console.error('Erro ao buscar dados:', erro));
}

function prepararEdicaoPortador(id) {
    fetch(`/api/portadores/${id}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('portador_id_edit').value = data.id;
            document.querySelector('#formNovoPortador [name="nome"]').value = data.nome;
            document.querySelector('#formNovoPortador [name="tipo"]').value = data.tipo;
            document.querySelector('#formNovoPortador [name="saldo_inicial"]').value = data.saldo_inicial.replace('.', ',');
            abrirModal('modalNovoPortador');
        });
}

function prepararEdicaoPlanoConta(id) {
    fetch(`/api/planocontas/${id}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('plano_conta_id_edit').value = data.id;
            document.querySelector('#formNovoPlano [name="codigo"]').value = data.codigo;
            document.querySelector('#formNovoPlano [name="nome"]').value = data.nome;
            document.querySelector('#formNovoPlano [name="tipo"]').value = data.tipo;
            document.querySelector('#formNovoPlano [name="parent_id"]').value = data.parent_id || "";
            abrirModal('modalNovoPlano');
        });
}

function prepararEdicaoCentroCusto(id) {
    fetch(`/api/centroscusto/${id}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('centro_custo_id_edit').value = data.id;
            document.querySelector('#formNovoCentro [name="nome"]').value = data.nome;
            document.querySelector('#formNovoCentro [name="tipo"]').value = data.tipo;
            abrirModal('modalNovoCentro');
        });
}

function prepararEdicaoFormaPagamento(id) {
    fetch(`/api/formaspagamento/${id}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('forma_pagto_id_edit').value = data.id;
            document.querySelector('#formNovaForma [name="nome"]').value = data.nome;
            abrirModal('modalNovaForma');
        });
}

function prepararEdicaoFornecedor(id) {
    fetch(`/api/fornecedores/${id}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('fornecedor_id_edit').value = data.id;
            document.querySelector('#formNovoFornecedor [name="nome"]').value = data.nome;
            document.querySelector('#formNovoFornecedor [name="cnpj_cpf"]').value = data.cnpj_cpf;
            document.querySelector('#formNovoFornecedor [name="status"]').value = data.status;
            abrirModal('modalNovoFornecedor');
        });
}

function abrirModalUsuario() {
    document.getElementById('formNovoUsuario').reset();
    document.getElementById('usuario_id_edit').value = '';
    document.getElementById('tituloModalUsuario').textContent = 'Novo Usuário';
    document.getElementById('usuario_senha').required = true; // Senha é obrigatória para novos usuários
    abrirModal('modalNovoUsuario');
}

function prepararEdicaoUsuario(id) {
    fetch(`/api/usuarios/${id}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'erro') {
                alert(data.mensagem);
                return;
            }
            document.getElementById('formNovoUsuario').reset();
            document.getElementById('usuario_id_edit').value = data.id;
            document.getElementById('tituloModalUsuario').textContent = 'Editar Usuário';
            
            document.getElementById('usuario_nome').value = data.nome;
            document.getElementById('usuario_email').value = data.email;
            document.getElementById('usuario_perfil').value = data.perfil;
            document.getElementById('usuario_status').value = data.status;
            
            // Senha é opcional na edição
            document.getElementById('usuario_senha').value = ''; 
            document.getElementById('usuario_senha').required = false;

            abrirModal('modalNovoUsuario');
        })
        .catch(err => console.error('Erro ao buscar dados do usuário:', err));
}

// Aguarda o documento HTML carregar completamente
document.addEventListener('DOMContentLoaded', function() {
    
    // --- LÓGICA DO MENU MOBILE (HAMBURGER) ---
    const hamburgerBtn = document.getElementById('hamburger-btn');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (hamburgerBtn && sidebar && overlay) {
        // Abre o menu
        hamburgerBtn.addEventListener('click', function() {
            sidebar.classList.add('sidebar-open');
            overlay.classList.add('sidebar-open');
        });

        // Fecha o menu ao clicar no overlay
        overlay.addEventListener('click', function() {
            sidebar.classList.remove('sidebar-open');
            overlay.classList.remove('sidebar-open');
        });
    }

    // --- LÓGICA DE NOVO LANÇAMENTO ---
    const formNovoLancamento = document.getElementById('formNovoLancamento');
    if (formNovoLancamento) {
        formNovoLancamento.addEventListener('submit', function(evento) {
            evento.preventDefault();
            
            const formData = new FormData(formNovoLancamento);
            const dados = Object.fromEntries(formData.entries());
            
            const lancamentoId = document.getElementById('lancamento_id').value;
            const method = lancamentoId ? 'PUT' : 'POST';
            const url = lancamentoId ? `/api/lancamentos/${lancamentoId}` : '/api/lancamentos';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(resposta => resposta.json())
            .then(data => {
                if (data.status === 'sucesso') {
                    alert('Lançamento salvo com sucesso!');
                    fecharModal('modalNovoLancamento');
                    formNovoLancamento.reset();
                    window.location.reload();
                } else {
                    alert('Erro ao salvar: ' + data.mensagem);
                }
            })
            .catch(erro => {
                console.error('Erro de requisição:', erro);
                alert('Erro de conexão com o servidor.');
            });
        });
    }

    // ABRIR MODAIS DE EDIÇÃO (EVENT DELEGATION)
    document.body.addEventListener('click', function(e) {
        // Botão para editar lançamento
        const btnEditarLancamento = e.target.closest('.btn-editar-lancamento');
        if (btnEditarLancamento) {
            const id = btnEditarLancamento.getAttribute('data-id');
            prepararEdicao(id);
            return;
        }

        // Botão para editar usuário
        const btnEditarUsuario = e.target.closest('.btn-editar-usuario');
        if (btnEditarUsuario) {
            const id = btnEditarUsuario.getAttribute('data-id');
            prepararEdicaoUsuario(id);
            return;
        }
    });

    // DELETAR LANÇAMENTO
    const botoesDeletar = document.querySelectorAll('.btn-deletar-lancamento');
    botoesDeletar.forEach(botao => {
        botao.addEventListener('click', function() {
            const id = this.getAttribute('data-id');
            if (confirm("Tem certeza que deseja excluir este lançamento?")) {
                fetch(`/api/lancamentos/${id}`, { method: 'DELETE' })
                .then(resposta => resposta.json())
                .then(data => {
                    if (data.status === 'sucesso') {
                        window.location.reload(); 
                    } else {
                        alert('Erro ao excluir: ' + data.mensagem);
                    }
                })
                .catch(erro => console.error('Erro na requisição:', erro));
            }
        });
    });

    // INICIALIZAÇÃO DAS MÁSCARAS DE MOEDA
    inicializarMascaraMoeda(document.getElementById('valor')); 
    inicializarMascaraMoeda(document.getElementById('valor_total_despesa')); 
    inicializarMascaraMoeda(document.getElementById('valor_transferencia'));

    // ALTERAR STATUS DO LANÇAMENTO (Previsto/Realizado)
    const statusToggles = document.querySelectorAll('.status-toggle');
    statusToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const id = this.dataset.id;
            const statusAtual = this.dataset.statusAtual;
            const novoStatus = statusAtual === 'Previsto' ? 'Realizado' : 'Previsto';

            fetch(`/api/lancamentos/${id}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: novoStatus })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'sucesso') {
                    this.textContent = novoStatus;
                    this.dataset.statusAtual = novoStatus;
                    this.classList.toggle('status-previsto');
                    this.classList.toggle('status-realizado');
                } else {
                    alert('Erro ao atualizar status: ' + data.mensagem);
                }
            });
        });
    });

    // DELETAR ITENS DE CADASTRO GERAL
    const setupDeleteButtons = (btnClass, endpoint, entityName) => {
        const botoes = document.querySelectorAll(btnClass);
        botoes.forEach(botao => {
            botao.addEventListener('click', function() {
                const id = this.getAttribute('data-id');
                if (confirm(`Tem certeza que deseja excluir este ${entityName}? A ação não pode ser desfeita.`)) {
                    fetch(`${endpoint}/${id}`, { method: 'DELETE' })
                    .then(res => res.json())
                    .then(data => {
                        alert(data.mensagem);
                        if (data.status === 'sucesso') window.location.reload();
                    });
                }
            });
        });
    };

    setupDeleteButtons('.btn-deletar-portador', '/api/portadores', 'portador');
    setupDeleteButtons('.btn-deletar-plano-conta', '/api/planocontas', 'plano de conta');
    setupDeleteButtons('.btn-deletar-centro-custo', '/api/centroscusto', 'centro de custo');
    setupDeleteButtons('.btn-deletar-forma-pagamento', '/api/formaspagamento', 'forma de pagamento');
    setupDeleteButtons('.btn-deletar-fornecedor', '/api/fornecedores', 'fornecedor');
    setupDeleteButtons('.btn-deletar-usuario', '/api/usuarios', 'usuário');

    // LÓGICA DO MODAL DE PORTADOR
    const formNovoPortador = document.getElementById('formNovoPortador');
    if (formNovoPortador) {
        formNovoPortador.addEventListener('submit', function(evento) {
            evento.preventDefault();
            const formData = new FormData(formNovoPortador);
            const dados = Object.fromEntries(formData.entries());

            const id = document.getElementById('portador_id_edit')?.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/portadores/${id}` : '/api/portadores';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') window.location.reload();
            });
        });
    }

    // LÓGICA DO MODAL DE FORNECEDOR
    const formNovoFornecedor = document.getElementById('formNovoFornecedor');
    if(formNovoFornecedor) {
        formNovoFornecedor.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(formNovoFornecedor);
            const dados = Object.fromEntries(formData.entries());

            const id = document.getElementById('fornecedor_id_edit')?.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/fornecedores/${id}` : '/api/fornecedores';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json()).then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') window.location.reload();
            });
        });
    }

    // LÓGICA DO MODAL DE PLANO DE CONTAS
    const formNovoPlano = document.getElementById('formNovoPlano');
    if(formNovoPlano) {
        formNovoPlano.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(formNovoPlano);
            const dados = Object.fromEntries(formData.entries());

            const id = document.getElementById('plano_conta_id_edit')?.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/planocontas/${id}` : '/api/planocontas';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') window.location.reload();
            });
        });
    }

    // LÓGICA DO MODAL DE CENTRO DE CUSTO
    const formNovoCentro = document.getElementById('formNovoCentro');
    if(formNovoCentro) {
        formNovoCentro.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(formNovoCentro);
            const dados = Object.fromEntries(formData.entries());

            const id = document.getElementById('centro_custo_id_edit')?.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/centroscusto/${id}` : '/api/centroscusto';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') window.location.reload();
            });
        });
    }

    // LÓGICA DO MODAL DE FORMA DE PAGAMENTO
    const formNovaForma = document.getElementById('formNovaForma');
    if(formNovaForma) {
        formNovaForma.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(formNovaForma);
            const dados = Object.fromEntries(formData.entries());

            const id = document.getElementById('forma_pagto_id_edit')?.value;
            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/formaspagamento/${id}` : '/api/formaspagamento';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') window.location.reload();
            });
        });
    }

    // LÓGICA DO MODAL DE TRANSFERÊNCIA
    const formTransferencia = document.getElementById('formTransferencia');
    if (formTransferencia) {
        formTransferencia.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(formTransferencia);
            const dados = Object.fromEntries(formData.entries());

            fetch(formTransferencia.action, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') {
                    window.location.reload();
                }
            })
            .catch(err => {
                alert('Erro de comunicação ao tentar realizar a transferência.');
            });
        });
    }

    // MÓDULO DE CARTÕES DE CRÉDITO
    const formNovoCartao = document.getElementById('formNovoCartao');
    if (formNovoCartao) {
        formNovoCartao.addEventListener('submit', function(e) {
            e.preventDefault();
            const dados = Object.fromEntries(new FormData(formNovoCartao).entries());
            fetch('/api/cartoes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') window.location.reload();
            });
        });
    }

    const formNovaDespesaCartao = document.getElementById('formNovaDespesaCartao');
    if (formNovaDespesaCartao) {
        formNovaDespesaCartao.addEventListener('submit', function(e) {
            e.preventDefault();
            const dados = Object.fromEntries(new FormData(formNovaDespesaCartao).entries());
            fetch('/api/despesas_cartao', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') {
                    formNovaDespesaCartao.reset();
                    abrirAba({ currentTarget: document.querySelector('button[onclick*="aba-resumo"]') }, 'aba-resumo');
                    window.location.reload(); 
                }
            });
        });
    }

    const btnBuscarFatura = document.getElementById('btn-buscar-fatura');
    if (btnBuscarFatura) {
        btnBuscarFatura.addEventListener('click', function() {
            const cartaoId = document.getElementById('filtro_cartao_id').value;
            const periodo = document.getElementById('filtro_periodo').value;

            if (!cartaoId || !periodo) {
                alert('Por favor, selecione o cartão e o período da fatura.');
                return;
            }

            fetch(`/api/faturas?cartao_id=${cartaoId}&periodo=${periodo}`)
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'sucesso') {
                        const corpoTabela = document.getElementById('corpo-tabela-fatura');
                        corpoTabela.innerHTML = ''; 

                        if (data.despesas.length === 0) {
                            corpoTabela.innerHTML = `<tr class="table-empty-state"><td colspan="4">Nenhuma despesa encontrada para esta fatura.</td></tr>`;
                        } else {
                            data.despesas.forEach(d => {
                                corpoTabela.innerHTML += `
                                    <tr>
                                        <td>${d.data_compra}</td>
                                        <td>${d.descricao}</td>
                                        <td class="cell-center">${d.parcela_info}</td>
                                        <td style="text-align: right;">R$ ${d.valor_parcela}</td>
                                    </tr>`;
                            });
                        }
                        document.getElementById('total-fatura').textContent = `R$ ${data.total_fatura}`;
                        document.getElementById('resultado-fatura').style.display = 'block';

                        const btnPagar = document.getElementById('abrir-modal-pagar-fatura');
                        const statusPaga = document.getElementById('status-fatura-paga');
                        btnPagar.style.display = data.paga || data.despesas.length === 0 ? 'none' : 'flex';
                        statusPaga.style.display = data.paga ? 'flex' : 'none';
                    }
                });
        });
    }

    const abrirModalPagarFaturaBtn = document.getElementById('abrir-modal-pagar-fatura');
    if (abrirModalPagarFaturaBtn) {
        abrirModalPagarFaturaBtn.addEventListener('click', function() {
            const total = document.getElementById('total-fatura').textContent;
            document.getElementById('valor-fatura-pagamento').textContent = total;

            // Adicionado para preencher a data atual no campo de data do pagamento
            const dataPagamentoInput = document.getElementById('fatura_data_pagamento');
            if (dataPagamentoInput) {
                dataPagamentoInput.valueAsDate = new Date();
            }
            abrirModal('modalPagarFatura');
        });
    }

    const formPagarFatura = document.getElementById('formPagarFatura');
    if (formPagarFatura) {
        formPagarFatura.addEventListener('submit', function(e) {
            e.preventDefault();
            // Adicione um campo de data com id="fatura_data_pagamento" ao seu modal de pagamento
            const dados = {
                cartao_id: document.getElementById('filtro_cartao_id').value,
                periodo: document.getElementById('filtro_periodo').value,
                portador_id: document.getElementById('portador_pagamento_id').value,
                data_pagamento: document.getElementById('fatura_data_pagamento').value
            };
            fetch('/api/faturas/pagar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) })
            .then(res => res.json()).then(data => { alert(data.mensagem); if (data.status === 'sucesso') window.location.reload(); });
        });
    }

    // ===================================================================
    // MÓDULO DE CONTAS A PAGAR
    // ===================================================================
    const formNovaContaPagar = document.getElementById('formNovaContaPagar');
    if (formNovaContaPagar) {
        const condicaoPagamentoSelect = document.getElementById('condicao_pagamento');
        const camposPagamentoContainer = document.getElementById('campos_pagamento_container');
        const valorTotalInput = document.getElementById('conta_valor_total');
        let formasPagamentoOptions = '';

        const getFormasPagamentoOptions = () => {
            if (formasPagamentoOptions) return formasPagamentoOptions;
            const select = document.querySelector('#forma_pagto_id'); // Pega de um modal existente
            if (select) {
                formasPagamentoOptions = Array.from(select.options)
                    .map(opt => `<option value="${opt.value}">${opt.text}</option>`)
                    .join('');
                return formasPagamentoOptions;
            }
            return '<option value="">Carregando...</option>';
        };

        const renderCamposPagamento = () => {
            const tipo = condicaoPagamentoSelect.value;
            camposPagamentoContainer.innerHTML = '';

            let content = '';
            if (tipo === 'vista') {
                content = `
                    <div class="form-row">
                        <div class="form-group"><label>Data de Vencimento</label><input type="date" class="parcela-vencimento" required></div>
                        <div class="form-group"><label>Forma de Pagamento</label><select class="parcela-forma" required>${getFormasPagamentoOptions()}</select></div>
                    </div>`;
            } else if (tipo === 'fixo') {
                content = `
                    <div class="form-row">
                        <div class="form-group"><label>Qtd. Parcelas</label><input type="number" id="qtd_parcelas_fixo" value="2" min="2"></div>
                        <div class="form-group"><label>Data do 1º Venc.</label><input type="date" id="data_1_venc_fixo" required></div>
                        <div class="form-group"><label>Intervalo (dias)</label><input type="number" id="intervalo_dias_fixo" value="30"></div>
                        <div class="form-group"><label>Forma de Pagamento</label><select id="forma_pagto_padrao_fixo" required>${getFormasPagamentoOptions()}</select></div>
                    </div>
                    <button type="button" id="btn_gerar_parcelas_fixo" class="btn-secondary" style="margin-top: 16px;">Gerar Prévia</button>
                    <div id="preview_parcelas_container"></div>`;
            } else if (tipo === 'dinamico') {
                content = `
                    <p style="font-size: 14px; color: var(--cor-texto-suave);">Adicione cada parcela manualmente. A soma dos valores deve ser igual ao total da nota.</p>
                    <table class="data-table parcela-preview-table"><thead id="tabela_parcelas_dinamico_head"></thead><tbody id="tabela_parcelas_dinamico_body"></tbody></table>
                    <button type="button" id="btn_add_parcela_dinamico" class="btn-secondary" style="margin-top: 16px;">+ Adicionar Parcela</button>
                    <div id="preview_parcelas_container"></div>`;
            }
            camposPagamentoContainer.innerHTML = content + `
                <div class="total-parcelas-footer">
                    <span style="font-weight: 600;">Soma das Parcelas:</span>
                    <span id="soma_parcelas_display" style="font-weight: 700; font-size: 18px;">R$ 0,00</span>
                    <span id="status_soma_parcelas"></span>
                </div>`;
            if (tipo === 'vista') gerarParcelaUnica();
        };

        const gerarParcelaUnica = () => {
            const valorTotal = parseFloat(valorTotalInput.value.replace(/\./g, '').replace(',', '.')) || 0;
            document.getElementById('soma_parcelas_display').textContent = `R$ ${valorTotal.toFixed(2).replace('.', ',')}`;
            validarSomaParcelas();
        }

        const gerarParcelasFixo = () => {
            const valorTotal = parseFloat(valorTotalInput.value.replace(/\./g, '').replace(',', '.')) || 0;
            const qtd = parseInt(document.getElementById('qtd_parcelas_fixo').value);
            const data1Str = document.getElementById('data_1_venc_fixo').value;
            const intervalo = parseInt(document.getElementById('intervalo_dias_fixo').value);
            const formaID = document.getElementById('forma_pagto_padrao_fixo').value;
            const formaTexto = document.getElementById('forma_pagto_padrao_fixo').options[document.getElementById('forma_pagto_padrao_fixo').selectedIndex].text;

            if (!valorTotal || !qtd || !data1Str || !intervalo || !formaID) { alert('Preencha todos os campos para gerar as parcelas.'); return; }

            const valorParcela = (valorTotal / qtd).toFixed(2);
            let dataVenc = new Date(data1Str + 'T12:00:00');
            let tabelaHTML = `<table class="data-table parcela-preview-table"><thead><tr><th>#</th><th>Vencimento</th><th>Valor (R$)</th><th>Forma</th></tr></thead><tbody>`;
            for (let i = 1; i <= qtd; i++) {
                tabelaHTML += `<tr class="parcela-row" data-numero="${i}" data-valor="${valorParcela}" data-vencimento="${dataVenc.toISOString().split('T')[0]}" data-forma="${formaID}">
                    <td>${i}</td>
                    <td>${dataVenc.toLocaleDateString('pt-BR')}</td>
                    <td>${valorParcela.replace('.', ',')}</td>
                    <td>${formaTexto}</td>
                </tr>`;
                dataVenc.setDate(dataVenc.getDate() + intervalo);
            }
            tabelaHTML += `</tbody></table>`;
            document.getElementById('preview_parcelas_container').innerHTML = tabelaHTML;
            validarSomaParcelas();
        };

        const adicionarLinhaParcelaDinamico = () => {
            const tbody = document.getElementById('tabela_parcelas_dinamico_body');
            if (tbody.children.length === 0) {
                document.getElementById('tabela_parcelas_dinamico_head').innerHTML = `<tr><th>Vencimento</th><th>Valor (R$)</th><th>Forma de Pagamento</th><th class="cell-center">Ação</th></tr>`;
            }
            const numero = tbody.children.length + 1;
            const newRow = document.createElement('tr');
            newRow.className = 'parcela-row';
            newRow.dataset.numero = numero;
            newRow.innerHTML = `
                <td><input type="date" class="parcela-vencimento" required></td>
                <td><input type="text" class="parcela-valor-input input-moeda" placeholder="0,00" required></td>
                <td><select class="parcela-forma" required>${getFormasPagamentoOptions()}</select></td>
                <td class="cell-center"><button type="button" class="action-icon btn-remover-parcela" title="Remover"><span class="material-symbols-outlined" style="color: var(--cor-perigo);">delete</span></button></td>
            `;
            tbody.appendChild(newRow);
            inicializarMascaraMoeda(newRow.querySelector('.input-moeda'));
        };

        const validarSomaParcelas = () => {
            const valorTotal = parseFloat(valorTotalInput.value.replace(/\./g, '').replace(',', '.')) || 0;
            let somaParcelas = 0;
            const tipo = condicaoPagamentoSelect.value;

            if (tipo === 'vista') {
                somaParcelas = valorTotal;
            } else if (tipo === 'fixo') {
                const qtd = parseInt(document.getElementById('qtd_parcelas_fixo').value) || 0;
                const valorParcela = parseFloat((valorTotal / qtd).toFixed(2)) || 0;
                somaParcelas = valorParcela * qtd;
            } else if (tipo === 'dinamico') {
                document.querySelectorAll('#tabela_parcelas_dinamico_body .parcela-valor-input').forEach(input => {
                    somaParcelas += parseFloat(input.value.replace(/\./g, '').replace(',', '.')) || 0;
                });
            }

            document.getElementById('soma_parcelas_display').textContent = `R$ ${somaParcelas.toFixed(2).replace('.', ',')}`;
            const statusEl = document.getElementById('status_soma_parcelas');
            const diferenca = Math.abs(valorTotal - somaParcelas);

            if (diferenca < 0.015) { // Tolerância para arredondamento
                statusEl.innerHTML = `<span class="total-ok">(Total OK)</span>`;
                return true;
            } else {
                statusEl.innerHTML = `<span class="total-erro">(Diferença de R$ ${diferenca.toFixed(2).replace('.', ',')})</span>`;
                return false;
            }
        };

        condicaoPagamentoSelect.addEventListener('change', renderCamposPagamento);
        valorTotalInput.addEventListener('input', () => {
            if (condicaoPagamentoSelect.value === 'vista') gerarParcelaUnica();
            else validarSomaParcelas();
        });

        camposPagamentoContainer.addEventListener('click', e => {
            if (e.target.id === 'btn_gerar_parcelas_fixo') gerarParcelasFixo();
            if (e.target.id === 'btn_add_parcela_dinamico') adicionarLinhaParcelaDinamico();
            if (e.target.closest('.btn-remover-parcela')) {
                e.target.closest('tr').remove();
                validarSomaParcelas();
            }
        });

        camposPagamentoContainer.addEventListener('input', e => {
            if (e.target.classList.contains('parcela-valor-input') || e.target.classList.contains('parcela-vencimento')) {
                validarSomaParcelas();
            }
        });

        formNovaContaPagar.addEventListener('submit', e => {
            e.preventDefault();
            if (!validarSomaParcelas()) {
                alert('A soma das parcelas não confere com o valor total da nota. Por favor, ajuste os valores.');
                return;
            }

            const formData = new FormData(formNovaContaPagar);
            const dados = Object.fromEntries(formData.entries());
            dados.parcelas = [];
            const tipo = condicaoPagamentoSelect.value;

            if (tipo === 'vista') {
                dados.parcelas.push({
                    numero_parcela: 1,
                    valor_parcela: dados.valor_total,
                    data_vencimento: document.querySelector('#campos_pagamento_container .parcela-vencimento').value,
                    forma_pagto_id: document.querySelector('#campos_pagamento_container .parcela-forma').value
                });
            } else {
                document.querySelectorAll('#campos_pagamento_container .parcela-row').forEach(row => {
                    let parcela = { numero_parcela: row.dataset.numero };
                    if (tipo === 'fixo') {
                        parcela.valor_parcela = row.dataset.valor.replace('.', ',');
                        parcela.data_vencimento = row.dataset.vencimento;
                        parcela.forma_pagto_id = row.dataset.forma;
                    } else { // dinâmico
                        parcela.valor_parcela = row.querySelector('.parcela-valor-input').value;
                        parcela.data_vencimento = row.querySelector('.parcela-vencimento').value;
                        parcela.forma_pagto_id = row.querySelector('.parcela-forma').value;
                    }
                    dados.parcelas.push(parcela);
                });
            }

            fetch('/api/contas_pagar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') {
                    formNovaContaPagar.reset();
                    renderCamposPagamento();
                }
            }).catch(err => alert('Erro de comunicação com o servidor.'));
        });

        renderCamposPagamento();
        inicializarMascaraMoeda(valorTotalInput);
    }

    // ===================================================================
    // MÓDULO DE GESTÃO DE USUÁRIOS
    // ===================================================================
    const formNovoUsuario = document.getElementById('formNovoUsuario');
    if (formNovoUsuario) {
        formNovoUsuario.addEventListener('submit', function(e) {
            e.preventDefault();
            const id = document.getElementById('usuario_id_edit').value;
            const dados = Object.fromEntries(new FormData(formNovoUsuario).entries());
            
            delete dados.usuario_id;

            if (id && !dados.senha) {
                delete dados.senha;
            }

            const method = id ? 'PUT' : 'POST';
            const url = id ? `/api/usuarios/${id}` : '/api/usuarios';

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            })
            .then(res => res.json())
            .then(data => {
                alert(data.mensagem);
                if (data.status === 'sucesso') {
                    window.location.reload();
                }
            })
            .catch(err => {
                console.error('Erro ao salvar usuário:', err);
                alert('Erro de comunicação com o servidor.');
            });
        });
    }

    // ===================================================================
    // GESTÃO DE CONTAS A PAGAR
    // ===================================================================
    const tabelaContasPagar = document.querySelector('.data-table-container');
    if (tabelaContasPagar) {

        // Lógica para expandir/recolher as parcelas
        tabelaContasPagar.addEventListener('click', function(e) {
            const principalRow = e.target.closest('.conta-principal-row');
            if (principalRow) {
                const targetId = principalRow.dataset.targetDetails;
                const detalhesRow = document.getElementById(targetId);
                if (detalhesRow) {
                    principalRow.classList.toggle('expanded');
                    detalhesRow.style.display = detalhesRow.style.display === 'table-row' ? 'none' : 'table-row';
                }
            }
        });

        // Lógica para abrir o modal de pagamento
        tabelaContasPagar.addEventListener('click', function(e) {
            const pagarBtn = e.target.closest('.btn-pagar-parcela');
            if (pagarBtn) {
                const id = pagarBtn.dataset.parcelaId;
                const valor = pagarBtn.dataset.parcelaValor;
                const desc = pagarBtn.dataset.parcelaDesc;

                document.getElementById('pagar_parcela_id').value = id;
                document.getElementById('pagar_parcela_valor').textContent = valor;
                document.getElementById('pagar_parcela_descricao').textContent = desc;
                
                // Preenche a data de hoje como padrão
                document.getElementById('pagar_data_pagamento').valueAsDate = new Date();

                abrirModal('modalPagarParcela');
            }
        });

        // Lógica para submeter o pagamento da parcela
        const formPagarParcela = document.getElementById('formPagarParcela');
        if (formPagarParcela) {
            formPagarParcela.addEventListener('submit', function(e) {
                e.preventDefault();
                const parcelaId = document.getElementById('pagar_parcela_id').value;
                const dados = {
                    portador_id: document.getElementById('pagar_portador_id').value,
                    data_pagamento: document.getElementById('pagar_data_pagamento').value
                };

                if (!dados.portador_id || !dados.data_pagamento) {
                    alert('Por favor, selecione a conta e a data do pagamento.');
                    return;
                }

                fetch(`/api/parcelas/pagar/${parcelaId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(dados)
                })
                .then(res => res.json())
                .then(data => {
                    alert(data.mensagem);
                    if (data.status === 'sucesso') {
                        window.location.reload();
                    }
                })
                .catch(err => {
                    console.error('Erro ao pagar parcela:', err);
                    alert('Ocorreu um erro de comunicação com o servidor.');
                });
            });
        }
    }

    // ===================================================================
    // CENTRAL DE EXTRATOS
    // ===================================================================
    const btnExportarCsv = document.getElementById('btn-exportar-csv');
    if (btnExportarCsv) {
        btnExportarCsv.addEventListener('click', function(e) {
            e.preventDefault();
            const form = document.getElementById('form-extrato');
            if (form) {
                const params = new URLSearchParams(new FormData(form)).toString();
                window.location.href = `/extrato/exportar_csv?${params}`;
            }
        });
    }
});