from fastapi.testclient import TestClient
from app.main import app

# יצירת "לקוח מדמה" ששולח בקשות לשרת שלנו מבלי באמת להפעיל אותו מחדש
client = TestClient(app)

def test_crud_lifecycle():
    """בדיקה שמוודאת יצירה, קריאה, עדכון ומחיקה עובדים כראוי"""
    
    # 1. בדיקת יצירה (Create)
    create_response = client.post(
        "/subscriptions",
        json={
            "name": "Spotify Test",
            "price": 20.0,
            "currency": "ILS",
            "billing_cycle": "monthly",
            "category": "entertainment",
            "status": "active"
        }
    )
    assert create_response.status_code == 201
    sub_data = create_response.json()
    sub_id = sub_data["id"]
    assert sub_data["name"] == "Spotify Test"

    # 2. בדיקת קריאה (Read)
    get_response = client.get("/subscriptions")
    assert get_response.status_code == 200
    assert len(get_response.json()) > 0

    # 3. בדיקת עדכון (Update)
    update_response = client.put(
        f"/subscriptions/{sub_id}",
        json={"price": 25.0}
    )
    assert update_response.status_code == 200
    assert update_response.json()["price"] == 25.0

    # 4. בדיקת מחיקה (Delete)
    delete_response = client.delete(f"/subscriptions/{sub_id}")
    assert delete_response.status_code == 204

    # וידוא שהמנוי אכן נמחק
    get_deleted = client.get(f"/subscriptions/{sub_id}")
    assert get_deleted.status_code == 404

def test_summary_endpoint():
    """בדיקה שנקודת הסיכום עובדת ומחזירה את המפתחות הנכונים"""
    response = client.get("/subscriptions/summary")
    assert response.status_code == 200
    data = response.json()
    assert "active_subscriptions" in data
    assert "monthly_burn_rate_ils" in data