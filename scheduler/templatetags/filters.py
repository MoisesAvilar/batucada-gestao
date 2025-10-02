from django import template

register = template.Library()

PREPOSICOES = {"da", "do", "das", "dos", "de"}


@register.filter
def smart_truncate(value, num_words):
    """
    Trunca um nome para X palavras, evitando terminar em preposições como 'da', 'dos', etc.
    """
    try:
        num_words = int(num_words)
    except (ValueError, TypeError):
        return value

    words = value.split()
    if len(words) <= num_words:
        return value

    result = words[:num_words]

    # Se a última palavra for uma preposição, remove e tenta adicionar mais uma
    if result[-1].lower() in PREPOSICOES:
        if len(words) > num_words:
            result = words[:num_words + 1]
        else:
            result = words[:num_words - 1]

    return ' '.join(result)