from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings
from app.models.expiring import ExpiringToken
from app.models.cart import Cart
from app.models.product import Product, BG_REMOVAL_STATUS, ProductCategory, ProductBrand, ProductSize
from cacheops import cache




@receiver(post_save, sender=get_user_model())
def user_save_hook(sender, instance, created, **kwargs):
    """
    create user auth token whenever a user is created
    """
    if created:
        try:
            instance.environment_id = settings.ENVIRONMENT + "_" +str(instance.id)
            instance.save()
        except Exception as e:
            print("Failed to update user's environment_id for user: ", instance.id)
        # create user's auth token
        ExpiringToken.objects.get_or_create(user=instance)
        Cart.objects.create(user=instance)


@receiver(post_save, sender=Product)
def trigger_bg_removal_process(sender, instance, created, **kwargs):
    # TODO: temporarily removing background removal
    return

    updated_fields = kwargs.get('update_fields')
    if created or 'front_image_large' in updated_fields or \
            'back_image_large' in updated_fields or 'images' in updated_fields:
        if instance.bg_removal_status in [
            BG_REMOVAL_STATUS.failed, BG_REMOVAL_STATUS.to_do,
            BG_REMOVAL_STATUS.done]:
            instance.request_to_remove_background(raise_exception=True)
            instance.save()


@receiver(post_save, sender=ProductBrand)
def trigger_approved(sender, instance, created, **kwargs):
    if created:
        pass
    else:
        if instance.Suggested_by == 0:
            pass
        else:
            user = get_user_model().objects.get(pk=instance.Suggested_by)
            if instance.Approved == 1 and instance.suggested == False:
                user = get_user_model().objects.get(email=user.email)
                user.send_user_notify()
                print(f'----------Approved mail sent Successfully to user on this email  {user.email}--------------')
            elif instance.Approved == 2 and instance.suggested == True:
                user = get_user_model().objects.get(email=user.email)
                user.send_user_notify_onreject()
                print(f'--------Rejection mail sent successfully to user on this email  {user.email}------------ ')
            else:
                pass


@receiver([post_save, post_delete], sender=ProductSize)
@receiver([post_save, post_delete], sender=ProductBrand)
@receiver([post_save, post_delete], sender=ProductCategory)
def trigger_options_invalidation(sender, instance, **kwargs):
    cache.delete('item_options')
