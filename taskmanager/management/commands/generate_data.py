from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from taskmanager.models import Task, Note, SubTask, Category, Priority


class Command(BaseCommand):
    help = "Generate fake data for Hangarin"

    def handle(self, *args, **kwargs):
        fake = Faker()

        categories = Category.objects.all()
        priorities = Priority.objects.all()

        for i in range(10):
            task = Task.objects.create(
                title=fake.sentence(nb_words=5),
                description=fake.paragraph(nb_sentences=3),
                deadline=timezone.make_aware(fake.date_time_this_month()),
                status=fake.random_element(
                    elements=["Pending", "In Progress", "Completed"]
                ),
                category=fake.random_element(elements=categories),
                priority=fake.random_element(elements=priorities)
            )

            for j in range(2):
                Note.objects.create(
                    task=task,
                    content=fake.paragraph(nb_sentences=2)
                )

            for j in range(3):
                SubTask.objects.create(
                    parent_task=task,
                    title=fake.sentence(nb_words=5),
                    status=fake.random_element(
                        elements=["Pending", "In Progress", "Completed"]
                    )
                )

        self.stdout.write(
            self.style.SUCCESS("Fake data generated successfully!")
        )