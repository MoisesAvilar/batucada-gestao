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


@register.filter(name='smart_title')
def smart_title(value):
    """
    Capitaliza o texto como o filtro 'title', mas mantém siglas pré-definidas em maiúsculo.
    """
    if not isinstance(value, str):
        return value

    # Lista de siglas que devem permanecer em maiúsculo.
    # Você pode adicionar ou remover siglas aqui conforme sua necessidade.
    ACRONYMS = ['FGTS', 'DAS', 'NR', 'GPS', 'IRRF', 'PIS', 'COFINS', 'CSLL', 'MEI']

    words = value.split()
    processed_words = []
    for word in words:
        # Remove pontuações comuns para uma verificação mais limpa
        clean_word = word.strip('.,:;')
        if clean_word.upper() in ACRONYMS:
            # Se for uma sigla, mantenha em maiúsculo
            processed_words.append(word.upper())
        else:
            # Caso contrário, aplique a capitalização padrão
            processed_words.append(word.title())
            
    return ' '.join(processed_words)
