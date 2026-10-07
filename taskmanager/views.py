from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, F, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import (
    CategoryForm,
    NoteForm,
    PriorityForm,
    ProfilePictureForm,
    SubTaskEditForm,
    SubTaskForm,
    TaskForm,
)
from .models import STATUS_CHOICES, Category, Note, Priority, Profile, SubTask, Task

VALID_STATUSES = [value for value, _ in STATUS_CHOICES]

# sort_by value -> (label for the dropdown, what we really order by).
# Only keys listed here are accepted, anything else falls back to the deadline.
TASK_SORTS = {
    "deadline": ("Soonest deadline", ["deadline", "id"]),
    "-deadline": ("Latest deadline", ["-deadline", "id"]),
    "-created_at": ("Newest first", ["-created_at", "id"]),
    "title": ("Title A to Z", ["title", "id"]),
    "category__name": ("Category", ["category__name", "deadline", "id"]),
    "priority__name": ("Priority name", ["priority__name", "deadline", "id"]),
}
DEFAULT_TASK_SORT = "deadline"

OPTION_SORTS = [
    ("", "Defaults first"),
    ("name", "Name A to Z"),
    ("-name", "Name Z to A"),
    ("-created_at", "Newest first"),
]


# ------------------------------------------------------------------ small helpers

def safe_next(request, fallback):
    """Go back to the page the form was posted from, but only if it's our own site."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return fallback


class ListExtrasMixin:
    """Puts the search text and a querystring (without page=) in the context,
    so the pagination links keep the current search, filters and sorting."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop("page", None)
        context["q"] = self.request.GET.get("q", "").strip()
        context["querystring"] = params.urlencode()
        return context


def task_counts(user):
    """Numbers for the summary cards (dashboard, task list and profile)."""
    mine = Task.objects.filter(user=user)
    return {
        "total": mine.count(),
        "pending": mine.filter(status="Pending").count(),
        "in_progress": mine.filter(status="In Progress").count(),
        "completed": mine.filter(status="Completed").count(),
        "overdue": mine.exclude(status="Completed").filter(deadline__lt=timezone.now()).count(),
    }


# ------------------------------------------------------------------ dashboard

class HomePageView(LoginRequiredMixin, ListView):
    model = Task
    context_object_name = "upcoming"
    template_name = "taskmanager/home.html"

    def get_queryset(self):
        # the next few things that still need doing
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .exclude(status="Completed")
            .select_related("category", "priority")
            .order_by("deadline", "id")[:5]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["stats"] = task_counts(user)
        context["total_categories"] = Category.objects.for_user(user).count()
        context["total_priorities"] = Priority.objects.for_user(user).count()
        context["total_steps"] = SubTask.objects.filter(parent_task__user=user).count()
        context["total_notes"] = Note.objects.filter(task__user=user).count()

        today = timezone.localdate()
        context["added_this_month"] = Task.objects.filter(
            user=user,
            created_at__year=today.year,
            created_at__month=today.month,
        ).count()
        return context


# ------------------------------------------------------------------ tasks

class TaskListView(LoginRequiredMixin, ListExtrasMixin, ListView):
    model = Task
    context_object_name = "tasks"
    template_name = "taskmanager/task_list.html"
    paginate_by = 8

    def get_ordering(self):
        sort_by = self.request.GET.get("sort_by")
        if sort_by in TASK_SORTS:
            return TASK_SORTS[sort_by][1]
        return TASK_SORTS[DEFAULT_TASK_SORT][1]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .select_related("category", "priority")
            .annotate(
                subtask_total=Count("subtask", distinct=True),
                subtask_done=Count(
                    "subtask", filter=Q(subtask__status="Completed"), distinct=True
                ),
            )
        )

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
                | Q(priority__name__icontains=query)
            )

        status = self.request.GET.get("status", "")
        if status == "Overdue":
            qs = qs.exclude(status="Completed").filter(deadline__lt=timezone.now())
        elif status in VALID_STATUSES:
            qs = qs.filter(status=status)

        category = self.request.GET.get("category", "")
        if category.isdigit():
            qs = qs.filter(category_id=int(category))

        priority = self.request.GET.get("priority", "")
        if priority.isdigit():
            qs = qs.filter(priority_id=int(priority))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        get = self.request.GET

        status = get.get("status", "")
        if status != "Overdue" and status not in VALID_STATUSES:
            status = ""
        category = get.get("category", "")
        category = category if category.isdigit() else ""
        priority = get.get("priority", "")
        priority = priority if priority.isdigit() else ""

        sort_by = get.get("sort_by")
        if sort_by not in TASK_SORTS:
            sort_by = DEFAULT_TASK_SORT

        # progress bar for each card on this page
        for task in context["page_obj"]:
            if task.subtask_total:
                task.progress = int(task.subtask_done * 100 / task.subtask_total)
            else:
                task.progress = None

        context.update({
            "stats": task_counts(user),
            "status": status,
            "category": category,
            "priority": priority,
            "sort_by": sort_by,
            "sort_options": [(key, value[0]) for key, value in TASK_SORTS.items()],
            "categories": Category.objects.for_user(user),
            "priorities": Priority.objects.for_user(user),
            "filtering": bool(context["q"] or status or category or priority),
        })
        return context


class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = "task"
    template_name = "taskmanager/task_detail.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(user=self.request.user)
            .select_related("category", "priority")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subtasks = list(self.object.subtask_set.all())
        done = sum(1 for s in subtasks if s.status == "Completed")

        context.update({
            "notes": self.object.note_set.all(),
            "subtasks": subtasks,
            "subtasks_done": done,
            "progress": int(done * 100 / len(subtasks)) if subtasks else None,
            "note_form": NoteForm(),
            "subtask_form": SubTaskForm(),
            "status_options": VALID_STATUSES,
        })
        return context


class TaskFormMixin(LoginRequiredMixin):
    """What the add and edit pages have in common."""
    model = Task
    form_class = TaskForm
    template_name = "taskmanager/task_form.html"

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("task_detail", args=[self.object.pk])


class TaskCreateView(TaskFormMixin, CreateView):
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"“{self.object.title}” was added.")
        return response


class TaskUpdateView(TaskFormMixin, UpdateView):
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Your changes were saved.")
        return response


class TaskDeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = "task"
    template_name = "taskmanager/task_delete.html"
    success_url = reverse_lazy("task_list")

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def form_valid(self, form):
        title = self.object.title
        response = super().form_valid(form)
        messages.success(self.request, f"“{title}” was deleted.")
        return response


class TaskStatusView(LoginRequiredMixin, View):
    """Quick status change from the list or the detail page. POST only."""

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk, user=request.user)
        new_status = request.POST.get("status")

        if new_status in VALID_STATUSES:
            task.status = new_status
            task.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Marked as {new_status.lower()}.")
        else:
            messages.error(request, "That isn't a valid status.")

        return redirect(safe_next(request, reverse("task_detail", args=[task.pk])))


# ------------------------------------------------------------------ notes

class NoteCreateView(LoginRequiredMixin, CreateView):
    """The note box on the task page posts here, there's no page of its own."""
    model = Note
    form_class = NoteForm
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=kwargs["task_id"], user=request.user)
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("task_detail", args=[self.task.pk])

    def form_valid(self, form):
        form.instance.task = self.task
        messages.success(self.request, "Note added.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "A note can't be empty.")
        return HttpResponseRedirect(self.get_success_url())


class NoteUpdateView(LoginRequiredMixin, UpdateView):
    model = Note
    form_class = NoteForm
    template_name = "taskmanager/edit_form.html"

    def get_queryset(self):
        return Note.objects.filter(task__user=self.request.user).select_related("task")

    def get_success_url(self):
        return reverse("task_detail", args=[self.object.task_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "heading": "Edit note",
            "subheading": f"On “{self.object.task.title}”",
            "button": "Save note",
            "back_url": self.get_success_url(),
            "back_label": "Back to task",
        })
        return context

    def form_valid(self, form):
        messages.success(self.request, "Note updated.")
        return super().form_valid(form)


class NoteDeleteView(LoginRequiredMixin, DeleteView):
    model = Note
    http_method_names = ["post"]

    def get_queryset(self):
        return Note.objects.filter(task__user=self.request.user)

    def get_success_url(self):
        return reverse("task_detail", args=[self.object.task_id])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Note removed.")
        return response


# ------------------------------------------------------------------ steps (subtasks)

class SubTaskCreateView(LoginRequiredMixin, CreateView):
    model = SubTask
    form_class = SubTaskForm
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=kwargs["task_id"], user=request.user)
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("task_detail", args=[self.task.pk])

    def form_valid(self, form):
        form.instance.parent_task = self.task
        messages.success(self.request, "Step added.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Give the step a name first.")
        return HttpResponseRedirect(self.get_success_url())


class SubTaskUpdateView(LoginRequiredMixin, UpdateView):
    model = SubTask
    form_class = SubTaskEditForm
    template_name = "taskmanager/edit_form.html"

    def get_queryset(self):
        return SubTask.objects.filter(parent_task__user=self.request.user).select_related(
            "parent_task"
        )

    def get_success_url(self):
        return reverse("task_detail", args=[self.object.parent_task_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "heading": "Edit step",
            "subheading": f"Part of “{self.object.parent_task.title}”",
            "button": "Save step",
            "back_url": self.get_success_url(),
            "back_label": "Back to task",
        })
        return context

    def form_valid(self, form):
        messages.success(self.request, "Step updated.")
        return super().form_valid(form)


class SubTaskDeleteView(LoginRequiredMixin, DeleteView):
    model = SubTask
    http_method_names = ["post"]

    def get_queryset(self):
        return SubTask.objects.filter(parent_task__user=self.request.user)

    def get_success_url(self):
        return reverse("task_detail", args=[self.object.parent_task_id])

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Step removed.")
        return response


class SubTaskToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        sub = get_object_or_404(SubTask, pk=pk, parent_task__user=request.user)
        sub.status = "Pending" if sub.status == "Completed" else "Completed"
        sub.save(update_fields=["status", "updated_at"])
        return redirect("task_detail", pk=sub.parent_task_id)


# ------------------------------------------------------------------ categories and priorities
# These two work the same way, so the behaviour lives in the Option* classes
# and the small CategoryInfo / PriorityInfo classes only say what's different.
# (The form is called edit_form_class on purpose: DeleteView has its own form_class.)

class CategoryInfo:
    model = Category
    edit_form_class = CategoryForm
    label = "category"
    label_plural = "categories"
    title = "Categories"
    icon = "🌷"
    intro = "Group your tasks the way you think about them."
    task_field = "category"
    list_url = "category_list"
    add_url = "category_create"
    edit_url = "category_edit"
    delete_url = "category_delete"


class PriorityInfo:
    model = Priority
    edit_form_class = PriorityForm
    label = "priority"
    label_plural = "priorities"
    title = "Priorities"
    icon = "⭐"
    intro = "Decide how much each task matters."
    task_field = "priority"
    list_url = "priority_list"
    add_url = "priority_create"
    edit_url = "priority_edit"
    delete_url = "priority_delete"


class OptionListView(LoginRequiredMixin, ListExtrasMixin, ListView):
    template_name = "taskmanager/option_list.html"
    context_object_name = "items"
    paginate_by = 10

    def get_ordering(self):
        sort_by = self.request.GET.get("sort_by")
        if sort_by in [key for key, _ in OPTION_SORTS if key]:
            return [sort_by, "id"]
        # shared defaults first, then your own, oldest first
        return [F("user_id").asc(nulls_first=True), "id"]

    def get_queryset(self):
        user = self.request.user
        qs = (
            super()
            .get_queryset()
            .filter(Q(user__isnull=True) | Q(user=user))
            .annotate(use_count=Count("task", filter=Q(task__user=user)))
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(name__icontains=query)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sort_by = self.request.GET.get("sort_by", "")
        context.update({
            "info": self,
            "sort_by": sort_by if sort_by in dict(OPTION_SORTS) else "",
            "sort_options": OPTION_SORTS,
        })
        return context


class OptionFormMixin(LoginRequiredMixin):
    template_name = "taskmanager/edit_form.html"

    def get_form_class(self):
        return self.edit_form_class

    def get_queryset(self):
        # only your own entries can be changed, the shared defaults are read-only
        return self.model.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse(self.list_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "back_url": reverse(self.list_url),
            "back_label": f"Back to {self.label_plural}",
        })
        return context


class OptionCreateView(OptionFormMixin, CreateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "heading": f"Add a {self.label}",
            "subheading": "Only you will see it.",
            "button": "Add",
        })
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, f"Added “{self.object.name}”.")
        return response


class OptionUpdateView(OptionFormMixin, UpdateView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "heading": f"Rename {self.label}",
            "subheading": "Tasks that use it will pick up the new name.",
            "button": "Save",
        })
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Saved.")
        return response


class OptionDeleteView(LoginRequiredMixin, DeleteView):
    template_name = "taskmanager/option_delete.html"
    context_object_name = "item"

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse(self.list_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["info"] = self
        context["in_use"] = Task.objects.filter(**{self.task_field: self.object}).count()
        return context

    def form_valid(self, form):
        in_use = Task.objects.filter(**{self.task_field: self.object}).count()
        if in_use:
            # tasks use PROTECT, so the delete would fail anyway
            messages.error(
                self.request,
                f"“{self.object.name}” is still used by {in_use} "
                f"task{'s' if in_use != 1 else ''}. "
                f"Switch those tasks to another {self.label} first.",
            )
            return HttpResponseRedirect(self.get_success_url())

        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f"Deleted “{name}”.")
        return response


class CategoryListView(CategoryInfo, OptionListView):
    pass


class CategoryCreateView(CategoryInfo, OptionCreateView):
    pass


class CategoryUpdateView(CategoryInfo, OptionUpdateView):
    pass


class CategoryDeleteView(CategoryInfo, OptionDeleteView):
    pass


class PriorityListView(PriorityInfo, OptionListView):
    pass


class PriorityCreateView(PriorityInfo, OptionCreateView):
    pass


class PriorityUpdateView(PriorityInfo, OptionUpdateView):
    pass


class PriorityDeleteView(PriorityInfo, OptionDeleteView):
    pass


# ------------------------------------------------------------------ profile and offline page

class ProfileView(LoginRequiredMixin, UpdateView):
    """Shows your numbers. The picture form posts back to this same page."""
    model = Profile
    form_class = ProfilePictureForm
    template_name = "taskmanager/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = task_counts(self.request.user)
        total = stats["total"]
        context.update({
            "task_count": total,
            "completed_count": stats["completed"],
            "open_count": total - stats["completed"],
            "percent_done": int(stats["completed"] * 100 / total) if total else 0,
        })
        return context

    def form_valid(self, form):
        if not self.request.FILES.get("profile_picture"):
            return self.form_invalid(form)
        response = super().form_valid(form)
        messages.success(self.request, "Profile picture updated.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "That file didn't work. Try a JPG or PNG image.")
        return HttpResponseRedirect(self.success_url)


class OfflineView(TemplateView):
    """The service worker shows this when there's no connection."""
    template_name = "taskmanager/offline.html"
