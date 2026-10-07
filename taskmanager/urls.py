from django.urls import path

from . import views

urlpatterns = [
    path("tasks/", views.task_list, name="task_list"),
    path("tasks/create/", views.task_create, name="task_create"),
    path("tasks/<int:task_id>/", views.task_detail, name="task_detail"),
    path("tasks/<int:task_id>/edit/", views.task_edit, name="task_edit"),
    path("tasks/<int:task_id>/delete/", views.task_delete, name="task_delete"),
    path("tasks/<int:task_id>/status/", views.task_status, name="task_status"),

    path("tasks/<int:task_id>/notes/add/", views.note_add, name="note_add"),
    path("notes/<int:pk>/delete/", views.note_delete, name="note_delete"),

    path("tasks/<int:task_id>/subtasks/add/", views.subtask_add, name="subtask_add"),
    path("subtasks/<int:pk>/toggle/", views.subtask_toggle, name="subtask_toggle"),
    path("subtasks/<int:pk>/delete/", views.subtask_delete, name="subtask_delete"),

    path("notes/<int:pk>/edit/", views.note_edit, name="note_edit"),
    path("subtasks/<int:pk>/edit/", views.subtask_edit, name="subtask_edit"),

    path("manage/<slug:kind>/", views.option_list, name="option_list"),
    path("manage/<slug:kind>/<int:pk>/edit/", views.option_edit, name="option_edit"),
    path("manage/<slug:kind>/<int:pk>/delete/", views.option_delete, name="option_delete"),

    path("offline/", views.offline, name="offline"),
    path("profile/", views.profile, name="profile"),
    path("register/", views.register, name="register"),
]
