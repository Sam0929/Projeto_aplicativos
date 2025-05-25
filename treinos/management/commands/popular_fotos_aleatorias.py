# users/management/commands/popular_fotos_aleatorias.py

import os
import tempfile
import requests

from django.core.files import File
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Profile

User = get_user_model()

class Command(BaseCommand):
    help = (
        "Atribui avatares e imagens de capa aleatórias aos perfis que ainda não têm. "
        "Utiliza o Picsum (https://picsum.photos/) para obter fotos de exemplo."
    )

    def handle(self, *args, **options):
        # URLs “aleatórias” no Picsum:
        #   - https://picsum.photos/200/200   → avatar quadrado (200×200)
        #   - https://picsum.photos/800/180   → capa retangular (800×180)
        #
        # Se você preferir outro serviço, basta trocar as URLs abaixo.

        # 1) Percorre todos os usuários que têm Profile cadastrado
        perfis = Profile.objects.select_related("user").all()
        total = perfis.count()
        self.stdout.write(f"Encontrados {total} perfis. Iniciando download de imagens…")

        for perfil in perfis:
            # Se o avatar JÁ existe no Profile (não é default), pule.
            # Ajuste essa lógica conforme seu campo default; aqui assumimos que
            # valores “default.png” e “cover_default.jpg” significam que não há foto personalizada.
            #
            precisa_avatar = not perfil.avatar.name or "default.png" in perfil.avatar.name
            precisa_cover  = not perfil.cover_photo.name or "cover_default.jpg" in perfil.cover_photo.name

            # --- Avatar 200×200 ---
            if precisa_avatar:
                try:
                    resp = requests.get("https://picsum.photos/200/200", timeout=10)
                    resp.raise_for_status()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"[{perfil.user.username}] falha ao baixar avatar: {e}"
                    ))
                else:
                    # salva em um arquivo temporário para depois guardar no ImageField
                    nome_tmp = f"{perfil.user.username}_avatar.jpg"
                    caminho_tmp = os.path.join(tempfile.gettempdir(), nome_tmp)
                    with open(caminho_tmp, "wb") as f:
                        f.write(resp.content)

                    # abre o arquivo e atribui ao campo avatar
                    with open(caminho_tmp, "rb") as f:
                        perfil.avatar.save(nome_tmp, File(f), save=False)
                    os.remove(caminho_tmp)
                    self.stdout.write(self.style.SUCCESS(
                        f"[{perfil.user.username}] avatar atribuído."
                    ))
            else:
                self.stdout.write(f"[{perfil.user.username}] já tem avatar. Pulando…")

            # --- Capa 800×180 ---
            if precisa_cover:
                try:
                    resp2 = requests.get("https://picsum.photos/800/180", timeout=10)
                    resp2.raise_for_status()
                except Exception as e:
                    self.stdout.write(self.style.WARNING(
                        f"[{perfil.user.username}] falha ao baixar cover: {e}"
                    ))
                else:
                    nome_tmp2 = f"{perfil.user.username}_cover.jpg"
                    caminho_tmp2 = os.path.join(tempfile.gettempdir(), nome_tmp2)
                    with open(caminho_tmp2, "wb") as f:
                        f.write(resp2.content)

                    with open(caminho_tmp2, "rb") as f:
                        perfil.cover_photo.save(nome_tmp2, File(f), save=False)
                    os.remove(caminho_tmp2)
                    self.stdout.write(self.style.SUCCESS(
                        f"[{perfil.user.username}] cover atribuído."
                    ))
            else:
                self.stdout.write(f"[{perfil.user.username}] já tem cover. Pulando…")

            # Salva perfil (avatar e/ou cover gravados)
            perfil.save()

        self.stdout.write(self.style.SUCCESS("Todos os perfis foram processados."))
