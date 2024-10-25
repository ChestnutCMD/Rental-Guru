from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Complaint
from .permissions import IsMemberOrManagerAdmin
from .serializers import ComplaintSerializer


@extend_schema(summary="Жалобы на транспорт CRUD", description="Жалобы на транспорт")
class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated, IsMemberOrManagerAdmin]

    def perform_create(self, serializer):
        serializer.save()
