from agent import langchain_assitant as assistant


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None
        self.parameters = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, statement, parameters):
        self.statement = str(statement)
        self.parameters = parameters
        return FakeResult(self.rows)


class FakeEngine:
    def __init__(self, rows):
        self.connection = FakeConnection(rows)

    def connect(self):
        return self.connection


def test_search_dishes_by_name_finds_available_menu_item(monkeypatch):
    rows = [{"id": 1, "dish_name": "蒜蓉西兰花", "price": 15.0}]
    engine = FakeEngine(rows)
    monkeypatch.setattr(assistant, "get_mysql_engine", lambda: engine)

    result = assistant.search_dishes_by_name.invoke({"dish_name": " 蒜蓉西兰花 "})

    assert result == rows
    assert engine.connection.parameters == {"dish_name": "%蒜蓉西兰花%"}
    assert "is_available = 1" in engine.connection.statement


def test_search_dishes_by_name_reports_no_match(monkeypatch):
    engine = FakeEngine([])
    monkeypatch.setattr(assistant, "get_mysql_engine", lambda: engine)

    result = assistant.search_dishes_by_name.invoke({"dish_name": "不存在的菜"})

    assert "没有找到" in result
