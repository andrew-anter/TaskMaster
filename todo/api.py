from django.http import HttpRequest
from rest_framework import serializers
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Task
from .services import (
    task_update_service,
    task_delete_service,
    task_add_service,
    toggle_task_status_service,
)
from .selectors import get_all_tasks_for_user, get_task_for_user
from .exceptions import ScheduledDateInPastError, DueDateInPastError

from django.contrib.auth import get_user_model

User = get_user_model()


# TODO: add support for token authentication
class BaseAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]


class ListCreateApiView(BaseAPIView):
    class TaskSerializer(serializers.ModelSerializer):
        class Meta:
            model = Task
            fields: list[str] = [
                "id",
                "title",
                "description",
                "status",
                "priority",
                "due_datetime",
                "scheduled_date",
                "created_at",
                "modified_at",
            ]

    def get(self, request: HttpRequest) -> Response:
        user = request.user
        tasks = get_all_tasks_for_user(user=user)
        data = self.TaskSerializer(instance=tasks, many=True).data
        return Response(data)

    class TaskUpdateSerializer(serializers.ModelSerializer):
        class Meta:
            model = Task
            fields: list[str] = [
                "title",
                "description",
                "status",
                "priority",
                "due_datetime",
                "scheduled_date",
                "created_at",
                "modified_at",
            ]

    def post(self, request) -> Response:
        user = request.user
        serializer = self.TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_add_service(**serializer.validated_data, owner=user)
        return Response(status=status.HTTP_201_CREATED)


class DetailUpdateDeleteTaskApiView(BaseAPIView):
    class TaskSerializer(serializers.ModelSerializer):
        class Meta:
            model = Task
            fields: list[str] = [
                "title",
                "description",
                "status",
                "priority",
                "due_datetime",
                "scheduled_date",
                "created_at",
                "modified_at",
            ]

    def get(self, request: HttpRequest, pk: int) -> Response:
        """
        Get Details for a specific task
        """

        user = request.user
        task: Task = get_task_for_user(user=user, task_id=pk)
        data = self.TaskSerializer(instance=task).data
        return Response(data)

    def patch(self, request, pk: int) -> Response:
        """
        Handles partial updates for a specific task.
        """
        serializer = self.TaskSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            task, updated = task_update_service(
                task_id=pk, user=request.user, **serializer.validated_data
            )

        except Task.DoesNotExist:
            return Response(
                {"error": "Task not found."}, status=status.HTTP_404_NOT_FOUND
            )

        except (ValueError, DueDateInPastError, ScheduledDateInPastError) as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            return Response(
                data={"error": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if updated:
            response_serializer = self.TaskSerializer(instance=task)
            return Response(data=response_serializer.data, status=status.HTTP_200_OK)
        else:
            response_serializer = self.TaskSerializer(instance=task)
            return Response(
                data=response_serializer.data, status=status.HTTP_304_NOT_MODIFIED
            )

    def delete(self, request, pk: int) -> Response:
        user = request.user
        task_delete_service(user=user, task_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ToggleStatusAPI(BaseAPIView):
    def post(self, request, pk: int) -> Response:
        user = request.user
        task = get_task_for_user(user=user, task_id=pk)
        toggle_task_status_service(task=task)
        return Response(status=status.HTTP_200_OK)
