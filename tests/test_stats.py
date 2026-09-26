def crear(client, **overrides):
    payload = {
        "company": "Empresa",
        "position": "Data Analyst",
        "source": "LinkedIn",
        "found_date": "2026-09-01",
        "job_type": "Data Analyst",
        "cv_version": "Data",
        "status": "Guardada",
    }
    payload.update(overrides)
    res = client.post("/applications", json=payload)
    assert res.status_code == 201, res.json()
    return res.json()


def test_kpis_vacio(client):
    res = client.get("/stats/kpis")
    assert res.json()["candidaturas_totales"] == 0


def test_kpis_con_datos(client):
    crear(client, applied_date="2026-09-02", status="Candidatura enviada")
    crear(client, applied_date="2026-09-02", status="Entrevista")
    crear(client)  # solo "Guardada": no cuenta como candidatura

    data = client.get("/stats/kpis").json()
    assert data["candidaturas_totales"] == 2
    assert data["entrevistas"] == 1


def test_rechazo_cuenta_como_respuesta_aunque_no_hubiera_cv_visto(client):
    crear(client, applied_date="2026-09-02", status="Candidatura enviada")
    app_id = crear(client, applied_date="2026-09-02", status="Candidatura enviada")["id"]
    client.patch(f"/applications/{app_id}", json={"status": "Rechazada"})

    data = client.get("/stats/kpis").json()
    assert data["respuestas"] == 1


def test_funnel(client):
    crear(client, applied_date="2026-09-02", status="Oferta")
    etapas = {e["etapa"]: e["cantidad"] for e in client.get("/stats/funnel").json()}
    assert etapas["Ofertas recibidas"] == 1
    assert etapas["Candidaturas enviadas"] == 1


def test_respuestas_por_tipo_y_cv(client):
    crear(client, applied_date="2026-09-02", status="Entrevista", job_type="Data Analyst", cv_version="Data")
    res = client.get("/stats/by-type").json()
    assert len(res) == 1
    assert res[0]["tasa_respuesta"] == 100.0
