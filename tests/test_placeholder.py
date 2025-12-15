def test_can_import_package() -> None:
    import tg_bot_meal_planning

    assert tg_bot_meal_planning.__version__ == "0.1.0"
