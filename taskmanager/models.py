from django.contrib.auth.models import User
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.text import Truncator


STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("In Progress", "In Progress"),
    ("Completed", "Completed"),
]


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OptionQuerySet(models.QuerySet):
    """Categories and priorities come in two flavours: the shared defaults
    (user is empty, everybody sees them) and ones a person made themselves."""

    def for_user(self, user):
        return self.filter(Q(user__isnull=True) | Q(user=user)).order_by(
            F("user_id").asc(nulls_first=True), "id"
        )


class Priority(BaseModel):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)

    objects = OptionQuerySet.as_manager()

    class Meta:
        verbose_name = "Priority"
        verbose_name_plural = "Priorities"

    def __str__(self):
        return self.name


class Category(BaseModel):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)

    objects = OptionQuerySet.as_manager()

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Task(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    deadline = models.DateTimeField()

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="Pending",
    )

    # PROTECT so removing a category can never silently wipe out tasks
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    priority = models.ForeignKey(Priority, on_delete=models.PROTECT)

    class Meta:
        ordering = ["deadline"]

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return self.status != "Completed" and self.deadline < timezone.now()


class Note(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return Truncator(self.content).chars(60)


class SubTask(BaseModel):
    parent_task = models.ForeignKey(Task, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="Pending",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.title


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.user.username
