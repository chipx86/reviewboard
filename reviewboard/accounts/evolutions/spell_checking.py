from django_evolution.mutations import AddField
from django.db import models


MUTATIONS = [
    AddField('Profile', 'spell_checking', models.BooleanField, initial=True)
]
