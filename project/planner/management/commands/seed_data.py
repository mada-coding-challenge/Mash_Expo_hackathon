import json

from pathlib import Path

from django.core.management.base import BaseCommand

from planner.models import Interest, Pavilion
from planner.ml_service import DEFAULT_INTEREST_WEIGHTS


class Command(BaseCommand):

    help = "Load Expo 2030 pavilions and interests"

    def handle(self, *args, **options):

        file_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "expo2030_pavilions_project.json"
        )

        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Create interests
        for interest_name in data["meta"]["project_interests"]:

            interest, _ = Interest.objects.get_or_create(
                name=interest_name
            )

            # ربط الاهتمام بأبعاد موديل الاهتمامات
            if not interest.model_weights:
                interest.model_weights = DEFAULT_INTEREST_WEIGHTS.get(
                    interest_name, {}
                )
                interest.save(update_fields=["model_weights"])

        # Create pavilions
        for pavilion_data in data["pavilions"]:

            crowd_mapping = {
                "low": Pavilion.CrowdLevel.LOW,
                "moderate": Pavilion.CrowdLevel.MEDIUM,
                "high": Pavilion.CrowdLevel.HIGH,
                "very_high": Pavilion.CrowdLevel.HIGH,
            }

            pavilion, created = Pavilion.objects.update_or_create(

                name=pavilion_data["name_ar"],

                defaults={
                    "country": "",
                    "description": pavilion_data["description"],
                    "highlights": ", ".join(
                        pavilion_data["highlights"]
                    ),
                    "recommended_duration":
                        pavilion_data["recommended_duration"],
                    "latitude": pavilion_data["latitude"],
                    "longitude": pavilion_data["longitude"],
                    "crowd_level": crowd_mapping[
                        pavilion_data["crowd_level"]
                    ],
                    "challenge_visit_minutes":
                        pavilion_data[
                            "challenge_visit_minutes"
                        ],
                    "is_active":
                        pavilion_data["is_active"],
                }
            )

            # Connect pavilion with interests
            pavilion.interests.clear()

            for interest_name in pavilion_data["interests"]:

                interest = Interest.objects.get(
                    name=interest_name
                )

                pavilion.interests.add(interest)

            if created:
                self.stdout.write(
                    f"Created: {pavilion.name}"
                )
            else:
                self.stdout.write(
                    f"Updated: {pavilion.name}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Expo data loaded successfully!"
            )
        )