from django.db import models
import uuid


# ==========================================
# Interests
# ==========================================

class Interest(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True
    )

    # ربط الاهتمام بأبعاد موديل الاهتمامات (planner/ml_service.py)
    # مثال: {"tech": 1.0, "entertainment": 0.3}
    # الأبعاد: tech, heritage, sustainability, family, food, entertainment, global
    model_weights = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "أوزان الاهتمام على أبعاد الموديل (0 إلى 1). "
            "الأبعاد: tech, heritage, sustainability, family, "
            "food, entertainment, global"
        )
    )

    def __str__(self):
        return self.name


# ==========================================
# Pavilions
# ==========================================

class Pavilion(models.Model):

    class CrowdLevel(models.TextChoices):
        LOW = "LOW", "غير مزدحم"
        MEDIUM = "MEDIUM", "ازدحام متوسط"
        HIGH = "HIGH", "مزدحم"

    name = models.CharField(
        max_length=150
    )

    country = models.CharField(
        max_length=100,
        blank=True
    )

    description = models.TextField()

    highlights = models.TextField()

    # مدة الزيارة الطبيعية للجناح
    recommended_duration = models.PositiveIntegerField(
        help_text="مدة زيارة الجناح بالدقائق"
    )

    interests = models.ManyToManyField(
        Interest,
        related_name="pavilions"
    )

    # موقع الجناح
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    # مستوى الازدحام
    crowd_level = models.CharField(
        max_length=10,
        choices=CrowdLevel.choices,
        default=CrowdLevel.LOW
    )

    is_active = models.BooleanField(
        default=True
    )

    # المدة المطلوبة لاحتساب زيارة الجناح
    # ضمن Discover & Earn
    challenge_visit_minutes = models.PositiveIntegerField(
        default=10,
        help_text="المدة المطلوبة لإكمال زيارة التحدي"
    )

    def __str__(self):
        return self.name


# ==========================================
# Visit Plan
# ==========================================

class VisitPlan(models.Model):

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # تاريخ ووقت الزيارة (من - إلى)
    visit_date = models.DateField(
        null=True,
        blank=True
    )

    start_time = models.TimeField(
        null=True,
        blank=True
    )

    end_time = models.TimeField(
        null=True,
        blank=True
    )

    is_completed = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"Plan {self.id}"


# ==========================================
# Visit Plan Items
# ==========================================

class VisitPlanItem(models.Model):

    plan = models.ForeignKey(
        VisitPlan,
        on_delete=models.CASCADE,
        related_name="items"
    )

    pavilion = models.ForeignKey(
        Pavilion,
        on_delete=models.CASCADE
    )

    # ترتيب الجناح داخل الخطة
    order = models.PositiveIntegerField()

    # المستخدم يعمل Check بعد إنهاء الجناح
    is_visited = models.BooleanField(
        default=False
    )

    visited_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return (
            f"{self.order} - "
            f"{self.pavilion.name}"
        )


# ==========================================
# Discover & Earn Challenge
# ==========================================

class Challenge(models.Model):

    # الخطة التي ظهر منها التحدي
    visit_plan = models.ForeignKey(
        VisitPlan,
        on_delete=models.CASCADE,
        related_name="challenges"
    )

    # الجناح المزدحم الذي تسبب في ظهور التحدي
    crowded_pavilion = models.ForeignKey(
        Pavilion,
        on_delete=models.CASCADE,
        related_name="crowd_challenges"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_completed = models.BooleanField(
        default=False
    )

    def __str__(self):
        return (
            f"Challenge {self.id} - "
            f"{self.crowded_pavilion.name}"
        )


# ==========================================
# Challenge Visits
# ==========================================

class ChallengeVisit(models.Model):

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name="visits"
    )

    pavilion = models.ForeignKey(
        Pavilion,
        on_delete=models.CASCADE
    )

    # ترتيب الجناح داخل التحدي
    order = models.PositiveIntegerField()

    # يبدأ عندما نتأكد أن المستخدم
    # موجود بالقرب من الجناح
    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_completed = models.BooleanField(
        default=False
    )

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return (
            f"Challenge {self.challenge.id} - "
            f"{self.pavilion.name}"
        )


# ==========================================
# Free Pass
# ==========================================

class FreePass(models.Model):

    challenge = models.OneToOneField(
        Challenge,
        on_delete=models.CASCADE,
        related_name="free_pass"
    )

    # الـ Free Pass مخصص للجناح
    # المزدحم الذي بدأ منه التحدي
    pavilion = models.ForeignKey(
        Pavilion,
        on_delete=models.CASCADE
    )

    # يستخدم لاحقًا لإنشاء QR Code
    code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_used = models.BooleanField(
        default=False
    )

    used_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return (
            f"Free Pass - "
            f"{self.pavilion.name}"
        )