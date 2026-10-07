from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=User)
def make_profile(sender, instance, created, **kwargs):
    # every new account gets a profile row so the avatar code never has to guess
    if created:
        Profile.objects.get_or_create(user=instance)
