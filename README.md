<h1 align="center"> Projeto Aplicativos</h1>

### Passo a passo acesso ao projeto

Clone Repositório criado a partir do template, entre na pasta e execute os comandos abaixo:

Crie um ambiente virtual e ative-o:
```sh
python -m venv venv
```
```sh
venv\Scripts\activate
```
Instale as dependências:
```sh
pip install -r requirements.txt
```

Faça as migrations do bando de dados:
```sh
python manage.py makemigrations
```

Suba as migrations:
```sh
python manage.py migrate
```

Para iniciar o server:
```sh
python manage.py runserver
```

Acesse o site:
```sh
localhost:8000
```
