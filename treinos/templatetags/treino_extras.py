

from django import template

register = template.Library()

@register.filter
def dict_key(d, key):
    """
    Retorna d.get(key) para que possamos usar, na template:
       {{ meu_dicionario|dict_key:chave }}
    """
    try:
        return d.get(key)
    except Exception:
        return None
