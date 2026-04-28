"""Render endpoints: server-side fallback when client rendering is unavailable."""

AUTH = {"Cf-Access-Jwt-Assertion": "valid-test-jwt"}


async def test_kroki_render_proxies_to_kroki(client, httpx_mock):
    httpx_mock.add_response(
        url="http://127.0.0.1:8889/mermaid/svg",
        content=b"<svg>mermaid</svg>",
        method="POST",
    )
    r = await client.post(
        "/api/render/kroki",
        json={"diagram_type": "mermaid", "source": "graph TD\nA-->B"},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.content == b"<svg>mermaid</svg>"


async def test_render_unsupported_diagram_type_404(client, httpx_mock):
    r = await client.post(
        "/api/render/kroki",
        json={"diagram_type": "wat", "source": "x"},
        headers=AUTH,
    )
    assert r.status_code == 400


async def test_kroki_502_on_kroki_down(client, httpx_mock):
    httpx_mock.add_exception(
        Exception("connection refused"),
        url="http://127.0.0.1:8889/mermaid/svg",
        method="POST",
    )
    r = await client.post(
        "/api/render/kroki",
        json={"diagram_type": "mermaid", "source": "x"},
        headers=AUTH,
    )
    assert r.status_code == 502
