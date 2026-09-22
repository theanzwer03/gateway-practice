from rest_framework.viewsets import ModelViewSet

from .models import User
from .permissions import IsAdminRole
from .serializers import UserSerializer


class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
