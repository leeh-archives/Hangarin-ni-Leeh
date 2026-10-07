from django.shortcuts import render, redirect
from .models import Task, Note, SubTask, Category, Priority


def task_list(request):
    tasks = Task.objects.all()

    context = {
        "tasks": tasks
    }

    return render(request, "taskmanager/task_list.html", context)

def task_detail(request, task_id):
    task = Task.objects.get(id=task_id)

    notes = Note.objects.filter(task=task)
    subtasks = SubTask.objects.filter(parent_task=task)

    context = {
        "task": task,
        "notes": notes,
        "subtasks": subtasks
    }

    return render(request, "taskmanager/task_detail.html", context)

def task_create(request):
    categories = Category.objects.all()
    priorities = Priority.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        deadline = request.POST.get("deadline")
        status = request.POST.get("status")
        category_id = request.POST.get("category")
        priority_id = request.POST.get("priority")

        Task.objects.create(
            title=title,
            description=description,
            deadline=deadline,
            status=status,
            category_id=category_id,
            priority_id=priority_id
        )

        return redirect("task_list")

    context = {
        "categories": categories,
        "priorities": priorities
    }

    return render(request, "taskmanager/task_create.html", context)

def task_edit(request, task_id):
    task = Task.objects.get(id=task_id)

    categories = Category.objects.all()
    priorities = Priority.objects.all()

    if request.method == "POST":
        task.title = request.POST.get("title")
        task.description = request.POST.get("description")
        task.deadline = request.POST.get("deadline")
        task.status = request.POST.get("status")
        task.category_id = request.POST.get("category")
        task.priority_id = request.POST.get("priority")

        task.save()

        return redirect("task_detail", task_id=task.id)

    context = {
        "task": task,
        "categories": categories,
        "priorities": priorities
    }

    return render(request, "taskmanager/task_edit.html", context)

def task_delete(request, task_id):
    task = Task.objects.get(id=task_id)

    if request.method == "POST":
        task.delete()
        return redirect("task_list")

    context = {
        "task": task
    }

    return render(request, "taskmanager/task_delete.html", context)

