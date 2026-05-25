from celery import shared_task


@shared_task
def debug_task() -> str:
    return "Celery is connected."
