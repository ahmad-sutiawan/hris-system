from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.employees.models import Employee
from apps.employees.services.photo import _is_new_upload, maybe_compress_employee_photo


@receiver(pre_save, sender=Employee)
def compress_employee_profile_photo(sender, instance, **kwargs):
    photo = instance.photo
    if not photo or not photo.name:
        return
    if _is_new_upload(photo):
        maybe_compress_employee_photo(instance, previous_name="")
        return
    previous_name = (
        Employee.objects.filter(pk=instance.pk).values_list("photo", flat=True).first() or ""
    )
    maybe_compress_employee_photo(instance, previous_name=previous_name)
