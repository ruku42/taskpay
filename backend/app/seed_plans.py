from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models.plans import Plan


PLANS = [
    {
        "name": "Starter",
        "deposit_amount": 100,
        "daily_task_limit": 5,
        "sort_order": 1,
    },
    {
        "name": "Basic",
        "deposit_amount": 200,
        "daily_task_limit": 8,
        "sort_order": 2,
    },
    {
        "name": "Standard",
        "deposit_amount": 300,
        "daily_task_limit": 10,
        "sort_order": 3,
    },
    {
        "name": "Premium",
        "deposit_amount": 500,
        "daily_task_limit": 15,
        "sort_order": 4,
    },
    {
        "name": "Pro",
        "deposit_amount": 800,
        "daily_task_limit": 20,
        "sort_order": 5,
    },
]


def seed_plans():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        for plan_data in PLANS:
            existing = db.scalar(
                select(Plan).where(
                    Plan.deposit_amount == plan_data["deposit_amount"]
                )
            )

            if existing:
                continue

            db.add(
                Plan(
                    name=plan_data["name"],
                    deposit_amount=plan_data["deposit_amount"],
                    daily_task_limit=plan_data["daily_task_limit"],
                    status="active",
                    sort_order=plan_data["sort_order"],
                )
            )

        db.commit()
        print("TaskPay plans seeded successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_plans()
