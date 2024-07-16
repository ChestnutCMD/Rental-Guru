from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.generics import RetrieveAPIView, DestroyAPIView

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import RegisterSerializer, CustomUserSerializer, ChangePasswordSerializer, UserUpdateSerializer


@extend_schema(summary="Регистрация пользователя", description="Регистрация пользователя")
class RegisterView(generics.CreateAPIView):
    """Регистрация пользователя"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


@extend_schema(summary="Получение списка всех пользователей", description="Получение списка всех пользователей")
class UserListView(generics.ListAPIView):
    """Получение списка всех пользователей"""
    queryset = User.objects.all().select_related('lessor', 'renter')
    serializer_class = CustomUserSerializer


@extend_schema(summary="Смена пароля", description="Смена пароля")
class ChangePasswordView(APIView):
    """Смена пароля"""
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="Пользователь по ID", description="Детальное получение, обновление, удаление пользователя по ID")
class UserRetrieveAPIView(generics.UpdateAPIView, RetrieveAPIView, DestroyAPIView):
    """Детальное получение, обновление, удаление пользователя по ID"""
    queryset = User.objects.all().select_related('lessor', 'renter')
    serializer_class = UserUpdateSerializer
