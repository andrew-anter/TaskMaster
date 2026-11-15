import random
from datetime import timedelta
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from labels.models import Label
from notifications.models import Notification
from notifications.services import notify_bulk
from tasks.models import Task
from tasks.tasks import generate_reminder_notifications

if TYPE_CHECKING:
    from accounts.models import User
else:
    User = get_user_model()

SEED_USERNAME_PREFIX = "seed_user_"
SEED_LABEL_PREFIX = "Seed Label "

WORDS = [
    "Design",
    "Review",
    "Write",
    "Fix",
    "Update",
    "Refactor",
    "Test",
    "Deploy",
    "Migrate",
    "Document",
    "Optimize",
    "Investigate",
    "Implement",
    "Plan",
    "Prepare",
    "Clean",
    "Organize",
    "Research",
    "Draft",
    "Configure",
    "dashboard",
    "report",
    "API",
    "database",
    "frontend",
    "backend",
    "schema",
    "endpoint",
    "test suite",
    "docs",
    "deployment",
    "pipeline",
    "notifications",
    "reminders",
    "authentication",
    "authorization",
    "search",
    "filters",
    "templates",
    "middleware",
    "migrations",
    "queues",
    "worker",
    "webhook",
    "cache",
    "logging",
    "metrics",
    "onboarding",
    "settings page",
    "landing page",
]


def _title(rng: random.Random) -> str:
    count = rng.randint(3, 7)
    return " ".join(rng.sample(WORDS, count)).capitalize()


def _description(rng: random.Random, title: str) -> str:
    sentences = rng.randint(1, 4)
    parts = [title + "."]
    for _ in range(sentences):
        parts.append(" ".join(rng.sample(WORDS, rng.randint(5, 12))).capitalize() + ".")
    return " ".join(parts)


class Command(BaseCommand):
    help = (
        "Seed the database with demo data: users, labels, and tasks. "
        "Skips users/labels that already exist (identifiable by the "
        f"'{SEED_USERNAME_PREFIX}' / '{SEED_LABEL_PREFIX}' prefixes); "
        "re-running without --flush creates additional tasks. Pass "
        "--password to give every seeded user a usable password so the "
        "demo accounts can log in."
    )

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=100)
        parser.add_argument("--labels", type=int, default=50)
        parser.add_argument("--tasks", type=int, default=100_000)
        parser.add_argument("--batch-size", type=int, default=5_000)
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded users, labels, and tasks first.",
        )
        parser.add_argument(
            "--no-notifications",
            action="store_true",
            help="Skip seeding notifications (task reminders + welcome messages).",
        )
        parser.add_argument(
            "--seed", type=int, default=None, help="Seed for the random generator."
        )
        parser.add_argument(
            "--password",
            default=None,
            help=(
                "Password to set on every seeded user (new and previously "
                "seeded), so the demo accounts can log in."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        rng = random.Random(options["seed"])  # nosec B311 - demo data, not security
        n_users, n_labels, n_tasks = (
            options["users"],
            options["labels"],
            options["tasks"],
        )
        batch_size = options["batch_size"]

        if n_users < 1:
            raise CommandError("--users must be at least 1.")
        if n_labels < 0:
            raise CommandError("--labels must be 0 or greater.")
        if n_tasks < 0:
            raise CommandError("--tasks must be 0 or greater.")
        if batch_size < 1:
            raise CommandError("--batch-size must be at least 1.")

        if options["flush"]:
            self._flush()

        users = self._create_users(rng, n_users, password=options["password"])
        self._create_labels(rng, n_labels, users)
        labels_by_owner = {user.pk: [] for user in users}
        for owner_id, label_id in Label.objects.filter(
            name__startswith=SEED_LABEL_PREFIX
        ).values_list("owner_id", "id"):
            labels_by_owner[owner_id].append(label_id)

        self._create_tasks(rng, n_tasks, users, labels_by_owner, batch_size)

        if not options["no_notifications"]:
            self._create_notifications(users)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {n_users} users, {n_labels} labels, {n_tasks} tasks."
            )
        )

    def _create_notifications(self, users: list[User]) -> None:
        """Seed notifications: real task reminders via the periodic producer,
        plus a welcome message per user. Both are idempotent (dedupe keys)."""
        reminder_count = generate_reminder_notifications()
        welcome_count = notify_bulk(
            recipients=users,
            type="system_announcement",
            message="Welcome to TaskMaster — your tasks are ready.",
            link="/",
            dedupe_keys=[f"welcome:{user.pk}" for user in users],
        )
        self.stdout.write(
            f"  Generated {reminder_count + welcome_count} notifications"
            f" (duplicates skipped; {reminder_count} task reminders,"
            f" {welcome_count} welcome)."
        )

    def _flush(self) -> None:
        user_ids = User.objects.filter(
            username__startswith=SEED_USERNAME_PREFIX
        ).values_list("pk", flat=True)
        task_ids = Task.objects.filter(owner_id__in=user_ids).values_list(
            "pk", flat=True
        )
        Task.labels.through.objects.filter(task_id__in=task_ids).delete()
        # Explicit notification cleanup: deleting users/tasks does not cascade
        # through the generic foreign key, and SQLite may not enforce FKs at all.
        Notification.objects.filter(
            Q(recipient_id__in=user_ids)
            | Q(
                target_content_type=ContentType.objects.get_for_model(Task),
                target_object_id__in=task_ids,
            )
        ).delete()
        # Notifications are already gone at this point, so skip the per-row
        # post_delete receivers: a normal .delete() runs the generic-foreign-key
        # cascade lookup once per seeded task (100k on a full seed).
        tasks_to_delete = Task.objects.filter(pk__in=task_ids)
        tasks_to_delete._raw_delete(  # type: ignore[reportAttributeAccessIssue]
            tasks_to_delete.db
        )
        Label.objects.filter(name__startswith=SEED_LABEL_PREFIX).delete()
        deleted, _ = User.objects.filter(pk__in=user_ids).delete()
        self.stdout.write(
            f"Flushed {deleted} previously seeded users (and their data)."
        )

    def _create_users(
        self, rng: random.Random, n_users: int, *, password: str | None = None
    ) -> list[User]:
        seeded = User.objects.filter(username__startswith=SEED_USERNAME_PREFIX)
        existing = set(seeded.values_list("username", flat=True))

        new_users: list[User] = []
        i = 0
        while len(existing) + len(new_users) < n_users:
            i += 1
            username = f"{SEED_USERNAME_PREFIX}{i}"
            if username in existing:
                continue
            user = User(
                username=username,
                first_name=rng.choice(
                    ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank"]
                ),
                last_name=f"User {i}",
            )
            if password:
                user.set_password(password)
            new_users.append(user)
        if new_users:
            User.objects.bulk_create(new_users)

        users = list(seeded.order_by("id"))
        if password:
            # Previously seeded users need a hash too; one UPDATE per row is
            # fine, but bulk_update keeps the 100-user seed to a single query.
            previously_seeded = [u for u in users if u.username in existing]
            for user in previously_seeded:
                user.set_password(password)
            if previously_seeded:
                User.objects.bulk_update(previously_seeded, ["password"])
        return users

    def _create_labels(
        self, rng: random.Random, n_labels: int, users: list[User]
    ) -> list[Label]:
        seeded = Label.objects.filter(name__startswith=SEED_LABEL_PREFIX)
        existing = {
            (owner_id, name)
            for owner_id, name in seeded.values_list("owner_id", "name")
        }
        colors = [
            "#EF4444",
            "#F97316",
            "#F59E0B",
            "#22C55E",
            "#10B981",
            "#06B6D4",
            "#3B82F6",
            "#6366F1",
            "#A855F7",
            "#EC4899",
        ]
        labels: list[Label] = []
        missing = n_labels - seeded.count()
        i = 0
        while len(labels) < missing:
            i += 1
            name = f"{SEED_LABEL_PREFIX}{i}"
            owner = users[i % len(users)]
            if (owner.pk, name) in existing:
                continue
            labels.append(Label(name=name, color=rng.choice(colors), owner=owner))
        if labels:
            Label.objects.bulk_create(labels)
        return list(seeded.order_by("id"))

    def _create_tasks(
        self,
        rng: random.Random,
        n_tasks: int,
        users: list[User],
        labels_by_owner: dict[int, list[int]],
        batch_size: int,
    ) -> None:
        now = timezone.now()
        statuses = [s[0] for s in Task.Status.choices]
        status_weights = [45, 30, 5, 20]
        priorities = [p[0] for p in Task.Priority.choices]
        priority_weights = [10, 55, 25, 10]
        TaskLabel = Task.labels.through
        owner_ids = [u.pk for u in users]

        created = 0
        while created < n_tasks:
            count = min(batch_size, n_tasks - created)
            tasks = []
            for _ in range(count):
                owner_id = rng.choice(owner_ids)
                has_due = rng.random() < 0.75
                has_scheduled = rng.random() < 0.5
                title = _title(rng)
                task = Task(
                    title=title,
                    description=_description(rng, title),
                    owner_id=owner_id,
                    status=rng.choices(statuses, weights=status_weights)[0],
                    priority=rng.choices(priorities, weights=priority_weights)[0],
                    due_datetime=(
                        now
                        + timedelta(days=rng.randint(-7, 60), hours=rng.randint(0, 23))
                        if has_due
                        else None
                    ),
                    scheduled_date=(
                        now.date() + timedelta(days=rng.randint(0, 30))
                        if has_scheduled
                        else None
                    ),
                )
                tasks.append(task)
            Task.objects.bulk_create(tasks)

            m2m_rows = []
            for task in tasks:
                owner_labels = labels_by_owner.get(task.owner_id, [])
                if not owner_labels:
                    continue
                n_labels = rng.randint(1, min(3, len(owner_labels)))
                for label_id in rng.sample(owner_labels, n_labels):
                    m2m_rows.append(TaskLabel(task_id=task.pk, label_id=label_id))
            TaskLabel.objects.bulk_create(m2m_rows)

            created += count
            self.stdout.write(f"  Created {created}/{n_tasks} tasks...")
