from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver  
from .models import Job, UserProfile
import os

@receiver(post_save, sender=Job)
@receiver(post_save, sender=UserProfile)
@receiver(post_delete, sender=Job)
@receiver(post_delete, sender=UserProfile)
def clear_cache(sender, instance, **kwargs):
    cache_dir = os.path.join(settings.BASE_DIR, 'cache')
    if os.path.exists(cache_dir):
        for file in os.listdir(cache_dir):
            os.remove(os.path.join(cache_dir, file))

