from fastapi.testclient import TestClient
from app.main import app

# יצירת "לקוח מדמה" ששולח בקשות לשרת שלנו מבלי באמת להפעיל אותו מחדש
client = TestClient(app)

def test_crud_lifecycle():
    """בדיקה שמוודאת יצירה, קריאה ומחיקה עובדים כראוי לפי המבנה החדש"""
    
    test_name = "Spotify Test API"
    
    # 1. בדיקת יצירה (Create)
    create_response = client.post(
        "/subscriptions",
        json={
            "name": test_name,
            "price": 20.0,
            "currency": "USD",
            "billing_cycle": "monthly",
            "category": "entertainment",
            "status": "active"
        }
    )
    assert create_response.status_code == 201
    sub_data = create_response.json()
    assert sub_data["name"] == test_name

    # 2. בדיקת קריאה (Read)
    get_response = client.get("/subscriptions")
    assert get_response.status_code == 200
    assert len(get_response.json()) > 0

    # 3. בדיקת מחיקה (Delete)
    # שים לב שכעת אנו מוחקים לפי השם, והשרת מחזיר 200 (OK)
    delete_response = client.delete(f"/subscriptions/{test_name}")
    assert delete_response.status_code == 200

    # 4. וידוא מחיקה (ניסיון למחוק שוב אמור להחזיר 404 Not Found)
    delete_again = client.delete(f"/subscriptions/{test_name}")
    assert delete_again.status_code == 404

def test_summary_endpoint():
    """בדיקה שנקודת הסיכום עובדת ומחזירה את המפתחות הנכונים"""
    response = client.get("/subscriptions/summary")
    assert response.status_code == 200
    data = response.json()
    assert "active_subscriptions" in data
    assert "monthly_burn_rate_ils" in data

def test_validation_error():
    """בדיקת אבטחה: מוודא שהשרת חוסם מנוי עם מחיר שלילי"""
    response = client.post(
        "/subscriptions",
        json={
            "name": "Netflix Fake",
            "price": -50.0, # מחיר לא חוקי!
            "currency": "ILS",
            "billing_cycle": "monthly",
            "category": "entertainment",
            "status": "active"
        }
    )
    # Pydantic אמור לזרוק שגיאת 422 Unprocessable Entity
    assert response.status_code == 422