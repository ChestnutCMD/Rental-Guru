from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from vehicle.models import Vehicle
from .models import User, RenterDocuments, Renter
from .permissions import IsAdminOrSelf
from .serializers import RegisterSerializer, ChangePasswordSerializer, UserListSerializer, UserDetailSerializer, \
    RenterDocumentsSerializer, VehicleListSerializer


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


@extend_schema(summary="Пользователи", description="Регистрация, получение списка пользователей, получение пользователя по ID, обновление, удаление")
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


@extend_schema(summary="Документы арендаторы", description="Документы арендатора")
class RenterDocumentsViewSet(viewsets.ModelViewSet):
    serializer_class = RenterDocumentsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            renter = user.renter
        except ObjectDoesNotExist:
            return RenterDocuments.objects.none()
        return RenterDocuments.objects.filter(renter=renter)

    def perform_create(self, serializer):
        user = self.request.user
        try:
            renter = user.renter
        except ObjectDoesNotExist:
            raise Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(renter=renter)

    def perform_update(self, serializer):
        user = self.request.user
        try:
            renter = user.renter
        except ObjectDoesNotExist:
            raise Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(renter=renter)

    def perform_destroy(self, instance):
        user = self.request.user
        try:
            renter = user.renter
        except ObjectDoesNotExist:
            raise Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)
        if instance.renter != renter:
            raise Response({'detail': 'Документ не принадлежит текущему арендатору'}, status=status.HTTP_400_BAD_REQUEST)
        instance.delete()


@extend_schema(summary="Избранный транпорт", description="Избранный транпорт арендатора. Эндпоинты app/favorite/add/ "
                                                         "и app/favorite/remove/ принимают {'vehicle_id': id} для "
                                                         "добавления и удаления в список избранного соответственно")
class FavoriteVehicleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        try:
            renter = user.renter
        except Renter.DoesNotExist:
            return Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)

        favorites = renter.favorite.all()
        serializer = VehicleListSerializer(favorites, many=True)
        return Response({'favorites': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='add', url_name='add_favorite')
    def add_favorite(self, request):
        """
        Добавить транспортное средство в избранное.
        """
        user = request.user
        try:
            renter = user.renter
        except Renter.DoesNotExist:
            return Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)

        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response({'detail': 'Требуется ID транспортного средства'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            renter.favorite.add(vehicle)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Vehicle.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['patch'], url_path='remove', url_name='remove_favorite')
    def remove_favorite(self, request):
        """
        Убрать транспортное средство из избранного.
        """
        user = request.user
        try:
            renter = user.renter
        except Renter.DoesNotExist:
            return Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)

        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response({'detail': 'Требуется ID транспортного средства'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            renter.favorite.remove(vehicle)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Vehicle.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_404_NOT_FOUND)
