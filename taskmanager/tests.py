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
        "category": Category.objects.get_or_create(name="Work", user=None)[0],
        "priority": Priority.objects.get_or_create(name="High", user=None)[0],
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


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", "mara@example.com", "pass12345!")

    def test_pages_need_login(self):
        for name in ("home", "task_list", "task_create", "category_list", "priority_list", "profile"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn("/accounts/login/", response["Location"], name)

    def test_login_page_loads(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username or email")

    def test_log_in_with_username(self):
        response = self.client.post(
            reverse("account_login"), {"login": "mara", "password": "pass12345!"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_log_in_with_email(self):
        response = self.client.post(
            reverse("account_login"), {"login": "mara@example.com", "password": "pass12345!"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_password_stays_on_the_page(self):
        response = self.client.post(
            reverse("account_login"), {"login": "mara", "password": "nope"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_sign_up_logs_you_in(self):
        response = self.client.post(reverse("account_signup"), {
            "username": "newperson",
            "email": "new@example.com",
            "password1": "a-decent-pass-4821",
            "password2": "a-decent-pass-4821",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newperson", email="new@example.com").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_sign_up_needs_an_email(self):
        self.client.post(reverse("account_signup"), {
            "username": "noemail",
            "password1": "a-decent-pass-4821",
            "password2": "a-decent-pass-4821",
        })
        self.assertFalse(User.objects.filter(username="noemail").exists())

    def test_logout_on_get(self):
        self.client.login(username="mara", password="pass12345!")
        self.client.get(reverse("account_logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_offline_page_works_without_login(self):
        response = self.client.get(reverse("offline"))
        self.assertEqual(response.status_code, 200)


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")
        self.other = User.objects.create_user("jon", password="pass12345!")
        self.client.login(username="mara", password="pass12345!")

    def test_counts_only_my_tasks(self):
        make_task(self.user, title="One")
        make_task(self.user, title="Two", status="Completed")
        make_task(self.user, title="Late", deadline=timezone.now() - timedelta(days=1))
        make_task(self.other, title="Not mine")

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

        stats = response.context["stats"]
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["pending"], 2)
        self.assertEqual(stats["overdue"], 1)

    def test_category_and_priority_counts(self):
        make_task(self.user)  # makes the shared Work / High
        Category.objects.create(name="Gym", user=self.user)
        Category.objects.create(name="Their list", user=self.other)
        Priority.objects.create(name="Someday", user=self.user)

        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["total_categories"], 2)
        self.assertEqual(response.context["total_priorities"], 2)

    def test_added_this_month_and_steps(self):
        task = make_task(self.user)
        SubTask.objects.create(parent_task=task, title="Outline")
        Note.objects.create(task=task, content="remember this")

        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["added_this_month"], 1)
        self.assertEqual(response.context["total_steps"], 1)
        self.assertEqual(response.context["total_notes"], 1)

    def test_upcoming_skips_finished_tasks_and_is_in_deadline_order(self):
        soon = make_task(self.user, title="Soon", deadline=timezone.now() + timedelta(days=1))
        later = make_task(self.user, title="Later", deadline=timezone.now() + timedelta(days=5))
        make_task(self.user, title="Done already", status="Completed")

        response = self.client.get(reverse("home"))
        self.assertEqual(list(response.context["upcoming"]), [soon, later])


class TaskViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")
        self.other = User.objects.create_user("jon", password="pass12345!")
        self.client.login(username="mara", password="pass12345!")

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

    def test_cannot_edit_or_delete_someone_elses_task(self):
        theirs = make_task(self.other)
        self.assertEqual(self.client.get(reverse("task_edit", args=[theirs.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("task_delete", args=[theirs.id])).status_code, 404)
        self.assertTrue(Task.objects.filter(id=theirs.id).exists())

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

    def test_cannot_use_someone_elses_category(self):
        theirs = Category.objects.create(name="Secret", user=self.other)
        priority = Priority.objects.create(name="Low")
        self.client.post(reverse("task_create"), {
            "title": "Sneaky",
            "deadline": "2030-01-15T09:30",
            "status": "Pending",
            "category": theirs.id,
            "priority": priority.id,
        })
        self.assertFalse(Task.objects.filter(title="Sneaky").exists())

    def test_edit_task(self):
        task = make_task(self.user, title="Old title")
        self.client.post(reverse("task_edit", args=[task.id]), {
            "title": "New title",
            "description": task.description,
            "deadline": "2030-01-15T09:30",
            "status": "In Progress",
            "category": task.category_id,
            "priority": task.priority_id,
        })
        task.refresh_from_db()
        self.assertEqual((task.title, task.status), ("New title", "In Progress"))

    def test_delete_task(self):
        task = make_task(self.user)
        response = self.client.post(reverse("task_delete", args=[task.id]))
        self.assertRedirects(response, reverse("task_list"))
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_delete_page_asks_first(self):
        task = make_task(self.user)
        response = self.client.get(reverse("task_delete", args=[task.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Task.objects.filter(id=task.id).exists())

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


class SearchSortTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")
        self.client.login(username="mara", password="pass12345!")

    def titles(self, **params):
        response = self.client.get(reverse("task_list"), params)
        self.assertEqual(response.status_code, 200)
        return [t.title for t in response.context["page_obj"]]

    def test_status_filter_and_search(self):
        make_task(self.user, title="Pay rent", status="Completed")
        make_task(self.user, title="Buy milk")

        self.assertEqual(self.titles(status="Completed"), ["Pay rent"])
        self.assertEqual(self.titles(q="milk"), ["Buy milk"])

    def test_search_looks_at_description_category_and_priority(self):
        gym = Category.objects.create(name="Gym", user=self.user)
        make_task(self.user, title="Leg day", description="squats", category=gym)
        make_task(self.user, title="Other")

        self.assertEqual(self.titles(q="squats"), ["Leg day"])
        self.assertEqual(self.titles(q="gym"), ["Leg day"])
        self.assertEqual(sorted(self.titles(q="high")), ["Leg day", "Other"])
        self.assertEqual(self.titles(q="nothing like this"), [])

    def test_sort_by_title(self):
        for name in ("Banana", "Apple", "Cherry"):
            make_task(self.user, title=name)
        self.assertEqual(self.titles(sort_by="title"), ["Apple", "Banana", "Cherry"])

    def test_sort_by_deadline_both_ways(self):
        now = timezone.now()
        make_task(self.user, title="Second", deadline=now + timedelta(days=2))
        make_task(self.user, title="First", deadline=now + timedelta(days=1))
        make_task(self.user, title="Third", deadline=now + timedelta(days=3))

        self.assertEqual(self.titles(sort_by="deadline"), ["First", "Second", "Third"])
        self.assertEqual(self.titles(sort_by="-deadline"), ["Third", "Second", "First"])

    def test_sort_by_category_name(self):
        zoo = Category.objects.create(name="Zoo", user=self.user)
        art = Category.objects.create(name="Art", user=self.user)
        make_task(self.user, title="In zoo", category=zoo)
        make_task(self.user, title="In art", category=art)
        self.assertEqual(self.titles(sort_by="category__name"), ["In art", "In zoo"])

    def test_unknown_sort_falls_back_to_deadline(self):
        make_task(self.user)
        response = self.client.get(reverse("task_list"), {"sort_by": "password"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sort_by"], "deadline")

    def test_dropdown_keeps_the_current_choice(self):
        response = self.client.get(reverse("task_list"), {"sort_by": "title"})
        self.assertContains(response, 'value="title" selected')

    def test_pagination_keeps_the_search(self):
        for i in range(10):
            make_task(self.user, title=f"Chore {i}")
        response = self.client.get(reverse("task_list"), {"q": "chore"})
        self.assertEqual(len(response.context["page_obj"]), 8)
        self.assertContains(response, "q=chore&page=2")

        response = self.client.get(reverse("task_list"), {"q": "chore", "page": 2})
        self.assertEqual(len(response.context["page_obj"]), 2)


class NoteAndStepTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")
        self.other = User.objects.create_user("jon", password="pass12345!")
        self.client.login(username="mara", password="pass12345!")

    def test_add_note_and_subtask_then_toggle(self):
        task = make_task(self.user)
        self.client.post(reverse("note_add", args=[task.id]), {"content": "Ask Sam for the file"})
        self.client.post(reverse("subtask_add", args=[task.id]), {"title": "Outline"})
        self.assertEqual(Note.objects.filter(task=task).count(), 1)

        sub = SubTask.objects.get(parent_task=task)
        self.client.post(reverse("subtask_toggle", args=[sub.id]))
        sub.refresh_from_db()
        self.assertEqual(sub.status, "Completed")

    def test_empty_note_is_not_saved(self):
        task = make_task(self.user)
        self.client.post(reverse("note_add", args=[task.id]), {"content": "   "})
        self.assertEqual(Note.objects.filter(task=task).count(), 0)

    def test_cannot_add_a_note_to_someone_elses_task(self):
        theirs = make_task(self.other)
        response = self.client.post(reverse("note_add", args=[theirs.id]), {"content": "hi"})
        self.assertEqual(response.status_code, 404)

    def test_cannot_toggle_someone_elses_subtask(self):
        theirs = make_task(self.other)
        sub = SubTask.objects.create(parent_task=theirs, title="Secret step")
        response = self.client.post(reverse("subtask_toggle", args=[sub.id]))
        self.assertEqual(response.status_code, 404)

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

    def test_delete_note_and_subtask(self):
        task = make_task(self.user)
        note = Note.objects.create(task=task, content="bye")
        sub = SubTask.objects.create(parent_task=task, title="bye")

        self.client.post(reverse("note_delete", args=[note.id]))
        self.client.post(reverse("subtask_delete", args=[sub.id]))
        self.assertFalse(Note.objects.filter(id=note.id).exists())
        self.assertFalse(SubTask.objects.filter(id=sub.id).exists())

    def test_cannot_edit_someone_elses_note(self):
        theirs = make_task(self.other)
        note = Note.objects.create(task=theirs, content="private")
        response = self.client.get(reverse("note_edit", args=[note.id]))
        self.assertEqual(response.status_code, 404)

    def test_cannot_delete_someone_elses_note(self):
        theirs = make_task(self.other)
        note = Note.objects.create(task=theirs, content="private")
        response = self.client.post(reverse("note_delete", args=[note.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Note.objects.filter(id=note.id).exists())


class CategoryPriorityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")
        self.other = User.objects.create_user("jon", password="pass12345!")
        self.client.login(username="mara", password="pass12345!")

    def test_add_own_category_and_block_duplicates(self):
        Category.objects.create(name="Work")  # shared default
        self.client.post(reverse("category_create"), {"name": "Errands"})
        mine = Category.objects.get(name="Errands")
        self.assertEqual(mine.user, self.user)

        self.client.post(reverse("category_create"), {"name": "work"})
        self.assertEqual(Category.objects.filter(name__iexact="work").count(), 1)

    def test_add_own_priority(self):
        self.client.post(reverse("priority_create"), {"name": "Someday"})
        self.assertEqual(Priority.objects.get(name="Someday").user, self.user)

    def test_rename_own_priority(self):
        item = Priority.objects.create(name="Soon", user=self.user)
        self.client.post(reverse("priority_edit", args=[item.id]), {"name": "Very soon"})
        item.refresh_from_db()
        self.assertEqual(item.name, "Very soon")

    def test_shared_defaults_cannot_be_edited_or_deleted(self):
        shared = Category.objects.create(name="School")
        self.assertEqual(self.client.get(reverse("category_edit", args=[shared.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("category_delete", args=[shared.id])).status_code, 404)
        self.assertTrue(Category.objects.filter(id=shared.id).exists())

    def test_other_users_options_are_hidden(self):
        Category.objects.create(name="Their secret list", user=self.other)
        response = self.client.get(reverse("category_list"))
        self.assertNotContains(response, "Their secret list")

    def test_cannot_delete_category_that_tasks_use(self):
        cat = Category.objects.create(name="Gym", user=self.user)
        make_task(self.user, category=cat)
        self.client.post(reverse("category_delete", args=[cat.id]))
        self.assertTrue(Category.objects.filter(id=cat.id).exists())

    def test_delete_unused_category(self):
        cat = Category.objects.create(name="Gym", user=self.user)
        response = self.client.post(reverse("category_delete", args=[cat.id]))
        self.assertRedirects(response, reverse("category_list"))
        self.assertFalse(Category.objects.filter(id=cat.id).exists())

    def test_delete_unused_priority(self):
        item = Priority.objects.create(name="Whenever", user=self.user)
        self.client.post(reverse("priority_delete", args=[item.id]))
        self.assertFalse(Priority.objects.filter(id=item.id).exists())

    def test_search_in_the_category_list(self):
        Category.objects.create(name="Gym", user=self.user)
        Category.objects.create(name="Garden", user=self.user)
        response = self.client.get(reverse("category_list"), {"q": "gym"})
        self.assertEqual([c.name for c in response.context["items"]], ["Gym"])

    def test_search_in_the_priority_list(self):
        Priority.objects.create(name="Someday", user=self.user)
        response = self.client.get(reverse("priority_list"), {"q": "some"})
        self.assertEqual([p.name for p in response.context["items"]], ["Someday"])

    def test_sort_the_category_list_by_name(self):
        Category.objects.create(name="Zoo", user=self.user)
        Category.objects.create(name="Art", user=self.user)
        response = self.client.get(reverse("category_list"), {"sort_by": "name"})
        self.assertEqual([c.name for c in response.context["items"]], ["Art", "Zoo"])

        response = self.client.get(reverse("category_list"), {"sort_by": "-name"})
        self.assertEqual([c.name for c in response.context["items"]], ["Zoo", "Art"])

    def test_defaults_come_first_by_default(self):
        Category.objects.create(name="Mine", user=self.user)
        Category.objects.create(name="Shared")
        response = self.client.get(reverse("category_list"))
        self.assertEqual([c.name for c in response.context["items"]], ["Shared", "Mine"])

    def test_list_shows_how_many_tasks_use_each_one(self):
        cat = Category.objects.create(name="Gym", user=self.user)
        make_task(self.user, category=cat)
        make_task(self.user, category=cat)
        response = self.client.get(reverse("category_list"))
        gym = [c for c in response.context["items"] if c.name == "Gym"][0]
        self.assertEqual(gym.use_count, 2)


class ProfileTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("mara", password="pass12345!")
        self.client.login(username="mara", password="pass12345!")

    def test_profile_page_shows_progress(self):
        make_task(self.user, status="Completed")
        make_task(self.user)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["percent_done"], 50)
        self.assertEqual(response.context["open_count"], 1)

    def test_posting_without_a_file_does_not_crash(self):
        response = self.client.post(reverse("profile"), {})
        self.assertRedirects(response, reverse("profile"))
