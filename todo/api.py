from rest_framework import serializers
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Task

from .selectors import get_all_tasks_for_user


# TODO: add support for token authentication
class ListTasksAPI(APIView):
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

    def get(self, request):
        user = request.user
        tasks = get_all_tasks_for_user(user=user)

        data = self.TaskSerializer(tasks, many=True).data

        return Response(data)


# TODO: GetTaskAPI
# TODO: UpdateTakskAPI
# TODO: AddTaskAPI
# TODO: DeleteTaskAPI
# TODO: ToggleStatusAPI
