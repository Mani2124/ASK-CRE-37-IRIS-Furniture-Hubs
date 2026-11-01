from src.overpass import fetch, query_stores


class Response:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"elements": []}


class Session:
    def post(self, *args, **kwargs):
        self.timeout = kwargs["timeout"]
        return Response()


def test_client_waits_longer_than_query_budget():
    session = Session()
    fetch(query_stores(), session=session, endpoints=["https://test.invalid"])
    assert session.timeout[1] > 180


def test_dashboard_does_not_override_timeout_to_45():
    from pathlib import Path

    app = (Path(__file__).parents[1] / "app.py").read_text()
    assert "read_timeout=45" not in app
