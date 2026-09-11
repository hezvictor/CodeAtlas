

def test_worker_settings_register_document_processor():
    from app.worker import WorkerSettings

    assert "process_document" in {fn.__name__ for fn in WorkerSettings.functions}
