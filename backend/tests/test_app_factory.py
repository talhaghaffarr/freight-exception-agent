from relayops.errors import ApiError


def test_application_errors_use_versioned_envelope(client):
    response = client.get("/api/v1/does-not-exist")
    body = response.get_json()
    assert response.status_code == 404
    assert body["data"] is None
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["meta"]["request_id"].startswith("req_")


def test_successful_responses_carry_the_same_envelope(client):
    response = client.get("/api/v1/meta")
    body = response.get_json()
    assert response.status_code == 200
    assert body["error"] is None
    assert body["data"]["environment_mode"] == "sandbox"
    assert body["data"]["api_version"] == "v1"
    assert body["meta"]["request_id"].startswith("req_")


def test_request_id_is_echoed_in_a_header_and_is_unique(client):
    first = client.get("/api/v1/meta")
    second = client.get("/api/v1/meta")
    assert first.headers["X-Request-ID"].startswith("req_")
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_api_error_renders_code_message_and_details(app):
    @app.route("/api/v1/_boom")
    def boom():
        raise ApiError(
            "GOAL_NOT_RETRYABLE", "This goal is already complete.", 409, {"state": "succeeded"}
        )

    response = app.test_client().get("/api/v1/_boom")
    body = response.get_json()
    assert response.status_code == 409
    assert body["error"] == {
        "code": "GOAL_NOT_RETRYABLE",
        "message": "This goal is already complete.",
        "details": {"state": "succeeded"},
    }


def test_unexpected_exceptions_do_not_leak_internal_detail(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/api/v1/_explode")
    def explode():
        raise RuntimeError("connection string postgres://user:hunter2@db/relayops")

    response = app.test_client().get("/api/v1/_explode")
    body = response.get_json()
    assert response.status_code == 500
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "hunter2" not in response.get_data(as_text=True)


def test_method_not_allowed_uses_the_envelope(client):
    response = client.post("/api/v1/meta")
    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"
