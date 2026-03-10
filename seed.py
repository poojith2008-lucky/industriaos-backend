from app.database import SessionLocal, engine, Base
from app.models import User, Employee
from app.models.revenue import Revenue, ActivityLog
from app.core.security import hash_password
from datetime import date, datetime

# ── Create all tables ─────────────────────────────────────
Base.metadata.create_all(bind=engine)

def seed():
    db = SessionLocal()
    try:
        # ── Skip if already seeded ───────────────────────────
        if db.query(User).count() > 0:
            print("✅ Database already seeded!")
            return

        print("🌱 Seeding database...")

        # ── ADMIN ────────────────────────────────────────────
        admin = User(
            name="Rajesh Kumar",
            email="admin@company.com",
            hashed_password=hash_password("admin123"),
            role="ADMIN",
            is_active=True
        )
        db.add(admin)

        # ── HR ───────────────────────────────────────────────
        hr = User(
            name="Priya Sharma",
            email="hr@company.com",
            hashed_password=hash_password("hr1234"),
            role="HR",
            is_active=True
        )
        db.add(hr)
        db.flush()

        # ── EMPLOYEES ────────────────────────────────────────
        employees_data = [
            {
                "name": "Arun Patel",
                "email": "arun@company.com",
                "password": "emp123",
                "dept": "Engineering",
                "position": "Software Engineer",
                "salary": 85000,
            },
            {
                "name": "Meena Nair",
                "email": "meena@company.com",
                "password": "emp456",
                "dept": "Design",
                "position": "UI/UX Designer",
                "salary": 72000,
            },
            {
                "name": "Rahul Singh",
                "email": "rahul@company.com",
                "password": "emp789",
                "dept": "Sales",
                "position": "Sales Executive",
                "salary": 65000,
            },
            {
                "name": "Divya Rao",
                "email": "divya@company.com",
                "password": "emp000",
                "dept": "Marketing",
                "position": "Marketing Executive",
                "salary": 70000,
            },
        ]

        for e in employees_data:
            user = User(
                name=e["name"],
                email=e["email"],
                hashed_password=hash_password(e["password"]),
                role="EMPLOYEE",
                is_active=True
            )
            db.add(user)
            db.flush()
            emp = Employee(
                user_id=user.id,
                department=e["dept"],
                position=e["position"],
                base_salary=e["salary"],
                phone="+91 98765 43210",
                address="Hyderabad, Telangana",
                emergency_contact="+91 91234 56789",
                join_date=date(2024, 1, 1)
            )
            db.add(emp)

        # ── REVENUE DATA ─────────────────────────────────────
        revenue_data = [
            { "month": 10, "year": 2025, "amount": 4200000, "expense": 1800000 },
            { "month": 11, "year": 2025, "amount": 4500000, "expense": 1900000 },
            { "month": 12, "year": 2025, "amount": 4800000, "expense": 2000000 },
            { "month": 1,  "year": 2026, "amount": 4600000, "expense": 1950000 },
            { "month": 2,  "year": 2026, "amount": 5000000, "expense": 2100000 },
            { "month": 3,  "year": 2026, "amount": 5200000, "expense": 2200000 },
        ]

        for r in revenue_data:
            rev = Revenue(
                month=r["month"], year=r["year"],
                amount=r["amount"], expense=r["expense"],
                profit=r["amount"] - r["expense"],
                uploaded_by=1
            )
            db.add(rev)

        db.commit()
        print("✅ Database seeded successfully!")
        print("")
        print("🔐 Login Credentials:")
        print("─────────────────────────────────────")
        print("ADMIN    → admin@company.com / admin123")
        print("HR       → hr@company.com    / hr1234")
        print("EMPLOYEE → arun@company.com  / emp123")
        print("EMPLOYEE → meena@company.com / emp456")
        print("EMPLOYEE → rahul@company.com / emp789")
        print("EMPLOYEE → divya@company.com / emp000")
        print("─────────────────────────────────────")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()