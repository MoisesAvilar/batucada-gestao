import re
from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter(name="format_contact", is_safe=True)
def format_contact(value, custom_whatsapp_url=None):
    """
    Formata um valor de contato.
    - Se for e-mail, cria um link 'mailto:'.
    - Se for telefone, cria um dropdown com opções para WhatsApp e ligação.
    - custom_whatsapp_url: (Opcional) URL completa para o WhatsApp (ex: com mensagem pré-definida).
    """
    if not isinstance(value, str):
        return value

    value = value.strip()

    # --- Lógica para E-mail ---
    if "@" in value:
        return format_html(
            '<a href="mailto:{0}" class="text-decoration-none">'
            '<i class="bi bi-envelope me-2"></i>{0}'
            "</a>",
            value,
        )

    # --- Lógica para Telefone ---
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
            return value

        # Define qual URL usar: a personalizada (vinda da View) ou a padrão
        if custom_whatsapp_url and str(custom_whatsapp_url).startswith("http"):
            final_whatsapp_url = custom_whatsapp_url
        else:
            final_whatsapp_url = f"https://wa.me/55{digits_only}"

        tel_number = digits_only

        # Monta o HTML do dropdown
        dropdown_html = format_html(
            """
            <div class="dropdown d-inline-block">
                <a href="#" class="text-decoration-none dropdown-toggle text-body" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                    <i class="bi bi-whatsapp me-1 text-success opacity-75"></i>{0}
                </a>
                <ul class="dropdown-menu">
                    <li>
                        <a class="dropdown-item" href="{1}" target="_blank" rel="noopener noreferrer">
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
            final_whatsapp_url,
            tel_number,
        )
        return dropdown_html
