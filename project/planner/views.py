from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import VisitPlanForm

from .models import (
    Pavilion,
    VisitPlan,
    VisitPlanItem,
    Challenge,
    ChallengeVisit,
    FreePass,
)

import base64
from io import BytesIO

import qrcode

from django.contrib import messages

from .ml_service import score_pavilions

from .services import (
    create_smart_visit_plan,
    get_challenge_pavilions,
    is_user_near_pavilion,
    build_schedule,
    format_time_range,
    duration_label,
)

from django.conf import settings
# ==========================================
# Create Visit Plan
# ==========================================

def create_plan(request):

    if request.method == "POST":

        form = VisitPlanForm(request.POST)

        if form.is_valid():

            selected_interests = form.cleaned_data[
                "interests"
            ]

            favorite_pavilions = form.cleaned_data[
                "favorite_pavilions"
            ]

            available_minutes = form.cleaned_data[
                "available_minutes"
            ]

            group_type = (
                form.cleaned_data.get("group_type") or "solo"
            )

            # Get active pavilions
            pavilions = list(
                Pavilion.objects
                .filter(is_active=True)
                .prefetch_related("interests")
            )

            chosen_pavilions = list(
                favorite_pavilions.prefetch_related("interests")
            )

            # 1) موديل الاهتمامات يعطي درجة لكل جناح
            #    (إذا تعذّر تحميل الموديل يُستخدم التطابق المباشر)
            scores, reasons, _profile = score_pavilions(
                pavilions=pavilions,
                selected_interests=selected_interests,
                chosen_pavilions=chosen_pavilions,
                available_minutes=available_minutes,
                group_type=group_type,
            )

            # 2) ترتيب الخطة حسب الوقت والمسافات
            visit_plan = create_smart_visit_plan(
                pavilions=pavilions,
                scores=scores,
                reasons=reasons,
                must_visit_ids=[p.id for p in chosen_pavilions],
                available_minutes=available_minutes,
            )

            if visit_plan["skipped"]:
                messages.warning(
                    request,
                    "لم يتسع الوقت لـ: "
                    + "، ".join(p.name for p in visit_plan["skipped"])
                )

            # Save plan
            db_plan = VisitPlan.objects.create(
                visit_date=(
                    form.cleaned_data["visit_date"]
                    or timezone.localdate()
                ),
                start_time=form.cleaned_data["start_time"],
                end_time=form.cleaned_data["end_time"],
            )

            # Save plan items
            for index, item in enumerate(
                visit_plan["items"],
                start=1
            ):

                VisitPlanItem.objects.create(
                    plan=db_plan,
                    pavilion=item["pavilion"],
                    order=index
                )

            return redirect(
                "plan_detail",
                plan_id=db_plan.id
            )

    else:

        form = VisitPlanForm()

    return render(
        request,
        "planner/create_plan.html",
        {
            "form": form
        }
    )


# ==========================================
# Plan Details
# ==========================================

def plan_detail(request, plan_id):

    plan = get_object_or_404(
        VisitPlan,
        id=plan_id
    )

    items = list(
        plan.items.select_related("pavilion")
    )

    # First pavilion not visited yet
    next_item = next(
        (item for item in items if not item.is_visited),
        None
    )

    # كل تصاريح المسار السريع الخاصة بهذه الخطة
    passes = list(
        FreePass.objects.filter(
            challenge__visit_plan=plan
        )
    )

    pass_pavilion_ids = {p.pavilion_id for p in passes}

    # تصريح غير مستخدم لكل جناح
    active_passes = {
        p.pavilion_id: p
        for p in passes
        if not p.is_used
    }

    show_challenge = False

    # Check if next pavilion is crowded
    # (ولا يظهر التحدي إذا كسب المستخدم تصريحًا لهذا الجناح)
    if next_item:

        show_challenge = (
            next_item.pavilion.crowd_level
            == Pavilion.CrowdLevel.HIGH
            and next_item.pavilion_id not in pass_pavilion_ids
        )

    rows = build_schedule(plan, items)

    for row in rows:
        row["free_pass"] = active_passes.get(
            row["item"].pavilion_id
        )

    done_count = sum(1 for item in items if item.is_visited)

    return render(
        request,
        "planner/plan_detail.html",
        {
            "plan": plan,
            "items": items,
            "rows": rows,
            "next_item": next_item,
            "show_challenge": show_challenge,
            "done_count": done_count,
            "total_count": len(items),
            "progress_percent": (
                round(done_count * 100 / len(items))
                if items else 0
            ),
            "time_range": format_time_range(
                plan.start_time,
                plan.end_time
            ),
            "duration_text": (
                duration_label(
                    (plan.end_time.hour * 60 + plan.end_time.minute)
                    - (plan.start_time.hour * 60 + plan.start_time.minute)
                )
                if plan.start_time and plan.end_time
                else ""
            ),
            "active_pass": (
                active_passes.get(next_item.pavilion_id)
                if next_item else None
            ),
        }
    )


# ==========================================
# Complete Pavilion Visit
# ==========================================

@require_POST
def complete_plan_item(request, item_id):

    item = get_object_or_404(
        VisitPlanItem,
        id=item_id
    )

    # Get current pavilion
    next_item = item.plan.items.filter(
        is_visited=False
    ).first()

    # Prevent checking future pavilions
    if not next_item or next_item.id != item.id:

        return redirect(
            "plan_detail",
            plan_id=item.plan.id
        )

    # Mark pavilion as visited
    item.is_visited = True
    item.visited_at = timezone.now()

    item.save(
        update_fields=[
            "is_visited",
            "visited_at"
        ]
    )

    # Check if all pavilions are completed
    has_remaining_items = (
        item.plan.items
        .filter(is_visited=False)
        .exists()
    )

    if not has_remaining_items:

        item.plan.is_completed = True

        item.plan.save(
            update_fields=[
                "is_completed"
            ]
        )

    return redirect(
        "plan_detail",
        plan_id=item.plan.id
    )


# ==========================================
# Start Discover & Earn Challenge
# ==========================================

@require_POST
def start_challenge(request, plan_id):

    plan = get_object_or_404(
        VisitPlan,
        id=plan_id
    )

    # Find next pavilion
    next_item = plan.items.filter(
        is_visited=False
    ).first()

    if not next_item:

        return redirect(
            "plan_detail",
            plan_id=plan.id
        )

    crowded_pavilion = next_item.pavilion

    # Challenge only appears for HIGH crowd
    if (
        crowded_pavilion.crowd_level
        != Pavilion.CrowdLevel.HIGH
    ):

        return redirect(
            "plan_detail",
            plan_id=plan.id
        )

    # Get 3 less crowded pavilions
    pavilions = get_challenge_pavilions(
        plan,
        crowded_pavilion
    )

    # Challenge requires 3 pavilions
    if len(pavilions) < 3:

        return redirect(
            "plan_detail",
            plan_id=plan.id
        )

    # Avoid duplicate active challenge
    challenge, created = (
        Challenge.objects.get_or_create(
            visit_plan=plan,
            crowded_pavilion=crowded_pavilion,
            is_completed=False,
        )
    )

    # Create challenge visits
    if created:

        for index, pavilion in enumerate(
            pavilions,
            start=1
        ):

            ChallengeVisit.objects.create(
                challenge=challenge,
                pavilion=pavilion,
                order=index
            )

    return redirect(
        "challenge_detail",
        challenge_id=challenge.id
    )


# ==========================================
# Challenge Details
# ==========================================

def challenge_detail(request, challenge_id):

    challenge = get_object_or_404(
        Challenge,
        id=challenge_id
    )

    visits = (
        challenge.visits
        .select_related("pavilion")
        .all()
    )

    completed_count = visits.filter(
        is_completed=True
    ).count()

    free_pass = FreePass.objects.filter(
        challenge=challenge
    ).first()

    return render(
        request,
        "planner/challenge_detail.html",
        {
            "challenge": challenge,
            "visits": visits,
            "completed_count": completed_count,
            "free_pass": free_pass,
        }
    )
    
    
@require_POST
def start_challenge_visit(request, visit_id):

    visit = get_object_or_404(
        ChallengeVisit,
        id=visit_id
    )

    # Already completed
    if visit.is_completed:

        return redirect(
            "challenge_detail",
            challenge_id=visit.challenge.id
        )

    # Don't restart timer
    if visit.started_at is None:

        visit.started_at = timezone.now()

        visit.save(
            update_fields=["started_at"]
        )

    return redirect(
        "challenge_detail",
        challenge_id=visit.challenge.id
    )
    

@require_POST
def check_challenge_visit(request, visit_id):

    visit = get_object_or_404(
        ChallengeVisit,
        id=visit_id
    )


    # إذا كانت الزيارة مكتملة مسبقًا
    if visit.is_completed:

        return redirect(
            "challenge_detail",
            challenge_id=visit.challenge.id
        )


    # إذا لم تبدأ الزيارة
    if visit.started_at is None:

        return redirect(
            "challenge_detail",
            challenge_id=visit.challenge.id
        )


    # الوقت الذي مر منذ بداية الزيارة
    elapsed_seconds = (
        timezone.now() - visit.started_at
    ).total_seconds()


    # مدة التحدي
    if settings.DEMO_MODE:

        required_seconds = (
            settings.DEMO_CHALLENGE_SECONDS
        )

    else:

        required_seconds = (
            visit.pavilion.challenge_visit_minutes
            * 60
        )


    # هل انتهت المدة؟
    if elapsed_seconds >= required_seconds:

        visit.is_completed = True

        visit.completed_at = timezone.now()

        visit.save(
            update_fields=[
                "is_completed",
                "completed_at"
            ]
        )


        # ==========================
        # هل اكتملت الزيارات الثلاث؟
        # ==========================

        challenge = visit.challenge

        has_incomplete_visits = (
            challenge.visits
            .filter(is_completed=False)
            .exists()
        )


        if not has_incomplete_visits:

            challenge.is_completed = True

            challenge.save(
                update_fields=[
                    "is_completed"
                ]
            )


            FreePass.objects.get_or_create(
                challenge=challenge,
                defaults={
                    "pavilion":
                        challenge.crowded_pavilion
                }
            )


    return redirect(
        "challenge_detail",
        challenge_id=visit.challenge.id
    )
    
def free_pass_detail(request, code):

    free_pass = get_object_or_404(
        FreePass,
        code=code
    )

    # URL that will be inside the QR
    verification_url = (
    f"{settings.DEMO_BASE_URL}"
    f"/pass/{free_pass.code}/verify/"
)

    # Create QR
    qr_image = qrcode.make(
        verification_url
    )

    buffer = BytesIO()

    qr_image.save(
        buffer,
        format="PNG"
    )

    qr_code = base64.b64encode(
        buffer.getvalue()
    ).decode()

    return render(
        request,
        "planner/free_pass.html",
        {
            "free_pass": free_pass,
            "qr_code": qr_code,
        }
    )
def verify_free_pass(request, code):

    free_pass = get_object_or_404(
        FreePass,
        code=code
    )

    is_valid = (
        free_pass.challenge.is_completed
        and not free_pass.is_used
    )

    return render(
        request,
        "planner/verify_free_pass.html",
        {
            "free_pass": free_pass,
            "is_valid": is_valid,
        }
    )
    
@require_POST
def use_free_pass(request, code):

    free_pass = get_object_or_404(
        FreePass,
        code=code
    )

    if (
        free_pass.challenge.is_completed
        and not free_pass.is_used
    ):

        free_pass.is_used = True
        free_pass.used_at = timezone.now()

        free_pass.save(
            update_fields=[
                "is_used",
                "used_at"
            ]
        )

    return redirect(
        "verify_free_pass",
        code=free_pass.code
    )
    
@require_POST
def check_challenge_location(request, visit_id):

    visit = get_object_or_404(
        ChallengeVisit,
        id=visit_id
    )

    latitude = request.POST.get("latitude")
    longitude = request.POST.get("longitude")

    if not latitude or not longitude:

        return render(
            request,
            "planner/location_result.html",
            {
                "visit": visit,
                "error": "تعذر الحصول على موقعك."
            }
        )

    try:
        latitude = float(latitude)
        longitude = float(longitude)

    except ValueError:

        return render(
            request,
            "planner/location_result.html",
            {
                "visit": visit,
                "error": "بيانات الموقع غير صحيحة."
            }
        )


    is_near, distance = is_user_near_pavilion(
        latitude,
        longitude,
        visit.pavilion
    )


    # المستخدم قريب من الجناح
    if is_near:

        # نبدأ العداد فقط أول مرة
        if visit.started_at is None:

            visit.started_at = timezone.now()

            visit.save(
                update_fields=["started_at"]
            )


    return render(
        request,
        "planner/location_result.html",
        {
            "visit": visit,
            "is_near": is_near,
            "distance": distance,
        }
    )