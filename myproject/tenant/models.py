from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=30)
    owner = models.ForeignKey(
        to="self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )


class Partner(Tenant):
    partner_field = models.CharField(max_length=30)


class Client(Tenant):
    client_field = models.CharField(max_length=30)
