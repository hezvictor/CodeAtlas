def test_application_module_imports_successfully():
    import app.main

    assert app.main.app.title == "CodeAtlas API"
