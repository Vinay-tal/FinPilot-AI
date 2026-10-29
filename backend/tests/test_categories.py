from fastapi.testclient import TestClient

def test_list_categories(client: TestClient, auth_user: dict):
    res = client.get("/api/v1/categories", headers=auth_user["headers"])
    assert res.status_code == 200
    cats = res.json()
    assert len(cats) >= 14
    slugs = [c["slug"] for c in cats]
    assert "food-dining" in slugs
    assert "salary" in slugs
    assert "housing-rent" in slugs

def test_create_custom_category(client: TestClient, auth_user: dict):
    payload = {
        "name": "Pet Care & Vet",
        "slug": "pet-care",
        "icon": "dog",
        "color": "#10b981",
        "is_income": False,
    }
    res = client.post("/api/v1/categories", json=payload, headers=auth_user["headers"])
    assert res.status_code == 201
    cat = res.json()
    assert cat["name"] == "Pet Care & Vet"
    assert cat["is_system"] is False

    # Attempting duplicate should fail with 409
    dup_res = client.post("/api/v1/categories", json=payload, headers=auth_user["headers"])
    assert dup_res.status_code == 409
