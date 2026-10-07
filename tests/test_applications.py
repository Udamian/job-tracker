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


def test_cv_version_cv_general_y_legacy_data_engineer(client):
    res1 = client.post("/applications", json={
        "company": "Empresa A",
        "position": "Analista",
        "source": "LinkedIn",
        "found_date": "2026-09-01",
        "job_type": "Python",
        "cv_version": "CV General",
        "status": "Guardada",
    })
    assert res1.status_code == 201
    assert res1.json()["cv_version"] == "CV General"

    # Legado 'Data Engineer' se normaliza a 'CV General'
    res2 = client.post("/applications", json={
        "company": "Empresa B",
        "position": "Analista",
        "source": "LinkedIn",
        "found_date": "2026-09-01",
        "job_type": "Python",
        "cv_version": "Data Engineer",
        "status": "Guardada",
    })
    assert res2.status_code == 201
    assert res2.json()["cv_version"] == "CV General"

    # Filtrar por 'CV General' debe encontrar ambas
    res_list = client.get("/applications", params={"cv_version": "CV General"})
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2


def test_iconos_y_manifest_disponibles(client):
    res_favicon = client.get("/favicon.ico")
    assert res_favicon.status_code == 200

    res_manifest = client.get("/site.webmanifest")
    assert res_manifest.status_code == 200

    res_svg = client.get("/static/icon.svg")
    assert res_svg.status_code == 200


def test_sanitizacion_automatica_strings(client):
    payload = {
        "company": "   Globant Spain   ",
        "position": "   Senior Python Engineer   ",
        "source": "LinkedIn",
        "found_date": "2026-09-01",
        "job_type": "Python",
        "status": "Guardada",
        "location": "  Madrid, Remoto  ",
        "url": "   ",
        "notes": "  "
    }
    res = client.post("/applications", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["company"] == "Globant Spain"
    assert data["position"] == "Senior Python Engineer"
    assert data["location"] == "Madrid, Remoto"
    assert data["url"] is None
    assert data["notes"] is None


def test_exportar_csv(client):
    client.post("/applications", json={
        "company": "Empresa CSV",
        "position": "Data Analyst",
        "source": "LinkedIn",
        "found_date": "2026-09-01",
        "job_type": "Data Analyst",
        "status": "Guardada",
    })
    res = client.get("/applications/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Empresa CSV" in res.text
    assert "Data Analyst" in res.text
