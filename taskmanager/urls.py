from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),

    path("tasks/", views.TaskListView.as_view(), name="task_list"),
    path("tasks/add/", views.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/", views.TaskDetailView.as_view(), name="task_detail"),
    path("tasks/<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task_edit"),
    path("tasks/<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task_delete"),
    path("tasks/<int:pk>/status/", views.TaskStatusView.as_view(), name="task_status"),

    path("tasks/<int:task_id>/notes/add/", views.NoteCreateView.as_view(), name="note_add"),
    path("notes/<int:pk>/edit/", views.NoteUpdateView.as_view(), name="note_edit"),
    path("notes/<int:pk>/delete/", views.NoteDeleteView.as_view(), name="note_delete"),

    path("tasks/<int:task_id>/subtasks/add/", views.SubTaskCreateView.as_view(), name="subtask_add"),
    path("subtasks/<int:pk>/edit/", views.SubTaskUpdateView.as_view(), name="subtask_edit"),
    path("subtasks/<int:pk>/toggle/", views.SubTaskToggleView.as_view(), name="subtask_toggle"),
    path("subtasks/<int:pk>/delete/", views.SubTaskDeleteView.as_view(), name="subtask_delete"),

    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_edit"),
    path("categories/<int:pk>/delete/", views.CategoryDeleteView.as_view(), name="category_delete"),

    path("priorities/", views.PriorityListView.as_view(), name="priority_list"),
    path("priorities/add/", views.PriorityCreateView.as_view(), name="priority_create"),
    path("priorities/<int:pk>/edit/", views.PriorityUpdateView.as_view(), name="priority_edit"),
    path("priorities/<int:pk>/delete/", views.PriorityDeleteView.as_view(), name="priority_delete"),

    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("offline/", views.OfflineView.as_view(), name="offline"),
]
