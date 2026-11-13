from datetime import date


def crear(client, **overrides):
    payload = {
        "company": "Empresa",
        "position": "Data Analyst",
        "status": "Enviada",
    }
    payload.update(overrides)
    res = client.post("/applications", json=payload)
    assert res.status_code == 201, res.json()
    return res.json()


def test_kpis_vacio(client):
    data = client.get("/stats/kpis").json()
    assert data["candidaturas_totales"] == 0
    assert data["hoy"] == 0


def test_kpis_con_datos(client):
    crear(client, status="Enviada")
    crear(client, status="Entrevista")

    data = client.get("/stats/kpis").json()
    assert data["candidaturas_totales"] == 2
    assert data["entrevistas"] == 1
    assert data["hoy"] == 2  # ambas se han creado hoy


def test_rechazo_cuenta_como_respuesta_aunque_no_hubiera_contacto(client):
    crear(client, status="Enviada")
    app_id = crear(client, status="Enviada")["id"]
    client.patch(f"/applications/{app_id}", json={"status": "Rechazada"})

    data = client.get("/stats/kpis").json()
    assert data["respuestas"] == 1
    assert data["rechazadas"] == 1


def test_funnel(client):
    crear(client, status="Entrevista")
    etapas = {e["etapa"]: e["cantidad"] for e in client.get("/stats/funnel").json()}
    assert etapas["Enviadas"] == 1
    assert etapas["Contactadas"] == 1
    assert etapas["Entrevistas"] == 1
    assert etapas["Rechazadas"] == 0


def test_respuestas_por_tipo_inferido(client):
    crear(client, position="Ingeniero/a de datos Python-Pyspark", status="Entrevista")
    res = client.get("/stats/by-type").json()
    assert len(res) == 1
    assert res[0]["job_type"] == "Data Engineer"
    assert res[0]["cv_version"] == "Sin especificar"
    assert res[0]["tasa_respuesta"] == 100.0


def test_respuestas_por_tipo_y_cv(client):
    crear(
        client,
        position="Data Analyst",
        status="Entrevista",
        job_type="Data Analyst",
        cv_version="Data",
    )
    res = client.get("/stats/by-type").json()
    assert len(res) == 1
    assert res[0]["tasa_respuesta"] == 100.0


def test_respuestas_por_tipo_y_cv_general(client):
    crear(
        client,
        position="Python",
        status="Entrevista",
        job_type="Python",
        cv_version="CV General",
    )
    crear(
        client,
        position="Python",
        status="Enviada",
        job_type="Python",
        cv_version="Data Engineer",
    )
    res = client.get("/stats/by-type").json()
    assert len(res) == 1
    assert res[0]["cv_version"] == "CV General"
    assert res[0]["candidaturas"] == 2
    assert res[0]["respuestas"] == 1
    assert res[0]["tasa_respuesta"] == 50.0


def test_semana_cuenta_solo_hasta_hoy(client):
    crear(
        client,
        status="Enviada",
        applied_date=date.today().isoformat(),
    )
    data = client.get("/stats/kpis").json()
    assert data["esta_semana"] >= 1
