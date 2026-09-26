def test_crear_y_listar_candidatura(client):
    payload = {
        "company": "Acme",
        "position": "Data Engineer",
        "source": "LinkedIn",
        "found_date": "2026-09-01",
        "job_type": "Data Engineer",
        "status": "Guardada",
    }
    res = client.post("/applications", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["company"] == "Acme"
    assert data["max_stage_reached"] == 0

    res = client.get("/applications")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_no_se_puede_fijar_sin_respuesta_a_mano(client):
    payload = {
        "company": "Acme",
        "position": "Backend",
        "source": "Indeed",
        "found_date": "2026-09-01",
        "job_type": "Backend",
        "status": "Sin respuesta",
    }
    res = client.post("/applications", json=payload)
    assert res.status_code == 422


def test_estado_sin_applied_date_falla(client):
    payload = {
        "company": "Acme",
        "position": "Backend",
        "source": "Indeed",
        "found_date": "2026-09-01",
        "job_type": "Backend",
        "status": "Candidatura enviada",  # sin applied_date
    }
    res = client.post("/applications", json=payload)
    assert res.status_code == 422


def test_cambiar_estado_actualiza_max_stage_reached_y_no_baja_al_rechazar(client):
    payload = {
        "company": "Acme",
        "position": "Backend",
        "source": "Indeed",
        "found_date": "2026-09-01",
        "applied_date": "2026-09-02",
        "job_type": "Backend",
        "status": "Candidatura enviada",
    }
    res = client.post("/applications", json=payload)
    app_id = res.json()["id"]

    res = client.patch(f"/applications/{app_id}", json={"status": "Entrevista"})
    assert res.status_code == 200
    assert res.json()["max_stage_reached"] == 3

    res = client.patch(f"/applications/{app_id}", json={"status": "Rechazada"})
    assert res.status_code == 200
    assert res.json()["max_stage_reached"] == 3


def test_filtrar_por_estado(client):
    client.post("/applications", json={
        "company": "A", "position": "Backend", "source": "Indeed",
        "found_date": "2026-09-01", "job_type": "Backend", "status": "Guardada",
    })
    client.post("/applications", json={
        "company": "B", "position": "Backend", "source": "Indeed",
        "found_date": "2026-09-01", "applied_date": "2026-09-02",
        "job_type": "Backend", "status": "Candidatura enviada",
    })
    res = client.get("/applications", params={"status": "Guardada"})
    assert len(res.json()) == 1
    assert res.json()[0]["company"] == "A"
