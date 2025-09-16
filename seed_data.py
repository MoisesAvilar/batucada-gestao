import os
import django
import random
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

# --- CONFIGURAÇÃO DO AMBIENTE DJANGO ---
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
print("✅ Configurando o ambiente Django...")
django.setup()
print("✅ Ambiente configurado.")

# --- IMPORTAÇÃO DOS MODELOS ---
from finances.models import (
    Receita, Despesa, Category, Transaction, 
    ReceitaRecorrente, DespesaRecorrente
)
from core.models import UnidadeNegocio
from scheduler.models import Aluno, CustomUser
from store.models import Produto, CategoriaProduto

# ==============================================================================
# ⚠️ CONFIGURE O ID DA SUA UNIDADE DE NEGÓCIO AQUI ⚠️
# ==============================================================================
UNIDADE_NEGOCIO_ID = 1
# ==============================================================================

# --- PARÂMETROS DE GERAÇÃO DE DADOS ---
NUMERO_DE_MESES = 4
DESPESAS_POR_MES = random.randint(10, 20)
VENDAS_POR_MES = random.randint(10, 20) 
NUMERO_DE_PRODUTOS = 15

def run_seed():
    """Função principal que executa a geração de dados."""

    # --- 1. BUSCAR A UNIDADE DE NEGÓCIO ---
    try:
        unidade = UnidadeNegocio.objects.get(pk=UNIDADE_NEGOCIO_ID)
        print(f"\n🏢 Unidade de Negócio encontrada: '{unidade.nome}'")
    except UnidadeNegocio.DoesNotExist:
        print(f"❌ ERRO: Unidade de Negócio com ID {UNIDADE_NEGOCIO_ID} não encontrada.")
        return

    # --- 2. LIMPAR DADOS ANTERIORES ---
    print("\n🧹 Limpando dados antigos...")
    ReceitaRecorrente.objects.filter(unidade_negocio=unidade).delete()
    DespesaRecorrente.objects.filter(unidade_negocio=unidade).delete()
    Receita.objects.filter(unidade_negocio=unidade).delete()
    Despesa.objects.filter(unidade_negocio=unidade).delete()
    Transaction.objects.filter(unidade_negocio=unidade).delete()
    Produto.objects.filter(unidade_negocio=unidade).delete()
    CategoriaProduto.objects.filter(unidade_negocio=unidade).delete()
    Category.objects.filter(unidade_negocio=unidade).delete()
    print("✅ Dados antigos (Recorrências, Finanças, Produtos, Categorias) removidos.")

    # --- 3. CRIAR CATEGORIAS ---
    print("\n🏷️  Criando categorias...")
    categorias_para_criar = {
        'income': ['Mensalidades Alunos', 'Venda de Produtos', 'Aulas Avulsas', 'Parcerias'],
        'expense': {
            'custo': ['Pagamento de Professores', 'Compra de Mercadoria para Revenda'],
            'despesa': ['Aluguel', 'Contas de Consumo', 'Marketing', 'Software']
        }
    }
    categorias_receita = {nome: Category.objects.create(unidade_negocio=unidade, name=nome, type='income') for nome in categorias_para_criar['income']}
    categorias_custo = {nome: Category.objects.create(unidade_negocio=unidade, name=nome, type='expense', tipo_dre='custo') for nome in categorias_para_criar['expense']['custo']}
    categorias_despesa = {nome: Category.objects.create(unidade_negocio=unidade, name=nome, type='expense', tipo_dre='despesa') for nome in categorias_para_criar['expense']['despesa']}
    cat_venda_produto = categorias_receita['Venda de Produtos']
    nomes_cat_produto = ["Sapatilhas e Vestuário", "Acessórios", "Alimentação e Bebidas"]
    categorias_produto = [CategoriaProduto.objects.create(unidade_negocio=unidade, nome=nome) for nome in nomes_cat_produto]
    print(f"✅ Categorias criadas.")

    # --- 4. VERIFICAR E ATUALIZAR ALUNOS ---
    print("\n👥 Verificando se existem alunos e professores cadastrados...")
    alunos_qs = Aluno.objects.filter(status='ativo')
    professores = list(CustomUser.objects.filter(tipo__in=['professor', 'admin']))
    
    if not alunos_qs.exists():
        print("❌ ERRO: Nenhum aluno ativo encontrado.")
        return

    # <--- INÍCIO DA NOVA SEÇÃO ---
    # Garante que todos os alunos ativos tenham valor de mensalidade e dia de vencimento
    print("🔧 Verificando e preenchendo dados de mensalidade dos alunos...")
    alunos_atualizados = 0
    dias_vencimento_comuns = [5, 10, 15, 20, 25]
    for aluno in alunos_qs:
        precisa_salvar = False
        if not aluno.valor_mensalidade or aluno.valor_mensalidade <= 0:
            aluno.valor_mensalidade = Decimal(random.uniform(180, 450)).quantize(Decimal('0.01'))
            precisa_salvar = True
        
        if not aluno.dia_vencimento:
            aluno.dia_vencimento = random.choice(dias_vencimento_comuns)
            precisa_salvar = True

        # --- LINHA ADICIONADA PARA CORRIGIR O ERRO ---
        if not aluno.data_criacao:
            aluno.data_criacao = timezone.now().date() # Define a data de hoje se estiver faltando
            precisa_salvar = True
        # --- FIM DA ADIÇÃO ---

        if precisa_salvar:
            aluno.save()
    
    if alunos_atualizados > 0:
        print(f"✅ {alunos_atualizados} alunos tiveram dados de mensalidade/vencimento preenchidos.")
    else:
        print("✅ Todos os alunos ativos já possuem dados de mensalidade.")
    # <--- FIM DA NOVA SEÇÃO ---
    
    alunos = list(alunos_qs) # Converte para lista para uso posterior
    print(f"✅ Encontrados {len(alunos)} alunos ativos e {len(professores)} professores/admins.")

    # --- 5. CRIAR LANÇAMENTOS RECORRENTES ---
    print("\n🔄 Criando regras de lançamentos recorrentes...")
    data_inicio_recorrencia = date.today().replace(day=1) - timedelta(days=365)
    # (O restante da lógica de criação de recorrências permanece a mesma)
    DespesaRecorrente.objects.create(unidade_negocio=unidade, descricao="Aluguel do Espaço", valor=Decimal('2500.00'), categoria=categorias_despesa['Aluguel'], dia_do_mes=5, ativa=True, data_inicio=data_inicio_recorrencia)
    DespesaRecorrente.objects.create(unidade_negocio=unidade, descricao="Assinatura Software de Gestão", valor=Decimal('150.00'), categoria=categorias_despesa['Software'], dia_do_mes=10, ativa=True, data_inicio=data_inicio_recorrencia)
    DespesaRecorrente.objects.create(unidade_negocio=unidade, descricao="Plano de Internet", valor=Decimal('120.00'), categoria=categorias_despesa['Contas de Consumo'], dia_do_mes=15, ativa=True, data_inicio=data_inicio_recorrencia)
    print("✅ 3 regras de despesas recorrentes criadas.")
    alunos_mensalistas = random.sample(alunos, int(len(alunos) * 0.8))
    for aluno in alunos_mensalistas:
        ReceitaRecorrente.objects.create(unidade_negocio=unidade, descricao=f"Mensalidade de {aluno.nome_completo}", aluno=aluno, categoria=categorias_receita['Mensalidades Alunos'], ativa=True, data_inicio=data_inicio_recorrencia)
    print(f"✅ {len(alunos_mensalistas)} regras de mensalidades recorrentes para alunos criadas.")
    ReceitaRecorrente.objects.create(unidade_negocio=unidade, descricao="Parceria Academia Corpo & Mente", valor=Decimal('500.00'), categoria=categorias_receita['Parcerias'], dia_do_mes=20, ativa=True, data_inicio=data_inicio_recorrencia)
    print("✅ 1 regra de receita recorrente fixa criada.")

    # --- 6. CRIAR PRODUTOS ---
    print("\n🛍️  Criando produtos...")
    # (A lógica de criação de produtos permanece a mesma)
    nomes_produtos = ["Sapatilha", "Collant Preto", "Meia-calça", "Garrafa de Água", "Toalha Fitness", "Barra de Cereal"]
    produtos_criados = []
    for i in range(NUMERO_DE_PRODUTOS):
        custo = Decimal(random.uniform(10, 150)).quantize(Decimal('0.01'))
        produto = Produto.objects.create(
            unidade_negocio=unidade,
            nome=f"{random.choice(nomes_produtos)} {random.choice(['Premium', 'Básico', 'Flex'])}",
            categoria=random.choice(categorias_produto),
            custo_de_aquisicao=custo,
            percentual_markup=Decimal(random.uniform(40, 80)).quantize(Decimal('0.01')),
            quantidade_em_estoque=random.randint(10, 50)
        )
        produtos_criados.append(produto)
    print(f"✅ {len(produtos_criados)} produtos criados.")

    # --- 7. GERAR DADOS VARIÁVEIS MÊS A MÊS ---
    today = date.today()
    for i in range(NUMERO_DE_MESES):
        target_month_date = today.replace(day=1) - timedelta(days=i*30)
        mes_ano = target_month_date.strftime("%B/%Y")
        print(f"\n🔄 Gerando dados VARIÁVEIS para o mês de {mes_ano}...")
        
        # (A lógica de vendas e despesas variáveis permanece a mesma)
        for _ in range(VENDAS_POR_MES):
            aluno = random.choice(alunos)
            produto = random.choice([p for p in produtos_criados if p.quantidade_em_estoque > 0])
            quantidade = random.randint(1, 2)
            if produto.quantidade_em_estoque < quantidade: continue
            valor_total = produto.preco_de_venda_calculado * quantidade
            data_venda = target_month_date.replace(day=random.randint(1, 28))
            descricao_venda = f"Venda de {quantidade}x {produto.nome}"
            transacao = Transaction.objects.create(
                unidade_negocio=unidade, description=descricao_venda, amount=valor_total,
                category=cat_venda_produto, transaction_date=data_venda, student=aluno
            )
            Receita.objects.create(
                unidade_negocio=unidade, descricao=descricao_venda, valor=valor_total,
                categoria=cat_venda_produto, aluno=aluno, data_competencia=data_venda,
                produto=produto, quantidade=quantidade, status='recebido',
                data_recebimento=data_venda, transacao=transacao
            )
            produto.quantidade_em_estoque -= quantidade
            produto.save()
            
        todas_categorias_despesa = list(categorias_custo.values()) + list(categorias_despesa.values())
        for _ in range(DESPESAS_POR_MES):
            categoria = random.choice(todas_categorias_despesa)
            professor = random.choice(professores) if 'Pagamento' in categoria.name and professores else None
            data_competencia = target_month_date.replace(day=random.randint(1, 28))
            valor = Decimal(random.uniform(50, 500)).quantize(Decimal('0.01'))
            despesa = Despesa(
                unidade_negocio=unidade, descricao=f"Compra Avulsa: {categoria.name}", valor=valor, categoria=categoria,
                professor=professor, data_competencia=data_competencia
            )
            if random.random() > 0.1:
                despesa.status = 'pago'
                despesa.data_pagamento = data_competencia + timedelta(days=random.randint(0, 5))
                transacao = Transaction.objects.create(
                    unidade_negocio=unidade, description=despesa.descricao, amount=despesa.valor,
                    category=despesa.categoria, transaction_date=despesa.data_pagamento, professor=professor
                )
                despesa.transacao = transacao
            despesa.save()

        print(f"✅ Dados variáveis de {mes_ano} gerados.")

    print("\n\n🎉 Processo concluído! Regras de recorrência e dados variáveis foram criados.")
    print("🚀 Agora execute 'python manage.py gerar_lancamentos_recorrentes' para criar as mensalidades e despesas fixas.")

if __name__ == '__main__':
    run_seed()