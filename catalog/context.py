from django.conf import settings


def platform(request):
    return {"PLATFORM_NAME": settings.PLATFORM_NAME}
