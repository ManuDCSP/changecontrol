import os

from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.shortcuts import HttpResponse
from django.shortcuts import render

from changecontrol.settings import MEDIA_ROOT
from .models import ChangeSet, XMLTools


def index(request):
    change_sets = ChangeSet.objects.all()
    return render(request, 'index.html', {'change_sets':change_sets})
    #return HttpResponse('Hello World')


def new(request):
    return HttpResponse('New Change Set')


def upload(request):
    if request.method == 'POST' and request.FILES['myfile'] and request.FILES['myfile2']:
        fs = FileSystemStorage()
        xmlTools = XMLTools(MEDIA_ROOT,MEDIA_ROOT)
        sortedfile1_url=""
        sortedfile2_url=""

        uplfile1 = request.FILES['myfile']
        uplfile1_name = fs.save(uplfile1.name, uplfile1)
        if uplfile1_name.endswith(".xml"):
            sortedfile1_name = f"{os.path.splitext(uplfile1_name)[0]}_sorted{os.path.splitext(uplfile1_name)[1]}"
            sortedfile1 = xmlTools.process_document(os.path.join(MEDIA_ROOT, uplfile1_name), sortedfile1_name)
            sortedfile1_url = fs.url(sortedfile1_name)

        uplfile2 = request.FILES['myfile2']
        uplfile2_name = fs.save(uplfile2.name, uplfile2)
        if uplfile2_name.endswith(".xml"):
            sortedfile2_name = f"{os.path.splitext(uplfile2_name)[0]}_sorted{os.path.splitext(uplfile2_name)[1]}"
            sortedfile2 = xmlTools.process_document(os.path.join(MEDIA_ROOT, uplfile1_name), sortedfile2_name)
            sortedfile2_url = fs.url(sortedfile2_name)

        return render(request, 'upload.html', {
            'uploaded_file_url': sortedfile1_url, 'uploaded_file_url2': sortedfile2_url
        })
    return render(request, 'upload.html')

