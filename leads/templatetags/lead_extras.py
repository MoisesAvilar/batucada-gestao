import re
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="format_contact")
def format_contact(value):
    """
    Formata um valor de contato.
    - Se for e-mail, cria um link 'mailto:' com um ícone.
    - Se for telefone, aplica a máscara (XX) XXXX-XXXX ou (XX) XXXXX-XXXX
      e cria um link 'tel:' com um ícone.
    """
    if not isinstance(value, str):
        return value

    value = value.strip()

    # Se for um E-mail
    if "@" in value:
        # A tag 'safe' é necessária para renderizar o HTML do ícone
        return format_html(
            '<a href="mailto:{0}" class="text-decoration-none">'
            '<i class="bi bi-envelope me-2"></i>{0}'
            "</a>",
            value,
        )

    # Se for um Telefone
    else:
        digits_only = re.sub(r"\D", "", value)

        # Formato para 11 dígitos (celular com 9)
        if len(digits_only) == 11:
            formatted_phone = "({0}) {1}-{2}".format(
                digits_only[0:2], digits_only[2:7], digits_only[7:11]
            )
        # Formato para 10 dígitos (fixo ou celular antigo)
        elif len(digits_only) == 10:
            formatted_phone = "({0}) {1}-{2}".format(
                digits_only[0:2], digits_only[2:6], digits_only[6:10]
            )
        # Se não tiver 10 ou 11 dígitos, retorna o valor original
        else:
            return value

        return format_html(
            '<a href="tel:{0}" class="text-decoration-none">'
            '<i class="bi bi-telephone me-2"></i>{1}'
            "</a>",
            digits_only,
            formatted_phone,
        )
