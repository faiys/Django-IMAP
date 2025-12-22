from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from rest_framework.decorators import api_view

# Create your views here.

# http://127.0.0.1:8000/login/?e=test@gmail.com&a=dijfhsjdbjsj
@api_view(['GET'])
def login(req):
    email = req.GET.get('e')
    appPass = req.GET.get('a')

    user_obj = User.objects.filter(email=email).first()
    if user_obj is None and not appPass:
        return JsonResponse({"message": "Allow to create user"}, status=201)
    if email and appPass and user_obj is None:
        create_user = User.objects.create(email=email,username=email.split('@')[0], last_name=appPass)
        if create_user:
            return JsonResponse({"message": "User Created"}, status=200)
    # return JsonResponse({"message: User already created"}, status=200)
    return HttpResponse(user_obj)


