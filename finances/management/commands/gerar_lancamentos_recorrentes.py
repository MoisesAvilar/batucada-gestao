from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from finances.models import Despesa, DespesaRecorrente, Receita, ReceitaRecorrente

class Command(BaseCommand):
    help = 'Gera os lançamentos de despesas e receitas recorrentes que vencem hoje ou nos próximos 5 dias.'

    def handle(self, *args, **kwargs):
        hoje = timezone.now().date()
        
        # --- INÍCIO DA NOVA LÓGICA DE ANTECIPAÇÃO ---
        dias_antecedencia = 5
        dias_a_verificar = []
        # Criamos uma lista com os números dos dias que queremos verificar (hoje + 5 dias)
        for i in range(dias_antecedencia + 1):
            data_futura = hoje + timedelta(days=i)
            dias_a_verificar.append(data_futura.day)
        
        # Removemos duplicados caso o período passe pelo fim do mês (ex: [29, 30, 31, 1, 2])
        dias_a_verificar = sorted(list(set(dias_a_verificar)))

        self.stdout.write(f"Iniciando verificação de lançamentos recorrentes para os dias: {dias_a_verificar}...")
        # --- FIM DA NOVA LÓGICA DE ANTECIPAÇÃO ---

        # --- Gera Despesas Recorrentes ---
        # A busca agora usa a lista de dias a verificar
        despesas_a_lancar = DespesaRecorrente.objects.filter(
            ativa=True,
            dia_do_mes__in=dias_a_verificar,
            data_inicio__lte=hoje
        )

        for recorrente in despesas_a_lancar:
            # Define a data de competência correta para este mês
            data_competencia_despesa = hoje.replace(day=recorrente.dia_do_mes)

            if (recorrente.data_fim and data_competencia_despesa > recorrente.data_fim):
                continue

            ja_existe = Despesa.objects.filter(
                descricao=recorrente.descricao,
                data_competencia__year=data_competencia_despesa.year,
                data_competencia__month=data_competencia_despesa.month,
                unidade_negocio=recorrente.unidade_negocio
            ).exists()

            if not ja_existe:
                Despesa.objects.create(
                    unidade_negocio=recorrente.unidade_negocio,
                    descricao=recorrente.descricao,
                    valor=recorrente.valor,
                    categoria=recorrente.categoria,
                    data_competencia=data_competencia_despesa, # <-- Usa a data de competência correta
                    professor=recorrente.professor
                )
                self.stdout.write(self.style.SUCCESS(f"Despesa '{recorrente.descricao}' criada para competência de {data_competencia_despesa.strftime('%B/%Y')}."))

        # --- Gera Receitas Recorrentes (com a mesma lógica) ---
        receitas_a_lancar = ReceitaRecorrente.objects.filter(
            ativa=True,
            aluno__status='ativo',
            data_inicio__lte=hoje
        ).exclude(aluno__dia_vencimento__isnull=True) # Ignora alunos sem dia de vencimento

        for recorrente in receitas_a_lancar:
            aluno = recorrente.aluno
            
            if aluno.dia_vencimento not in dias_a_verificar:
                continue

            data_competencia_receita = hoje.replace(day=aluno.dia_vencimento)
            
            if (recorrente.data_fim and data_competencia_receita > recorrente.data_fim):
                continue
            
            ja_existe = Receita.objects.filter(
                aluno=aluno,
                data_competencia__year=data_competencia_receita.year,
                data_competencia__month=data_competencia_receita.month,
                categoria=recorrente.categoria
            ).exists()

            if not ja_existe:
                Receita.objects.create(
                    unidade_negocio=recorrente.unidade_negocio,
                    descricao=f"Mensalidade {data_competencia_receita.strftime('%B/%Y')} - {aluno.nome_completo}",
                    valor=aluno.valor_mensalidade,
                    categoria=recorrente.categoria,
                    data_competencia=data_competencia_receita, # <-- Usa a data de competência correta
                    aluno=aluno
                )
                self.stdout.write(self.style.SUCCESS(f"Receita para '{aluno.nome_completo}' criada para competência de {data_competencia_receita.strftime('%B/%Y')}."))
        
        self.stdout.write("Verificação concluída.")