from rest_framework import generics, status
from rest_framework.generics import RetrieveAPIView, DestroyAPIView

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import RegisterSerializer, CustomUserSerializer, ChangePasswordSerializer, UserUpdateSerializer


class RegisterView(generics.CreateAPIView):
    """Регистрация пользователя"""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


class UserListView(generics.ListAPIView):
    """Получение списка всех пользователей"""
    queryset = User.objects.all().select_related('lessor', 'renter')
    serializer_class = CustomUserSerializer


class ChangePasswordView(APIView):
    """Смена пароля"""
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRetrieveAPIView(generics.UpdateAPIView, RetrieveAPIView, DestroyAPIView):
    """Детальное получение, обновление, удаление пользователя по ID"""
    queryset = User.objects.all().select_related('lessor', 'renter')
    serializer_class = UserUpdateSerializer
