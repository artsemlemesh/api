from django.db.models import Model
from django.utils.translation import gettext_lazy as _
from django_currentuser.db.models import CurrentUserField

class AuthStampedModel(Model):
	"""
	An abstract base class model that provides auth information fields.
	"""
	created_by = CurrentUserField(related_name = "created_%(app_label)s_%(class)s_set")
	modified_by =  CurrentUserField(related_name = "modified_%(app_label)s_%(class)s_set")

	class Meta:
		abstract = True
