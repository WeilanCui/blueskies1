from django.core.management.base import BaseCommand

from skinconcerns.seeds.loader import seed_skin_concerns


class Command(BaseCommand):
    help = "Seed normalized skin concerns, aliases, rules, evidence, and red flags."

    def handle(self, *args, **options):
        counts = seed_skin_concerns()
        parts = ", ".join(f"{key}={value}" for key, value in counts.items())
        self.stdout.write(self.style.SUCCESS("Skin concern seed complete."))
        self.stdout.write(f"  {parts}")
