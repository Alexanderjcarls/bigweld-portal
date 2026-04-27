async def test_health_does_not_require_auth(client):
    r = await client.get("/health")
    assert r.status_code == 200


async def test_protected_endpoint_rejects_missing_header(client):
    r = await client.get("/api/conversations")
    assert r.status_code == 401


async def test_protected_endpoint_accepts_correct_email(client):
    r = await client.get(
        "/api/conversations",
        headers={"Cf-Access-Authenticated-User-Email": "alexanderjcarlson@gmail.com"},
    )
    assert r.status_code in (200, 404)
