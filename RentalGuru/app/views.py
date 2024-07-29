from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets


from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .permissions import IsAdminOrSelf
from .serializers import RegisterSerializer, ChangePasswordSerializer, UserListSerializer, UserDetailSerializer


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


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        elif self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer


    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminOrSelf]
        return super().get_permissions()

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
