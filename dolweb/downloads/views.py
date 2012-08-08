from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from dolweb.downloads.models import DevVersion, ReleaseVersion

import hashlib
import hmac

def index(request):
    """Displays the downloads index"""

    releases = ReleaseVersion.objects.order_by('-date')
    master_builds = DevVersion.objects.filter(branch='master').order_by('-date')[:20]

    return render_to_response('downloads-index.html', {
        'releases': releases,
        'master_builds': master_builds,
    }, context_instance=RequestContext(request))

def branches(request):
    raise NotImplemented

@csrf_exempt
def new(request):
    """Callback used by the buildbot to register a new build"""

    if request.method != 'POST':
        raise Http404

    # Check the message signature
    branch = request.POST['branch']
    shortrev = request.POST['shortrev']
    hash = request.POST['hash']
    author = request.POST['author']
    description = request.POST['description']
    build_type = request.POST['build_type']
    build_url = request.POST['build_url']
    msg = "%d|%d|%d|%d|%d|%d|%d|%s|%s|%s|%s|%s|%s|%s" % (
        len(branch), len(shortrev), len(hash), len(author), len(description),
        len(build_type), len(build_url),

        branch, shortrev, hash, author, description, build_type, build_url
    )
    hm = hmac.new(settings.DOWNLOADS_CREATE_KEY, msg, hashlib.sha1)
    if hm.hexdigest() != request.POST['hmac']:
        return HttpResponse('Invalid HMAC', status=403)

    # Check if we already have a commit with the same hash
    try:
        build_obj = DevVersion.objects.get(hash=hash)
    except DevVersion.DoesNotExist:
        build_obj = DevVersion()
        build_obj.branch = branch
        build_obj.shortrev = shortrev
        build_obj.hash = hash
        build_obj.author = author
        build_obj.description = description

        # Shorten the description by taking only the first line, truncating it to
        # 250 chars and adding an ellipsis if truncated
        descr_abbrev = description.split('\n')[0]
        if len(descr_abbrev) >= 250:
            descr_abbrev = descr_abbrev[:250] + "..."
        build_obj.description_abbrev = descr_abbrev

    if build_type == 'win32':
        build_obj.win32_url = build_url
    elif build_type == 'win64':
        build_obj.win64_url = build_url
    elif build_type == 'osx':
        build_obj.osx_url = build_url
    else:
        return HttpResponse('Wrong build type', status=400)

    build_obj.save()
    return HttpResponse('OK')