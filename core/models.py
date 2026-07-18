"""Core app — shared base models, querysets, and mixins."""
import uuid
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base model with created_at / updated_at timestamps."""
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrgScopedQuerySet(models.QuerySet):
    """Queryset that filters by organization."""
    def for_org(self, organization):
        return self.filter(organization=organization)


class OrgScopedManager(models.Manager):
    def get_queryset(self):
        return OrgScopedQuerySet(self.model, using=self._db)

    def for_org(self, organization):
        return self.get_queryset().for_org(organization)


class OrgScopedModel(TimeStampedModel):
    """Abstract base model for org-isolated data."""
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)s_set',
    )

    objects = OrgScopedManager()

    class Meta:
        abstract = True
