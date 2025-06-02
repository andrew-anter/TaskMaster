from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("todo", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="task",
            old_name="due_date",
            new_name="due_datetime",
        ),
        migrations.AlterModelOptions(
            name="task",
            options={
                "ordering": ["status", "priority", "due_datetime"],
                "verbose_name": "To-Do Item",
                "verbose_name_plural": "To-Do Items",
            },
        ),
    ]
