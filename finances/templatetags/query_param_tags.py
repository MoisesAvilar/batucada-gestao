from django import template
from urllib.parse import urlencode

register = template.Library()

@register.filter(name='dict_minus')
def dict_minus(query_dict, key_to_remove):
    """
    Recebe um QueryDict (como request.GET) e uma chave.
    Retorna uma string de URL com todos os outros parâmetros, exceto a chave especificada.
    Isso é útil para construir links de ordenação que mantêm os filtros existentes.
    """
    # Cria uma cópia mutável do dicionário de parâmetros
    params = query_dict.copy()
    
    # Remove a chave (se ela existir)
    if key_to_remove in params:
        del params[key_to_remove]
        
    # Retorna os parâmetros restantes codificados para URL
    return params.urlencode()