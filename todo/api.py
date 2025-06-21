from rest_framework import serializers
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Task
from .selectors import get_all_tasks_for_user, get_task_for_user


# TODO: add support for token authentication
class BaseAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "title",
            "description",
            "status",
            "priority",
            "due_datetime",
            "scheduled_date",
            "created_at",
            "modified_at",
        ]


class ListTasksAPI(BaseAPIView):
    def get(self, request):
        user = request.user
        tasks = get_all_tasks_for_user(user=user)
        data = TaskSerializer(tasks, many=True).data
        return Response(data)


class DetailTaskAPI(BaseAPIView):
    def get(self, request, pk: int):
        user = request.user
        task = get_task_for_user(user=user, task_id=pk)
        data = TaskSerializer(task).data
        return Response(data)


# TODO: UpdateTakskAPI
class UpdateTaskAPI(BaseAPIView):
    pass


# TODO: AddTaskAPI
class AddTaskAPI(BaseAPIView):
    pass


# TODO: DeleteTaskAPI
class DeleteTaskAPI(BaseAPIView):
    pass


# TODO: ToggleStatusAPI
class ToggleStatusAPI(BaseAPIView):
    pass
