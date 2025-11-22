# Em leads/templatetags/lead_extras.py

import re
from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter(name="format_contact", is_safe=True)
def format_contact(value):
    """
    Formata um valor de contato.
    - Se for e-mail, cria um link 'mailto:'.
    - Se for telefone, cria um dropdown com opções para WhatsApp e ligação.
    """
    if not isinstance(value, str):
        return value

    value = value.strip()

    # --- Lógica para E-mail (sem alteração) ---
    if "@" in value:
        return format_html(
            '<a href="mailto:{0}" class="text-decoration-none">'
            '<i class="bi bi-envelope me-2"></i>{0}'
            "</a>",
            value,
        )

    # --- NOVA LÓGICA PARA TELEFONE (COM DROPDOWN) ---
    else:
        digits_only = re.sub(r"\D", "", value)
        formatted_phone = ""

        if len(digits_only) == 11:
            formatted_phone = "({0}) {1}-{2}".format(
                digits_only[0:2], digits_only[2:7], digits_only[7:11]
            )
        elif len(digits_only) == 10:
            formatted_phone = "({0}) {1}-{2}".format(
                digits_only[0:2], digits_only[2:6], digits_only[6:10]
            )
        else:
            return value  # Retorna o original se não for um telefone válido

        # Prepara os números para os links (assumindo código do Brasil 55 para o WhatsApp)
        whatsapp_number = "55" + digits_only
        tel_number = digits_only

        # Monta o HTML do dropdown do Bootstrap
        dropdown_html = format_html(
            """
            <div class="dropdown d-inline-block">
                <a href="#" class="text-decoration-none dropdown-toggle" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="bi bi-telephone me-2"></i>{0}
                </a>
                <ul class="dropdown-menu">
                    <li>
                        <a class="dropdown-item" href="https://wa.me/{1}" target="_blank" rel="noopener noreferrer">
                            <i class="bi bi-whatsapp me-2 text-success"></i>Abrir WhatsApp
                        </a>
                    </li>
                    <li>
                        <a class="dropdown-item" href="tel:{2}">
                            <i class="bi bi-telephone-outbound me-2"></i>Fazer Ligação
                        </a>
                    </li>
                </ul>
            </div>
            """,
            formatted_phone,
            whatsapp_number,
            tel_number,
        )
        return dropdown_html
