from django.urls import path
from . import views


urlpatterns = [
    path("", views.create_plan, name="create_plan"),
    
    path(
    "plan/<int:plan_id>/challenge/start/",
    views.start_challenge,
    name="start_challenge"
),

path(
    "challenge/<int:challenge_id>/",
    views.challenge_detail,
    name="challenge_detail"
),

path(
    "plan/<int:plan_id>/",
    views.plan_detail,
    name="plan_detail"
),

path(
    "plan-item/<int:item_id>/complete/",
    views.complete_plan_item,
    name="complete_plan_item"
),
path(
    "challenge-visit/<int:visit_id>/start/",
    views.start_challenge_visit,
    name="start_challenge_visit"
),

path(
    "challenge-visit/<int:visit_id>/check/",
    views.check_challenge_visit,
    name="check_challenge_visit"
),
path(
    "pass/<uuid:code>/",
    views.free_pass_detail,
    name="free_pass_detail"
),

path(
    "pass/<uuid:code>/verify/",
    views.verify_free_pass,
    name="verify_free_pass"
),

path(
    "pass/<uuid:code>/use/",
    views.use_free_pass,
    name="use_free_pass"
),
path(
    "challenge-visit/<int:visit_id>/location/",
    views.check_challenge_location,
    name="check_challenge_location"
),
]

