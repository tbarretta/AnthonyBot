from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


@shared_task
def send_verification_email(user_id, token):
    from apps.accounts.models import User
    user = User.objects.get(pk=user_id)
    verify_url = f"{settings.SITE_URL}/accounts/verify/{token}/"
    body = render_to_string("emails/verify_email.txt", {
        "user": user,
        "verify_url": verify_url,
    })
    send_mail(
        subject="Verify your Gift Registry email address",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@shared_task
def send_invitation_email(invitation_id):
    from apps.families.models import FamilyInvitation
    inv = FamilyInvitation.objects.select_related("family", "invited_by").get(pk=invitation_id)
    register_url = f"{settings.SITE_URL}/accounts/register/{inv.token}/"
    body = render_to_string("emails/invitation.txt", {
        "invitation": inv,
        "register_url": register_url,
    })
    send_mail(
        subject=f"🎁 You've been invited to the {inv.family.name} Gift Registry",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[inv.email],
    )


@shared_task
def send_password_reset_email(user_id):
    from apps.accounts.models import User
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    user = User.objects.get(pk=user_id)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.SITE_URL}/accounts/reset-password/{uid}:{token}/"
    body = render_to_string("emails/password_reset.txt", {
        "user": user,
        "reset_url": reset_url,
    })
    send_mail(
        subject="Reset your Gift Registry password",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )

    from apps.notifications.models import ActivityLog
    ActivityLog.log(
        event_type="password_reset",
        actor=user,
        description=f"Password reset requested for {user.email}",
    )


@shared_task
def send_access_request_notification(access_request_id):
    from apps.access.models import WishlistAccessRequest
    req = WishlistAccessRequest.objects.select_related(
        "from_user", "to_user", "family"
    ).get(pk=access_request_id)

    approve_url = f"{settings.SITE_URL}/access/email/{req.token}/approve/"
    deny_url = f"{settings.SITE_URL}/access/email/{req.token}/deny/"

    body = render_to_string("emails/access_request.txt", {
        "req": req,
        "approve_url": approve_url,
        "deny_url": deny_url,
    })
    send_mail(
        subject=f"🔔 {req.from_user.name} wants to view your Gift Registry",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[req.to_user.email],
    )


@shared_task
def send_access_response_notification(access_request_id, action):
    from apps.access.models import WishlistAccessRequest
    req = WishlistAccessRequest.objects.select_related(
        "from_user", "to_user", "family"
    ).get(pk=access_request_id)

    body = render_to_string("emails/access_response.txt", {
        "req": req,
        "action": action,
        "wishlist_url": f"{settings.SITE_URL}/wishlist/{req.family_id}/member/{req.to_user_id}/",
    })
    verb = "approved" if action == "approved" else "declined"
    send_mail(
        subject=f"Gift Registry: {req.to_user.name} has {verb} your access request",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[req.from_user.email],
    )


@shared_task
def send_new_item_notification(item_id):
    from apps.wishlist.models import WishlistItem
    from apps.accounts.models import NewItemNotificationSubscription

    item = WishlistItem.objects.select_related("owner").get(pk=item_id)
    subscribers = NewItemNotificationSubscription.objects.filter(
        target_user=item.owner
    ).select_related("subscriber")

    for sub in subscribers:
        body = render_to_string("emails/new_item.txt", {
            "subscriber": sub.subscriber,
            "item": item,
            "wishlist_url": f"{settings.SITE_URL}/wishlist/",
        })
        send_mail(
            subject=f"🎁 {item.owner.name} added a new item to their wishlist",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[sub.subscriber.email],
        )
