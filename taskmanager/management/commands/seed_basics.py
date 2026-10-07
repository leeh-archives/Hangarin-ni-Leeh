from django.core.management.base import BaseCommand

from taskmanager.models import Category, Priority

PRIORITIES = ["Critical", "High", "Medium", "Low", "Optional"]
CATEGORIES = ["Work", "School", "Personal", "Finance", "Projects"]


class Command(BaseCommand):
    help = "Add the starter priorities and categories (safe to run more than once)."

    def handle(self, *args, **options):
        added = 0

        for name in PRIORITIES:
            _, created = Priority.objects.get_or_create(name=name, user=None)
            added += created

        for name in CATEGORIES:
            _, created = Category.objects.get_or_create(name=name, user=None)
            added += created

        if added:
            self.stdout.write(self.style.SUCCESS(f"Added {added} starter records."))
        else:
            self.stdout.write("Priorities and categories were already there.")
