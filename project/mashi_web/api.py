"""
mashi_web — طبقة ربط بين واجهة mashi والباك اند الموجود (تطبيق planner).

لا تعدّل أي شيء في planner: كل عملية تغيّر البيانات تمر عبر دوال
planner.views نفسها (إنشاء الخطة، إنهاء الزيارة، بدء التحدي، التحقق من الموقع،
إكمال زيارة التحدي، استخدام المسار السريع)، وهنا فقط نقرأ النتيجة ونرجعها JSON.
"""

import base64
import json
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import qrcode
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, render
from django.urls import resolve, reverse, Resolver404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from planner import views as planner_views
from planner.forms import VisitPlanForm
from planner.ml_service import score_pavilions
from planner.models import (
    Challenge,
    ChallengeVisit,
    VisitPlanItem,
    FreePass,
    Interest,
    Pavilion,
    VisitPlan,
)
from planner.services import (
    build_schedule,
    duration_label,
    format_time_range,
    is_user_near_pavilion,
    pavilion_travel_info,
)

DATA_FILE = (
    Path(planner_views.__file__).resolve().parent
    / "data"
    / "expo2030_pavilions_project.json"
)
SESSION_PLAN = "mashi_plan_id"


# ==========================================
# الصفحة نفسها
# ==========================================

@require_GET
def app_page(request):
    """يعرض واجهة mashi (templates/mashi/index.html + static/mashi/) ويضبط كوكي CSRF."""
    get_token(request)
    api_base = reverse("mashi_bootstrap").rsplit("bootstrap/", 1)[0].rstrip("/")
    return render(request, "mashi/index.html", {"api_base": api_base})


# ==========================================
# بيانات إضافية للعرض فقط (من ملف البيانات، قراءة فقط)
# ==========================================

@lru_cache(maxsize=1)
def _extra_by_name():
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {p["name_ar"]: p for p in data.get("pavilions", [])}


def _pavilion(p):
    extra = _extra_by_name().get(p.name, {})
    return {
        "id": p.id,
        "name": p.name,
        "name_en": extra.get("name_en", ""),
        "category": extra.get("category", ""),
        "zone": extra.get("zone", ""),
        "description": p.description,
        "highlights": [h.strip() for h in (p.highlights or "").split(",") if h.strip()],
        "duration": p.recommended_duration,
        "wait": extra.get("wait_minutes"),
        "crowd": p.crowd_level,
        "crowd_label": p.get_crowd_level_display(),
        "lat": float(p.latitude) if p.latitude is not None else None,
        "lng": float(p.longitude) if p.longitude is not None else None,
        "interests": [i.id for i in p.interests.all()],
        "challenge_minutes": p.challenge_visit_minutes,
    }


def _hhmm(t):
    return t.strftime("%H:%M") if t else None


def _error(message, status=400, **extra):
    return JsonResponse({"error": message, **extra}, status=status)


def _redirect_kwargs(response, url_name):
    """يقرأ رقم العنصر من الـ redirect الذي ترجعه دوال planner."""
    if response.status_code not in (301, 302):
        return None
    try:
        match = resolve(response.url)
    except Resolver404:
        return None
    return match.kwargs if match.url_name == url_name else None


def _drop_messages(request):
    # دوال planner تضيف رسائل للواجهة القديمة؛ نستهلكها هنا حتى لا تتراكم
    list(messages.get_messages(request))


# ==========================================
# البداية: الاهتمامات + الأجنحة + آخر خطة
# ==========================================

@require_GET
def bootstrap(request):
    interests = [{"id": i.id, "name": i.name} for i in Interest.objects.order_by("id")]
    pavilions = [
        _pavilion(p)
        for p in Pavilion.objects.filter(is_active=True).prefetch_related("interests").order_by("id")
    ]
    plan_id = request.session.get(SESSION_PLAN)
    plan = VisitPlan.objects.filter(id=plan_id).first() if plan_id else None
    return JsonResponse({
        "interests": interests,
        "pavilions": pavilions,
        "plan": _plan_payload(request, plan) if plan else None,
        "demo_mode": bool(getattr(settings, "DEMO_MODE", False)),
    })


# ==========================================
# الخطة
# ==========================================

def _plan_payload(request, plan):
    items = list(plan.items.select_related("pavilion").prefetch_related("pavilion__interests"))
    next_item = next((i for i in items if not i.is_visited), None)

    passes = list(FreePass.objects.filter(challenge__visit_plan=plan))
    pass_pavilion_ids = {p.pavilion_id for p in passes}
    active_passes = {p.pavilion_id: p for p in passes if not p.is_used}

    # نفس شرط planner.views.plan_detail
    show_challenge = bool(
        next_item
        and next_item.pavilion.crowd_level == Pavilion.CrowdLevel.HIGH
        and next_item.pavilion_id not in pass_pavilion_ids
    )

    meta = request.session.get(f"mashi_plan_{plan.id}", {})
    reasons = meta.get("reasons", {})
    chosen = set(meta.get("chosen", []))

    rows = []
    cursor = plan.start_time.hour * 60 + plan.start_time.minute if plan.start_time else 600
    previous = None
    for row in build_schedule(plan, items):
        item = row["item"]
        if previous is not None:
            cursor += pavilion_travel_info(previous.pavilion, item.pavilion)["walking_time"]
        fp = active_passes.get(item.pavilion_id)
        rows.append({
            "item_id": item.id,
            "order": item.order,
            "pavilion": _pavilion(item.pavilion),
            "clock": row["clock"],
            "period": row["period"],
            "start_min": cursor,
            "walk": row["walk"],
            "is_visited": item.is_visited,
            "is_next": bool(next_item and item.id == next_item.id),
            "chosen": item.pavilion_id in chosen,
            "reason": reasons.get(str(item.pavilion_id), ""),
            "free_pass": {"code": str(fp.code), "is_used": fp.is_used} if fp else None,
        })
        cursor += item.pavilion.recommended_duration
        previous = item

    challenges = [
        {
            "id": c.id,
            "is_completed": c.is_completed,
            "crowded_pavilion_id": c.crowded_pavilion_id,
        }
        for c in Challenge.objects.filter(visit_plan=plan).order_by("-id")
    ]

    done = sum(1 for i in items if i.is_visited)
    span = None
    if plan.start_time and plan.end_time:
        span = (plan.end_time.hour * 60 + plan.end_time.minute) - (
            plan.start_time.hour * 60 + plan.start_time.minute
        )

    return {
        "id": plan.id,
        "visit_date": plan.visit_date.isoformat() if plan.visit_date else None,
        "start_time": _hhmm(plan.start_time),
        "end_time": _hhmm(plan.end_time),
        "time_range": format_time_range(plan.start_time, plan.end_time),
        "duration_text": duration_label(span) if span else "",
        "is_completed": plan.is_completed,
        "done_count": done,
        "total_count": len(items),
        "next_item_id": next_item.id if next_item else None,
        "show_challenge": show_challenge,
        "rows": rows,
        "challenges": challenges,
        "skipped": meta.get("skipped", []),
    }


@require_POST
def plan_create(request):
    form = VisitPlanForm(request.POST)
    if not form.is_valid():
        return _error("invalid", errors=form.errors.get_json_data())

    # الأسباب لا تُحفظ في القاعدة؛ نحسبها بنفس دالة الموديل لعرضها في الواجهة
    pavilions = list(Pavilion.objects.filter(is_active=True).prefetch_related("interests"))
    chosen = list(form.cleaned_data["favorite_pavilions"].prefetch_related("interests"))
    _scores, reasons, _profile = score_pavilions(
        pavilions=pavilions,
        selected_interests=form.cleaned_data["interests"],
        chosen_pavilions=chosen,
        available_minutes=form.cleaned_data["available_minutes"],
        group_type=form.cleaned_data.get("group_type") or "solo",
    )

    # إنشاء الخطة الفعلي يتم في planner.views.create_plan كما هو
    response = planner_views.create_plan(request)
    _drop_messages(request)
    kwargs = _redirect_kwargs(response, "plan_detail")
    if not kwargs:
        return _error("plan_not_created", status=500)

    plan = VisitPlan.objects.get(id=kwargs["plan_id"])
    planned_ids = set(plan.items.values_list("pavilion_id", flat=True))
    request.session[SESSION_PLAN] = plan.id
    request.session[f"mashi_plan_{plan.id}"] = {
        "reasons": {str(k): v for k, v in reasons.items()},
        "chosen": [p.id for p in chosen],
        "skipped": [p.name for p in chosen if p.id not in planned_ids],
    }
    return JsonResponse(_plan_payload(request, plan), status=201)


@require_GET
def plan_detail(request, plan_id):
    plan = get_object_or_404(VisitPlan, id=plan_id)
    return JsonResponse(_plan_payload(request, plan))


@require_POST
def plan_item_complete(request, item_id):
    item = get_object_or_404(VisitPlanItem, id=item_id)
    planner_views.complete_plan_item(request, item_id)
    item.plan.refresh_from_db()
    return JsonResponse(_plan_payload(request, item.plan))


# ==========================================
# Discover & Earn
# ==========================================

def _required_seconds(visit):
    if getattr(settings, "DEMO_MODE", False):
        return int(getattr(settings, "DEMO_CHALLENGE_SECONDS", 10))
    return visit.pavilion.challenge_visit_minutes * 60


def _challenge_payload(challenge):
    visits = list(challenge.visits.select_related("pavilion").prefetch_related("pavilion__interests"))
    now = timezone.now()
    out = []
    for v in visits:
        required = _required_seconds(v)
        remaining = None
        if v.started_at and not v.is_completed:
            remaining = max(0, int(required - (now - v.started_at).total_seconds()))
        out.append({
            "id": v.id,
            "order": v.order,
            "pavilion": _pavilion(v.pavilion),
            "started": v.started_at.isoformat() if v.started_at else None,
            "is_completed": v.is_completed,
            "required_seconds": required,
            "remaining_seconds": remaining,
        })
    fp = FreePass.objects.filter(challenge=challenge).select_related("pavilion").first()
    return {
        "id": challenge.id,
        "plan_id": challenge.visit_plan_id,
        "crowded": _pavilion(challenge.crowded_pavilion),
        "is_completed": challenge.is_completed,
        "completed_count": sum(1 for v in visits if v.is_completed),
        "visits": out,
        "free_pass": (
            {"code": str(fp.code), "is_used": fp.is_used, "pavilion_id": fp.pavilion_id}
            if fp else None
        ),
    }


@require_POST
def challenge_start(request, plan_id):
    plan = get_object_or_404(VisitPlan, id=plan_id)
    response = planner_views.start_challenge(request, plan.id)
    kwargs = _redirect_kwargs(response, "challenge_detail")
    if not kwargs:
        # planner لا يبدأ التحدي إذا لم يكن الجناح التالي مزدحمًا أو لا توجد 3 أجنحة بديلة
        return _error("challenge_unavailable", status=409)
    challenge = get_object_or_404(Challenge, id=kwargs["challenge_id"])
    return JsonResponse(_challenge_payload(challenge), status=201)


@require_GET
def challenge_detail(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    return JsonResponse(_challenge_payload(challenge))


@require_POST
def visit_simulate_arrival(request, visit_id):
    visit = get_object_or_404(ChallengeVisit, id=visit_id)
    planner_views.start_challenge_visit(request, visit.id)
    return JsonResponse(_challenge_payload(visit.challenge))


@require_POST
def visit_location(request, visit_id):
    visit = get_object_or_404(ChallengeVisit, id=visit_id)
    is_near, distance = None, None
    try:
        lat = float(request.POST.get("latitude", ""))
        lng = float(request.POST.get("longitude", ""))
        is_near, distance = is_user_near_pavilion(lat, lng, visit.pavilion)
    except ValueError:
        pass
    # الحفظ الفعلي (بدء العداد إذا كان قريبًا) يتم في planner.views
    planner_views.check_challenge_location(request, visit.id)
    payload = _challenge_payload(visit.challenge)
    payload["location"] = {"is_near": bool(is_near), "distance": distance}
    return JsonResponse(payload)


@require_POST
def visit_check(request, visit_id):
    visit = get_object_or_404(ChallengeVisit, id=visit_id)
    planner_views.check_challenge_visit(request, visit.id)
    visit.challenge.refresh_from_db()
    return JsonResponse(_challenge_payload(visit.challenge))


# ==========================================
# المسار السريع
# ==========================================

def _pass_payload(free_pass):
    verify_url = f"{settings.DEMO_BASE_URL}/pass/{free_pass.code}/verify/"
    buffer = BytesIO()
    qrcode.make(verify_url).save(buffer, format="PNG")
    return {
        "code": str(free_pass.code),
        "pavilion": _pavilion(free_pass.pavilion),
        "is_used": free_pass.is_used,
        "used_at": free_pass.used_at.isoformat() if free_pass.used_at else None,
        "is_valid": free_pass.challenge.is_completed and not free_pass.is_used,
        "verify_url": verify_url,
        "qr_png": base64.b64encode(buffer.getvalue()).decode(),
    }


@require_GET
def pass_detail(request, code):
    free_pass = get_object_or_404(FreePass.objects.select_related("pavilion", "challenge"), code=code)
    return JsonResponse(_pass_payload(free_pass))


@require_POST
def pass_use(request, code):
    planner_views.use_free_pass(request, code)
    free_pass = get_object_or_404(FreePass.objects.select_related("pavilion", "challenge"), code=code)
    return JsonResponse(_pass_payload(free_pass))
