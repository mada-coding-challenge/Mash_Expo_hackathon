from django.urls import path

from . import api

urlpatterns = [
    path("", api.app_page, name="mashi_app"),
    path("api/bootstrap/", api.bootstrap, name="mashi_bootstrap"),
    path("api/plans/", api.plan_create, name="mashi_plan_create"),
    path("api/plans/<int:plan_id>/", api.plan_detail, name="mashi_plan"),
    path("api/plan-items/<int:item_id>/complete/", api.plan_item_complete, name="mashi_item_complete"),
    path("api/plans/<int:plan_id>/challenge/", api.challenge_start, name="mashi_challenge_start"),
    path("api/challenges/<int:challenge_id>/", api.challenge_detail, name="mashi_challenge"),
    path("api/challenge-visits/<int:visit_id>/arrive/", api.visit_simulate_arrival, name="mashi_visit_arrive"),
    path("api/challenge-visits/<int:visit_id>/location/", api.visit_location, name="mashi_visit_location"),
    path("api/challenge-visits/<int:visit_id>/check/", api.visit_check, name="mashi_visit_check"),
    path("api/passes/<uuid:code>/", api.pass_detail, name="mashi_pass"),
    path("api/passes/<uuid:code>/use/", api.pass_use, name="mashi_pass_use"),
]
