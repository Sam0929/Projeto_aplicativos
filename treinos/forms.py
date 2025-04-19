from django import forms

class TreinoForm(forms.Form):
    nome_treino = forms.CharField(label='Nome do Treino', max_length=100)