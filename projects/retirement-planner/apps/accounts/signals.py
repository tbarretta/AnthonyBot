from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .models import AuditLog, AuditEvent


def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        user=user,
        user_email=user.email,
        event=AuditEvent.LOGIN,
        ip_address=_get_ip(request),
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user:
        AuditLog.objects.create(
            user=user,
            user_email=user.email,
            event=AuditEvent.LOGOUT,
            ip_address=_get_ip(request),
        )


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    AuditLog.objects.create(
        user_email=credentials.get('username', ''),
        event=AuditEvent.LOGIN_FAILED,
        ip_address=_get_ip(request),
    )
