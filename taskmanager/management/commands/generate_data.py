from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from faker import Faker

from taskmanager.models import Category, Note, Priority, SubTask, Task

STATUSES = ["Pending", "In Progress", "Completed"]

# faker's default sentences are latin filler, so we feed it everyday words
# to make the demo tasks read like something a person might actually write
WORDS = [
    "finish", "submit", "review", "prepare", "call", "email", "buy", "pay",
    "update", "plan", "clean", "schedule", "organize", "write", "check",
    "report", "assignment", "groceries", "meeting", "budget", "bills",
    "project", "presentation", "laundry", "appointment", "notes", "slides",
    "draft", "proposal", "reading", "exam", "tickets", "receipts", "deadline",
    "team", "family", "weekend", "tomorrow", "today", "before", "after",
    "the", "for", "and", "with", "my", "this", "next",
]


class Command(BaseCommand):
    help = "Fill the database with fake tasks, notes and subtasks using Faker."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=10,
                            help="how many tasks to create (default 10)")
        parser.add_argument("--user", type=str, default=None,
                            help="username that will own the tasks (default: first account)")

    def handle(self, *args, **options):
        if options["user"]:
            try:
                owner = User.objects.get(username=options["user"])
            except User.DoesNotExist:
                raise CommandError(f"There's no user called '{options['user']}'.")
        else:
            owner = User.objects.order_by("id").first()
            if owner is None:
                raise CommandError(
                    "No accounts yet. Run `python manage.py createsuperuser` first."
                )

        # tasks need a category and a priority, so make sure they exist
        if not Priority.objects.exists() or not Category.objects.exists():
            call_command("seed_basics")

        fake = Faker()
        categories = list(Category.objects.for_user(owner))
        priorities = list(Priority.objects.for_user(owner))

        for _ in range(options["count"]):
            task = Task.objects.create(
                user=owner,
                title=fake.sentence(nb_words=5, ext_word_list=WORDS).capitalize(),
                description=fake.paragraph(nb_sentences=3, ext_word_list=WORDS)[:500],
                deadline=timezone.make_aware(fake.date_time_this_month()),
                status=fake.random_element(elements=STATUSES),
                category=fake.random_element(elements=categories),
                priority=fake.random_element(elements=priorities),
            )

            for _ in range(2):
                Note.objects.create(
                    task=task,
                    content=fake.paragraph(nb_sentences=2, ext_word_list=WORDS),
                )

            for _ in range(3):
                SubTask.objects.create(
                    parent_task=task,
                    title=fake.sentence(nb_words=5, ext_word_list=WORDS).capitalize(),
                    status=fake.random_element(elements=STATUSES),
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {options['count']} tasks for {owner.username}."
            )
        )
