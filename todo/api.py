from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Task
from .services import task_update_service, task_delete_service
from .selectors import get_all_tasks_for_user, get_task_for_user
from .exceptions import ScheduledDateInPastError, DueDateInPastError

from django.contrib.auth import get_user_model

User = get_user_model()


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
    def get(self, request: HttpRequest):
        user = request.user
        tasks = get_all_tasks_for_user(user=user)
        data = TaskSerializer(tasks, many=True).data
        return Response(data)


class DetailTaskAPI(BaseAPIView):
    def get(self, request: HttpRequest, pk: int):
        """
        Get Details for a specific task
        """

        user = request.user
        task: Task = get_task_for_user(user=user, task_id=pk)
        data = TaskSerializer(task).data
        return Response(data)

    def patch(self, request, pk: int):
        """
        Handles partial updates for a specific task.
        """
        serializer = TaskSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            task, updated = task_update_service(
                task_id=pk, user=request.user, **serializer.validated_data
            )

        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND
            )

        except (ValueError, DueDateInPastError, ScheduledDateInPastError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            return Response(
                {"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if updated:
            response_serializer = TaskSerializer(task)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        else:
            response_serializer = TaskSerializer(task)
            return Response(
                response_serializer.data, status=status.HTTP_304_NOT_MODIFIED
            )

    def delete(self, request, pk: int):
        user = request.user
        task_deleted = task_delete_service(user=user, task_id=pk)
        if task_deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_304_NOT_MODIFIED)


# TODO: AddTaskAPI
class AddTaskAPI(BaseAPIView):
    pass


# TODO: ToggleStatusAPI
class ToggleStatusAPI(BaseAPIView):
    pass
