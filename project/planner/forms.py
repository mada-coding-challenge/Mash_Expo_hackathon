from datetime import date, datetime

from django import forms

from .models import Interest, Pavilion


class VisitPlanForm(forms.Form):

    # الخطوة 1: وقت الزيارة (تُرسل كحقول مخفية من واجهة الوقت)
    visit_date = forms.DateField(
        required=False,
        widget=forms.HiddenInput
    )

    start_time = forms.TimeField(
        widget=forms.HiddenInput,
        input_formats=["%H:%M"],
        error_messages={"required": "اختر وقت الوصول."}
    )

    end_time = forms.TimeField(
        widget=forms.HiddenInput,
        input_formats=["%H:%M"],
        error_messages={"required": "اختر وقت المغادرة."}
    )

    # نوع المجموعة (من مدخلات موديل الاهتمامات)
    group_type = forms.ChoiceField(
        choices=[
            ("solo", "بمفردي"),
            ("couple", "شخصان"),
            ("family", "عائلة"),
            ("friends", "أصدقاء"),
        ],
        initial="solo",
        required=False,
        widget=forms.RadioSelect,
        label="مع من ستزور؟"
    )

    # الخطوة 2: الاهتمامات
    interests = forms.ModelMultipleChoiceField(
        queryset=Interest.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="اختر اهتماماتك",
        error_messages={"required": "اختر اهتمامًا واحدًا على الأقل."}
    )

    # الخطوة 3: الأجنحة المفضلة
    favorite_pavilions = forms.ModelMultipleChoiceField(
        queryset=Pavilion.objects.filter(
            is_active=True
        ).prefetch_related("interests"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="اختر الأجنحة التي تفضل زيارتها"
    )

    def clean(self):

        cleaned = super().clean()

        start = cleaned.get("start_time")
        end = cleaned.get("end_time")

        if start and end:

            day = date.today()

            minutes = int(
                (
                    datetime.combine(day, end)
                    - datetime.combine(day, start)
                ).total_seconds() // 60
            )

            if minutes < 30:
                raise forms.ValidationError(
                    "يجب أن تكون مدة الزيارة 30 دقيقة على الأقل، "
                    "ووقت المغادرة بعد الوصول."
                )

            if minutes > 12 * 60:
                raise forms.ValidationError(
                    "الحد الأقصى لمدة الزيارة 12 ساعة."
                )

            # تستخدمها view بدل visit_duration القديمة
            cleaned["available_minutes"] = minutes

        return cleaned
