from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Category, Note, Priority, Profile, SubTask, Task

DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "deadline", "status", "category", "priority"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "What do you need to get done?"}),
            "description": forms.Textarea(
                attrs={"placeholder": "Anything worth remembering (optional)", "rows": 4}
            ),
            "deadline": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format=DATETIME_FORMAT
            ),
        }
        error_messages = {
            "deadline": {"required": "When is this due? Pick a date and time."},
            "title": {"required": "Give your task a name first."},
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deadline"].input_formats = [DATETIME_FORMAT, "%Y-%m-%dT%H:%M:%S"]
        self.fields["category"].empty_label = "Choose a category"
        self.fields["priority"].empty_label = "Choose a priority"

        # only offer the shared defaults plus this person's own options
        if user is not None:
            self.fields["category"].queryset = Category.objects.for_user(user)
            self.fields["priority"].queryset = Priority.objects.for_user(user)

    def clean_title(self):
        return self.cleaned_data["title"].strip()


class OptionForm(forms.ModelForm):
    """Base for the category and priority forms."""

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        if not name:
            raise forms.ValidationError("Please type a name.")

        taken = self._meta.model.objects.for_user(self.user).filter(name__iexact=name)
        if self.instance.pk:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise forms.ValidationError(f"“{name}” already exists.")
        return name


class CategoryForm(OptionForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "e.g. Errands, Gym, Side projects"})}


class PriorityForm(OptionForm):
    class Meta:
        model = Priority
        fields = ["name"]
        widgets = {"name": forms.TextInput(attrs={"placeholder": "e.g. Urgent, Someday"})}


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"placeholder": "Jot something down...", "rows": 3}),
        }
        labels = {"content": "Note"}

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content:
            raise forms.ValidationError("A note can't be empty.")
        return content


class SubTaskForm(forms.ModelForm):
    """Quick add: just a title, the status starts as Pending."""

    class Meta:
        model = SubTask
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Add a small step..."}),
        }

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Give the step a name.")
        return title


class SubTaskEditForm(SubTaskForm):
    class Meta(SubTaskForm.Meta):
        fields = ["title", "status"]


class SignUpForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class ProfilePictureForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["profile_picture"]
