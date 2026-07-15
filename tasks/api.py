from typing import Any, cast

from django.http import HttpRequest
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import DueDateInPastError, ScheduledDateInPastError
from .models import Task
from .selectors import get_all_tasks_for_user, get_task_for_user
from .services import (
    task_add_service,
    task_delete_service,
    task_update_service,
    toggle_task_status_service,
)


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
            "labels",
        ]


class BaseAPIView(APIView):
    permission_classes = [IsAuthenticated]


class ListCreateApiView(BaseAPIView):
    def get(self, request: HttpRequest) -> Response:
        user = request.user
        tasks = get_all_tasks_for_user(user=user)
        data = TaskSerializer(instance=tasks, many=True).data
        return Response(data)

    def post(self, request) -> Response:
        user = request.user
        serializer = TaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = cast(dict[str, Any], serializer.validated_data)
        task_add_service(
            title=data["title"],
            description=data.get("description"),
            status=data.get("status", Task.Status.IN_PROGRESS),
            priority=data.get("priority", Task.Priority.MEDIUM),
            due_datetime=data.get("due_datetime"),
            scheduled_date=data.get("scheduled_date"),
            owner=user,
            labels=data.get("labels"),
        )
        return Response(status=status.HTTP_201_CREATED)


class DetailUpdateDeleteTaskApiView(BaseAPIView):
    def get(self, request: HttpRequest, pk: int) -> Response:
        """
        Get details for a specific task
        """
        user = request.user
        task: Task = get_task_for_user(user=user, task_id=pk)
        data = TaskSerializer(instance=task).data
        return Response(data)

    def patch(self, request, pk: int) -> Response:
        """
        Handles partial updates for a specific task.
        """
        serializer = TaskSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = cast(dict[str, Any], serializer.validated_data)
            task, updated = task_update_service(
                task_id=pk,
                user=request.user,
                title=data.get("title"),
                description=data.get("description"),
                status=data.get("status"),
                priority=data.get("priority"),
                due_datetime=data.get("due_datetime"),
                scheduled_date=data.get("scheduled_date"),
                labels=data.get("labels"),
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
            response_serializer = TaskSerializer(instance=task)
            return Response(data=response_serializer.data, status=status.HTTP_200_OK)
        else:
            response_serializer = TaskSerializer(instance=task)
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
