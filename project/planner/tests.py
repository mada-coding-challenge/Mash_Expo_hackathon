from django.test import TestCase

from .ml_service import (
    DEFAULT_INTEREST_WEIGHTS,
    load_interest_model,
    score_pavilions,
)
from .models import Interest, Pavilion
from .services import create_smart_visit_plan


class SmartPlanTests(TestCase):

    def setUp(self):
        self.tech = Interest.objects.create(
            name="التقنية", model_weights=DEFAULT_INTEREST_WEIGHTS["التقنية"]
        )
        self.food = Interest.objects.create(
            name="الطعام", model_weights=DEFAULT_INTEREST_WEIGHTS["الطعام"]
        )

        def pav(name, interest, lat, lng, minutes=20):
            p = Pavilion.objects.create(
                name=name, description="-", highlights="-",
                recommended_duration=minutes, latitude=lat, longitude=lng,
            )
            p.interests.add(interest)
            return p

        self.t1 = pav("تقنية 1", self.tech, 24.9300, 46.7300)
        self.t2 = pav("تقنية 2", self.tech, 24.9302, 46.7302)
        self.f1 = pav("مطعم", self.food, 24.9250, 46.7300, minutes=40)

    def _plan(self, interests, chosen, minutes):
        pavilions = list(Pavilion.objects.prefetch_related("interests"))
        scores, reasons, _ = score_pavilions(
            pavilions, interests, chosen, minutes, "solo"
        )
        return scores, create_smart_visit_plan(
            pavilions, scores, reasons, [p.id for p in chosen], minutes
        )

    def test_model_loads(self):
        self.assertIsNotNone(load_interest_model())

    def test_interest_drives_ranking(self):
        scores, _ = self._plan([self.tech], [], 60)
        self.assertGreater(scores[self.t1.id], scores[self.f1.id])

    def test_plan_respects_time(self):
        _, plan = self._plan([self.tech], [], 45)
        self.assertLessEqual(plan["total_time"], 45)
        names = [i["pavilion"].name for i in plan["items"]]
        self.assertEqual(set(names), {"تقنية 1", "تقنية 2"})

    def test_chosen_pavilion_included(self):
        _, plan = self._plan([self.tech], [self.f1], 60)
        self.assertIn(self.f1, [i["pavilion"] for i in plan["items"]])
