from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    CategoryForm,
    NoteForm,
    PriorityForm,
    ProfilePictureForm,
    SignUpForm,
    SubTaskEditForm,
    SubTaskForm,
    TaskForm,
)
from .models import STATUS_CHOICES, Category, Note, Priority, Profile, SubTask, Task

VALID_STATUSES = [value for value, _ in STATUS_CHOICES]

SORT_OPTIONS = {
    "deadline": ("deadline", "Soonest deadline"),
    "-deadline": ("-deadline", "Latest deadline"),
    "-created_at": ("-created_at", "Newest first"),
    "title": ("title", "Title A to Z"),
}


def _safe_next(request, fallback):
    """Go back to wherever the form was posted from, but only if it's our own site."""
    target = request.POST.get("next", "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return fallback


# ------------------------------------------------------------------ tasks

@login_required
def task_list(request):
    Profile.objects.get_or_create(user=request.user)

    mine = Task.objects.filter(user=request.user)

    # the little summary cards always count everything, not just the filtered view
    now = timezone.now()
    stats = {
        "total": mine.count(),
        "pending": mine.filter(status="Pending").count(),
        "in_progress": mine.filter(status="In Progress").count(),
        "completed": mine.filter(status="Completed").count(),
        "overdue": mine.exclude(status="Completed").filter(deadline__lt=now).count(),
    }

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")
    category = request.GET.get("category", "")
    priority = request.GET.get("priority", "")
    sort = request.GET.get("sort", "deadline")
    if sort not in SORT_OPTIONS:
        sort = "deadline"

    tasks = mine.select_related("category", "priority").annotate(
        subtask_total=Count("subtask", distinct=True),
        subtask_done=Count("subtask", filter=Q(subtask__status="Completed"), distinct=True),
    )

    if search:
        tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))

    if status == "Overdue":
        tasks = tasks.exclude(status="Completed").filter(deadline__lt=now)
    elif status in VALID_STATUSES:
        tasks = tasks.filter(status=status)
    else:
        status = ""

    if category.isdigit():
        tasks = tasks.filter(category_id=int(category))
    else:
        category = ""

    if priority.isdigit():
        tasks = tasks.filter(priority_id=int(priority))
    else:
        priority = ""

    tasks = tasks.order_by(SORT_OPTIONS[sort][0], "id")

    page_obj = Paginator(tasks, 8).get_page(request.GET.get("page"))
    for t in page_obj:
        t.progress = int(t.subtask_done * 100 / t.subtask_total) if t.subtask_total else None

    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "stats": stats,
        "search": search,
        "status": status,
        "category": category,
        "priority": priority,
        "sort": sort,
        "sort_options": [(key, label) for key, (_, label) in SORT_OPTIONS.items()],
        "status_options": VALID_STATUSES,
        "categories": Category.objects.for_user(request.user),
        "priorities": Priority.objects.for_user(request.user),
        "querystring": params.urlencode(),
        "filtering": bool(search or status or category or priority),
    }
    return render(request, "taskmanager/task_list.html", context)


@login_required
def task_detail(request, task_id):
    task = get_object_or_404(
        Task.objects.select_related("category", "priority"), id=task_id, user=request.user
    )
    subtasks = list(task.subtask_set.all())
    done = sum(1 for s in subtasks if s.status == "Completed")

    context = {
        "task": task,
        "notes": task.note_set.all(),
        "subtasks": subtasks,
        "progress": int(done * 100 / len(subtasks)) if subtasks else None,
        "subtasks_done": done,
        "note_form": NoteForm(),
        "subtask_form": SubTaskForm(),
        "status_options": VALID_STATUSES,
    }
    return render(request, "taskmanager/task_detail.html", context)


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, f"“{task.title}” was added.")
            return redirect("task_detail", task_id=task.id)
    else:
        form = TaskForm(user=request.user)

    return render(
        request,
        "taskmanager/task_form.html",
        {"form": form, "heading": "Add a new task", "subheading": "What's on your plate?",
         "button": "Create task"},
    )


@login_required
def task_edit(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your changes were saved.")
            return redirect("task_detail", task_id=task.id)
    else:
        form = TaskForm(instance=task, user=request.user)

    return render(
        request,
        "taskmanager/task_form.html",
        {"form": form, "task": task, "heading": "Edit task",
         "subheading": "Change whatever you need.", "button": "Save changes"},
    )


@login_required
def task_delete(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)

    if request.method == "POST":
        title = task.title
        task.delete()
        messages.success(request, f"“{title}” was deleted.")
        return redirect("task_list")

    return render(request, "taskmanager/task_delete.html", {"task": task})


@login_required
@require_POST
def task_status(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    new_status = request.POST.get("status")

    if new_status in VALID_STATUSES:
        task.status = new_status
        task.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Marked as {new_status.lower()}.")
    else:
        messages.error(request, "That isn't a valid status.")

    return redirect(_safe_next(request, reverse("task_detail", args=[task.id])))


# ------------------------------------------------------------------ notes

@login_required
@require_POST
def note_add(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    form = NoteForm(request.POST)

    if form.is_valid():
        note = form.save(commit=False)
        note.task = task
        note.save()
        messages.success(request, "Note added.")
    else:
        messages.error(request, "A note can't be empty.")

    return redirect("task_detail", task_id=task.id)


@login_required
@require_POST
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk, task__user=request.user)
    task_id = note.task_id
    note.delete()
    messages.success(request, "Note removed.")
    return redirect("task_detail", task_id=task_id)


@login_required
def note_edit(request, pk):
    note = get_object_or_404(Note, pk=pk, task__user=request.user)

    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, "Note updated.")
            return redirect("task_detail", task_id=note.task_id)
    else:
        form = NoteForm(instance=note)

    return render(request, "taskmanager/edit_form.html", {
        "form": form,
        "heading": "Edit note",
        "subheading": f"On “{note.task.title}”",
        "button": "Save note",
        "back_url": reverse("task_detail", args=[note.task_id]),
        "back_label": "Back to task",
    })


# ------------------------------------------------------------------ subtasks

@login_required
@require_POST
def subtask_add(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    form = SubTaskForm(request.POST)

    if form.is_valid():
        sub = form.save(commit=False)
        sub.parent_task = task
        sub.save()
        messages.success(request, "Step added.")
    else:
        messages.error(request, "Give the step a name first.")

    return redirect("task_detail", task_id=task.id)


@login_required
def subtask_edit(request, pk):
    sub = get_object_or_404(SubTask, pk=pk, parent_task__user=request.user)

    if request.method == "POST":
        form = SubTaskEditForm(request.POST, instance=sub)
        if form.is_valid():
            form.save()
            messages.success(request, "Step updated.")
            return redirect("task_detail", task_id=sub.parent_task_id)
    else:
        form = SubTaskEditForm(instance=sub)

    return render(request, "taskmanager/edit_form.html", {
        "form": form,
        "heading": "Edit step",
        "subheading": f"Part of “{sub.parent_task.title}”",
        "button": "Save step",
        "back_url": reverse("task_detail", args=[sub.parent_task_id]),
        "back_label": "Back to task",
    })


@login_required
@require_POST
def subtask_toggle(request, pk):
    sub = get_object_or_404(SubTask, pk=pk, parent_task__user=request.user)
    sub.status = "Pending" if sub.status == "Completed" else "Completed"
    sub.save(update_fields=["status", "updated_at"])
    return redirect("task_detail", task_id=sub.parent_task_id)


@login_required
@require_POST
def subtask_delete(request, pk):
    sub = get_object_or_404(SubTask, pk=pk, parent_task__user=request.user)
    task_id = sub.parent_task_id
    sub.delete()
    messages.success(request, "Step removed.")
    return redirect("task_detail", task_id=task_id)


# ------------------------------------------------------------------ categories and priorities

OPTION_KINDS = {
    "categories": {
        "model": Category,
        "form": CategoryForm,
        "title": "Categories",
        "one": "category",
        "icon": "🌷",
        "intro": "Group your tasks the way you think about them.",
        "task_field": "category",
    },
    "priorities": {
        "model": Priority,
        "form": PriorityForm,
        "title": "Priorities",
        "one": "priority",
        "icon": "⭐",
        "intro": "Decide how much each task matters.",
        "task_field": "priority",
    },
}


def _option_config(kind):
    config = OPTION_KINDS.get(kind)
    if config is None:
        raise Http404("Unknown list")
    return config


@login_required
def option_list(request, kind):
    config = _option_config(kind)
    model, form_class = config["model"], config["form"]

    if request.method == "POST":
        form = form_class(request.POST, user=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.save()
            messages.success(request, f"Added “{item.name}”.")
            return redirect("option_list", kind=kind)
    else:
        form = form_class(user=request.user)

    items = model.objects.for_user(request.user).annotate(
        use_count=Count("task", filter=Q(task__user=request.user))
    )

    return render(request, "taskmanager/option_list.html", {
        "kind": kind,
        "config": config,
        "form": form,
        "items": items,
    })


@login_required
def option_edit(request, kind, pk):
    config = _option_config(kind)
    # only your own entries can be changed; the shared defaults are read-only
    item = get_object_or_404(config["model"], pk=pk, user=request.user)

    if request.method == "POST":
        form = config["form"](request.POST, instance=item, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved.")
            return redirect("option_list", kind=kind)
    else:
        form = config["form"](instance=item, user=request.user)

    return render(request, "taskmanager/edit_form.html", {
        "form": form,
        "heading": f"Rename {config['one']}",
        "subheading": "Tasks that use it will pick up the new name.",
        "button": "Save",
        "back_url": reverse("option_list", args=[kind]),
        "back_label": f"Back to {config['title'].lower()}",
    })


@login_required
@require_POST
def option_delete(request, kind, pk):
    config = _option_config(kind)
    item = get_object_or_404(config["model"], pk=pk, user=request.user)

    in_use = Task.objects.filter(**{config["task_field"]: item}).count()
    if in_use:
        messages.error(
            request,
            f"“{item.name}” is still used by {in_use} task{'s' if in_use != 1 else ''}. "
            f"Switch those tasks to another {config['one']} first.",
        )
    else:
        name = item.name
        item.delete()
        messages.success(request, f"Deleted “{name}”.")

    return redirect("option_list", kind=kind)


# ------------------------------------------------------------------ accounts

@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfilePictureForm(request.POST, request.FILES, instance=profile_obj)
        if form.is_valid() and request.FILES.get("profile_picture"):
            form.save()
            messages.success(request, "Profile picture updated.")
        else:
            messages.error(request, "That file didn't work. Try a JPG or PNG image.")
        return redirect("profile")

    mine = Task.objects.filter(user=request.user)
    total = mine.count()
    completed = mine.filter(status="Completed").count()

    context = {
        "profile": profile_obj,
        "task_count": total,
        "completed_count": completed,
        "open_count": total - completed,
        "percent_done": int(completed * 100 / total) if total else 0,
    }
    return render(request, "taskmanager/profile.html", context)


def register(request):
    if request.user.is_authenticated:
        return redirect("task_list")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            # several login backends are active now, so say which one to use
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Welcome to Hangarin! Add your first task to get started.")
            return redirect("task_list")
    else:
        form = SignUpForm()

    return render(request, "registration/register.html", {"form": form})


def offline(request):
    """Shown by the service worker when there's no connection."""
    return render(request, "taskmanager/offline.html")
