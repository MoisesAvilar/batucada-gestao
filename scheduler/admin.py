from django.contrib import admin
from .models import (
    Aula, Aluno, Modalidade, CustomUser, 
    RelatorioAula, ItemRudimento, ItemRitmo, ItemVirada
)


@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    # Adicionamos 'cpf' e 'responsavel_nome' à lista
    list_display = ('status', 'nome_completo', 'email', 'cpf', 'responsavel_nome', 'valor_mensalidade', 'dia_vencimento')
    search_fields = ('nome_completo', 'email', 'cpf', 'responsavel_nome')
    ordering = ('nome_completo',)

    fieldsets = (
        ('Informações Pessoais', {
            # Adicionamos os novos campos aqui
            'fields': ('status', 'nome_completo', 'email', 'telefone', 'cpf', 'responsavel_nome', 'data_criacao')
        }),
        ('Detalhes Financeiros (Mensalistas)', {
            'classes': ('collapse',),
            'fields': ('valor_mensalidade', 'dia_vencimento'),
            'description': "Preencha estes campos apenas para alunos com pagamento mensal recorrente."
        }),
    )


@admin.register(Modalidade)
class ModalidadeAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

class ItemRudimentoInline(admin.TabularInline):
    model = ItemRudimento
    extra = 1

class ItemRitmoInline(admin.TabularInline):
    model = ItemRitmo
    extra = 1

class ItemViradaInline(admin.TabularInline):
    model = ItemVirada
    extra = 1

@admin.register(RelatorioAula)
class RelatorioAulaAdmin(admin.ModelAdmin):
    list_display = ('aula', 'professor_que_validou', 'data_atualizacao')
    autocomplete_fields = ('aula', 'professor_que_validou')
    inlines = [ItemRudimentoInline, ItemRitmoInline, ItemViradaInline]

@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    """
    Configuração da área de admin para o modelo Aula, agora atualizada
    para os campos ManyToMany `alunos` e `professores`.
    """
    # --- ATUALIZADO ---
    # `list_display` agora usa métodos customizados para exibir os nomes.
    list_display = ('data_hora', 'get_alunos_display', 'modalidade', 'get_professores_display', 'status')
    
    # Filtros atualizados para os novos campos.
    list_filter = ('status', 'modalidade', 'professores', 'data_hora')
    
    # Campos de busca atualizados.
    search_fields = ('alunos__nome_completo', 'professores__username', 'modalidade__nome')
    
    # Campos de autocompletar atualizados.
    autocomplete_fields = ('alunos', 'professores')
    
    ordering = ('-data_hora',)
    
    # O Django não exibe campos ManyToMany diretamente em `list_display`.
    # Criamos métodos para formatar a saída como uma lista de nomes.
    def get_alunos_display(self, obj):
        """Retorna uma string com os nomes dos alunos separados por vírgula."""
        return ", ".join([aluno.nome_completo for aluno in obj.alunos.all()])
    get_alunos_display.short_description = 'Alunos'  # Define o título da coluna

    def get_professores_display(self, obj):
        """Retorna uma string com os nomes dos professores separados por vírgula."""
        return ", ".join([prof.username for prof in obj.professores.all()])
    get_professores_display.short_description = 'Professores' # Define o título da coluna


# Você pode registrar o CustomUser aqui para gerenciá-lo no admin
# se ainda não estiver sendo gerenciado por outro app.
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'tipo', 'is_staff')
    list_filter = ('tipo', 'is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
