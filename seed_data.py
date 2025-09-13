import os
import django
import random
from datetime import date, timedelta
from decimal import Decimal

# --- CONFIGURAÇÃO DO AMBIENTE DJANGO ---
# Garante que o script possa usar os modelos do seu projeto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
print("✅ Configurando o ambiente Django...")
django.setup()
print("✅ Ambiente configurado.")

# --- IMPORTAÇÃO DOS MODELOS ---
# Importa os modelos APÓS a configuração do ambiente
from finances.models import Receita, Despesa, Category
from core.models import UnidadeNegocio
from scheduler.models import Aluno, CustomUser

# ==============================================================================
# ⚠️ CONFIGURE O ID DA SUA UNIDADE DE NEGÓCIO AQUI ⚠️
# ==============================================================================
UNIDADE_NEGOCIO_ID = 1
# ==============================================================================

# --- PARÂMETROS DE GERAÇÃO DE DADOS ---
NUMERO_DE_MESES = 4  # Gerar dados para os últimos 4 meses
RECEITAS_POR_MES = random.randint(25, 40)
DESPESAS_POR_MES = random.randint(15, 25)

def run_seed():
    """Função principal que executa a geração de dados."""

    # --- 1. BUSCAR A UNIDADE DE NEGÓCIO ---
    try:
        unidade = UnidadeNegocio.objects.get(pk=UNIDADE_NEGOCIO_ID)
        print(f"\n🏢 Unidade de Negócio encontrada: '{unidade.nome}'")
    except UnidadeNegocio.DoesNotExist:
        print(f"❌ ERRO: Unidade de Negócio com ID {UNIDADE_NEGOCIO_ID} não encontrada. Verifique o ID e tente novamente.")
        return

    # --- 2. LIMPAR DADOS FINANCEIROS ANTERIORES (DA UNIDADE SELECIONADA) ---
    print("\n🧹 Limpando dados financeiros antigos (Receitas e Despesas)...")
    Receita.objects.filter(unidade_negocio=unidade).delete()
    Despesa.objects.filter(unidade_negocio=unidade).delete()
    Category.objects.filter(unidade_negocio=unidade).delete()
    print("✅ Dados antigos removidos.")

    # --- 3. CRIAR CATEGORIAS ESSENCIAIS ---
    print("\n🏷️  Criando categorias financeiras...")
    categorias_para_criar = {
        'income': [
            'Mensalidades Alunos', 'Venda de Produtos', 'Aulas Avulsas', 'Eventos e Workshops'
        ],
        'expense': {
            'custo': ['Pagamento de Professores', 'Compra de Mercadoria para Revenda', 'Material Didático'],
            'despesa': ['Aluguel do Espaço', 'Contas de Consumo (Água, Luz, Internet)', 'Marketing e Publicidade', 'Software e Assinaturas', 'Manutenção e Limpeza']
        }
    }

    categorias_receita = []
    for nome in categorias_para_criar['income']:
        cat, _ = Category.objects.get_or_create(
            unidade_negocio=unidade, name=nome, type='income',
            defaults={'tipo_dre': 'despesa'} # tipo_dre é irrelevante para income
        )
        categorias_receita.append(cat)

    categorias_custo = []
    for nome in categorias_para_criar['expense']['custo']:
        cat, _ = Category.objects.get_or_create(
            unidade_negocio=unidade, name=nome, type='expense',
            defaults={'tipo_dre': 'custo'}
        )
        categorias_custo.append(cat)
    
    categorias_despesa = []
    for nome in categorias_para_criar['expense']['despesa']:
        cat, _ = Category.objects.get_or_create(
            unidade_negocio=unidade, name=nome, type='expense',
            defaults={'tipo_dre': 'despesa'}
        )
        categorias_despesa.append(cat)
        
    print(f"✅ {len(categorias_receita) + len(categorias_custo) + len(categorias_despesa)} categorias criadas.")

    # --- 4. VERIFICAR PRÉ-REQUISITOS (ALUNOS E PROFESSORES) ---
    print("\n👥 Verificando se existem alunos e professores cadastrados...")
    alunos = list(Aluno.objects.filter(status='ativo'))
    professores = list(CustomUser.objects.filter(tipo__in=['professor', 'admin']))

    if not alunos:
        print("❌ ERRO: Nenhum aluno ativo encontrado. Cadastre pelo menos um aluno antes de executar o script.")
        return
    print(f"✅ Encontrados {len(alunos)} alunos ativos.")
    print(f"✅ Encontrados {len(professores)} professores/admins.")

    # --- 5. GERAR DADOS MÊS A MÊS ---
    today = date.today()
    for i in range(NUMERO_DE_MESES):
        # Calcula o primeiro dia do mês corrente do loop
        target_month_date = today.replace(day=1) - timedelta(days=i*30)
        mes_ano = target_month_date.strftime("%B/%Y")
        print(f"\n🔄 Gerando dados para o mês de {mes_ano}...")
        
        # --- GERAR RECEITAS ---
        for _ in range(RECEITAS_POR_MES):
            aluno = random.choice(alunos)
            categoria = random.choice(categorias_receita)
            data_competencia = target_month_date.replace(day=random.randint(1, 28))
            
            if 'Mensalidades' in categoria.name:
                valor = Decimal(random.uniform(150, 450)).quantize(Decimal('0.01'))
                descricao = f"Mensalidade {aluno.nome_completo.split()[0]}"
            else:
                valor = Decimal(random.uniform(50, 200)).quantize(Decimal('0.01'))
                descricao = f"{categoria.name} - {aluno.nome_completo.split()[0]}"
            
            is_recebido = random.random() > 0.2 # 80% de chance de estar recebido
            
            Receita.objects.create(
                unidade_negocio=unidade,
                descricao=descricao,
                valor=valor,
                categoria=categoria,
                aluno=aluno,
                data_competencia=data_competencia,
                status='recebido' if is_recebido else 'a_receber',
                data_recebimento=data_competencia + timedelta(days=random.randint(0, 5)) if is_recebido else None
            )
            
        # --- GERAR DESPESAS ---
        categorias_despesas_todas = categorias_custo + categorias_despesa
        for _ in range(DESPESAS_POR_MES):
            categoria = random.choice(categorias_despesas_todas)
            data_competencia = target_month_date.replace(day=random.randint(1, 28))
            professor = random.choice(professores) if professores and 'Professores' in categoria.name else None

            if 'Aluguel' in categoria.name:
                valor = Decimal(random.uniform(2000, 3500)).quantize(Decimal('0.01'))
            elif 'Professores' in categoria.name:
                valor = Decimal(random.uniform(500, 1500)).quantize(Decimal('0.01'))
            else:
                valor = Decimal(random.uniform(100, 800)).quantize(Decimal('0.01'))

            is_pago = random.random() > 0.1 # 90% de chance de estar pago
            
            Despesa.objects.create(
                unidade_negocio=unidade,
                descricao=categoria.name,
                valor=valor,
                categoria=categoria,
                professor=professor,
                data_competencia=data_competencia,
                status='pago' if is_pago else 'a_pagar',
                data_pagamento=data_competencia + timedelta(days=random.randint(0, 5)) if is_pago else None
            )
        print(f"✅ Dados de {mes_ano} gerados.")

    print("\n\n🎉 Processo concluído! Seus dados financeiros fictícios foram criados com sucesso.")
    print("🚀 Agora você pode acessar a página do DRE para visualizar os resultados.")


if __name__ == '__main__':
    run_seed()