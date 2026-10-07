from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Note, Priority, Profile, SubTask, Task


def make_task(user, **extra):
    data = {
        "user": user,
        "title": "Write report",
        "description": "First draft",
        "deadline": timezone.now() + timedelta(days=2),
        "category": Category.objects.get_or_create(name="Work")[0],
        "priority": Priority.objects.get_or_create(name="High")[0],
    }
    data.update(extra)
    return Task.objects.create(**data)


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")

    def test_profile_is_created_with_the_user(self):
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_default_status_is_pending(self):
        self.assertEqual(make_task(self.user).status, "Pending")

    def test_overdue_only_when_unfinished_and_late(self):
        late = make_task(self.user, deadline=timezone.now() - timedelta(days=1))
        self.assertTrue(late.is_overdue)

        late.status = "Completed"
        self.assertFalse(late.is_overdue)

        self.assertFalse(make_task(self.user).is_overdue)

    def test_plural_names(self):
        self.assertEqual(Category._meta.verbose_name_plural, "Categories")
        self.assertEqual(Priority._meta.verbose_name_plural, "Priorities")


class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")
        self.other = User.objects.create_user("jon", password="pass12345!")
        self.client.login(username="mara", password="pass12345!")

    def test_pages_need_login(self):
        self.client.logout()
        response = self.client.get(reverse("task_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_list_only_shows_my_tasks(self):
        make_task(self.user, title="Mine")
        make_task(self.other, title="Not mine")
        response = self.client.get(reverse("task_list"))
        self.assertContains(response, "Mine")
        self.assertNotContains(response, "Not mine")

    def test_cannot_open_someone_elses_task(self):
        theirs = make_task(self.other)
        response = self.client.get(reverse("task_detail", args=[theirs.id]))
        self.assertEqual(response.status_code, 404)

    def test_create_task(self):
        category = Category.objects.create(name="School")
        priority = Priority.objects.create(name="Low")
        response = self.client.post(reverse("task_create"), {
            "title": "Read chapter 4",
            "description": "",
            "deadline": "2030-01-15T09:30",
            "status": "Pending",
            "category": category.id,
            "priority": priority.id,
        })
        task = Task.objects.get(title="Read chapter 4")
        self.assertRedirects(response, reverse("task_detail", args=[task.id]))
        self.assertEqual(task.user, self.user)

    def test_create_task_without_deadline_shows_error(self):
        category = Category.objects.create(name="School")
        priority = Priority.objects.create(name="Low")
        response = self.client.post(reverse("task_create"), {
            "title": "No date",
            "status": "Pending",
            "category": category.id,
            "priority": priority.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "When is this due?")
        self.assertFalse(Task.objects.filter(title="No date").exists())

    def test_search_and_status_filter(self):
        make_task(self.user, title="Pay rent", status="Completed")
        make_task(self.user, title="Buy milk")
        response = self.client.get(reverse("task_list"), {"status": "Completed"})
        self.assertContains(response, "Pay rent")
        self.assertNotContains(response, "Buy milk")

        response = self.client.get(reverse("task_list"), {"search": "milk"})
        self.assertContains(response, "Buy milk")
        self.assertNotContains(response, "Pay rent")

    def test_quick_status_change(self):
        task = make_task(self.user)
        self.client.post(reverse("task_status", args=[task.id]), {"status": "Completed"})
        task.refresh_from_db()
        self.assertEqual(task.status, "Completed")

    def test_bad_status_is_ignored(self):
        task = make_task(self.user)
        self.client.post(reverse("task_status", args=[task.id]), {"status": "Nonsense"})
        task.refresh_from_db()
        self.assertEqual(task.status, "Pending")

    def test_add_note_and_subtask_then_toggle(self):
        task = make_task(self.user)
        self.client.post(reverse("note_add", args=[task.id]), {"content": "Ask Sam for the file"})
        self.client.post(reverse("subtask_add", args=[task.id]), {"title": "Outline"})
        self.assertEqual(Note.objects.filter(task=task).count(), 1)

        sub = SubTask.objects.get(parent_task=task)
        self.client.post(reverse("subtask_toggle", args=[sub.id]))
        sub.refresh_from_db()
        self.assertEqual(sub.status, "Completed")

    def test_cannot_toggle_someone_elses_subtask(self):
        theirs = make_task(self.other)
        sub = SubTask.objects.create(parent_task=theirs, title="Secret step")
        response = self.client.post(reverse("subtask_toggle", args=[sub.id]))
        self.assertEqual(response.status_code, 404)

    def test_delete_task(self):
        task = make_task(self.user)
        self.client.post(reverse("task_delete", args=[task.id]))
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_add_own_category_and_block_duplicates(self):
        Category.objects.create(name="Work")  # shared default
        self.client.post(reverse("option_list", args=["categories"]), {"name": "Errands"})
        mine = Category.objects.get(name="Errands")
        self.assertEqual(mine.user, self.user)

        self.client.post(reverse("option_list", args=["categories"]), {"name": "work"})
        self.assertEqual(Category.objects.filter(name__iexact="work").count(), 1)

    def test_rename_own_priority(self):
        item = Priority.objects.create(name="Soon", user=self.user)
        self.client.post(reverse("option_edit", args=["priorities", item.id]), {"name": "Very soon"})
        item.refresh_from_db()
        self.assertEqual(item.name, "Very soon")

    def test_shared_defaults_cannot_be_edited(self):
        shared = Category.objects.create(name="School")
        response = self.client.get(reverse("option_edit", args=["categories", shared.id]))
        self.assertEqual(response.status_code, 404)

    def test_other_users_options_are_hidden(self):
        theirs = Category.objects.create(name="Their secret list", user=self.other)
        visible = Category.objects.for_user(self.user)
        self.assertNotIn(theirs, visible)

    def test_cannot_delete_category_that_tasks_use(self):
        cat = Category.objects.create(name="Gym", user=self.user)
        make_task(self.user, category=cat)
        self.client.post(reverse("option_delete", args=["categories", cat.id]))
        self.assertTrue(Category.objects.filter(id=cat.id).exists())

    def test_delete_unused_category(self):
        cat = Category.objects.create(name="Gym", user=self.user)
        self.client.post(reverse("option_delete", args=["categories", cat.id]))
        self.assertFalse(Category.objects.filter(id=cat.id).exists())

    def test_edit_note_and_subtask(self):
        task = make_task(self.user)
        note = Note.objects.create(task=task, content="old text")
        sub = SubTask.objects.create(parent_task=task, title="old step")

        self.client.post(reverse("note_edit", args=[note.id]), {"content": "new text"})
        self.client.post(reverse("subtask_edit", args=[sub.id]), {"title": "new step", "status": "In Progress"})

        note.refresh_from_db()
        sub.refresh_from_db()
        self.assertEqual(note.content, "new text")
        self.assertEqual((sub.title, sub.status), ("new step", "In Progress"))

    def test_cannot_edit_someone_elses_note(self):
        theirs = make_task(self.other)
        note = Note.objects.create(task=theirs, content="private")
        response = self.client.get(reverse("note_edit", args=[note.id]))
        self.assertEqual(response.status_code, 404)

    def test_offline_page_works_without_login(self):
        self.client.logout()
        response = self.client.get(reverse("offline"))
        self.assertEqual(response.status_code, 200)

    def test_sign_up_logs_you_in(self):
        self.client.logout()
        response = self.client.post(reverse("register"), {
            "username": "newperson",
            "password1": "a-decent-pass-4821",
            "password2": "a-decent-pass-4821",
        })
        self.assertRedirects(response, reverse("task_list"))
        self.assertTrue(User.objects.filter(username="newperson").exists())
