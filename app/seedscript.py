import os
from datetime import date
from sqlmodel import Session, create_engine, select
from app.main import Subscription  # ייבוא המודל בלבד

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://subman:submanpass@db:5432/subman_db")
engine = create_engine(DATABASE_URL)

def seed_data():
    print(f"🌱 Connecting to database at: {DATABASE_URL}")
    
    with Session(engine) as session:
        # 🧹 מוחק את כל מה שיש בטבלה כרגע כדי להתחיל נקי ומעודכן
        session.query(Subscription).delete()
        print("🧹 Database cleaned! Preparing to inject fresh records...")
        
        sample_subs = [
            Subscription(
                name="Netflix",
                price=16.216,  
                currency="USD",
                category="entertainment",
                billing_cycle="monthly",
                status="active",
                purchase_date=date(2026, 1, 15),
                next_billing_date=date(2026, 7, 15)
            ),
            Subscription(
                name="Spotify Premium",
                price=21.90,
                currency="ILS",
                category="entertainment",
                billing_cycle="monthly",
                status="active",
                purchase_date=date(2026, 2, 10),
                next_billing_date=date(2026, 7, 10)
            ),
            Subscription(
                name="Gym Membership",
                price=250.00,
                currency="ILS",
                category="sport",
                billing_cycle="monthly",
                status="active",
                purchase_date=date(2026, 6, 1),
                next_billing_date=date(2026, 7, 1)
            ),
            Subscription(
                name="AWS Cloud Server",
                price=45.00,
                currency="USD",
                category="software",
                billing_cycle="monthly",
                status="active",
                purchase_date=date(2026, 3, 20),
                next_billing_date=date(2026, 7, 20)
            )
        ]

        for sub in sample_subs:
            session.add(sub)
            print(f"➕ Added sample subscription: {sub.name} (Price: {sub.price})")
        
        session.commit()
    print("✅ Database seeding completed successfully with updated values!")

if __name__ == "__main__":
    seed_data()