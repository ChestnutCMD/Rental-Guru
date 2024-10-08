from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Complaint
from .permissions import IsMemberOrManagerAdmin
from .serializers import ComplaintSerializer


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.all()
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated, IsMemberOrManagerAdmin]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
