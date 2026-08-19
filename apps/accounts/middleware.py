from django.conf import settings
from django.http import HttpResponseRedirect


def redirect_localhost(get_response):
    def middleware(request):
        host = request.get_host().split(":")[0]
        if host == "localhost":
            return HttpResponseRedirect(settings.SITE_URL + request.get_full_path())
        return get_response(request)

    return middleware
