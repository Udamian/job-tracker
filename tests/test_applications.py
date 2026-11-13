from datetime import date, timedelta


def test_crear_con_solo_empresa_y_puesto(client):
    res = client.post("/applications", json={"company": "Acme", "position": "Backend Python"})
    assert res.status_code == 201, res.json()
    data = res.json()

    assert data["company"] == "Acme"
    assert data["position"] == "Backend Python"
    assert data["status"] == "Enviada"
    assert data["job_type"] == "Python"  # inferido del texto
    assert data["found_date"] == date.today().isoformat()
    assert data["applied_date"] == date.today().isoformat()
    assert data["max_stage_reached"] == 1
    assert data["source"] is None
    assert data["cv_version"] is None
    assert data["modality"] is None


def test_estados_legados_se_normalizan(client):
    esperado = {
        "Guardada": "Enviada",
        "Candidatura enviada": "Enviada",
        "Sin respuesta": "Enviada",
        "CV visto": "Contactado",
        "Prueba técnica": "Entrevista",
        "Oferta": "Entrevista",
    }
    for viejo, nuevo in esperado.items():
        res = client.post(
            "/applications",
            json={"company": f"Empresa {viejo}", "position": "Backend", "status": viejo},
        )
        assert res.status_code == 201, res.json()
        assert res.json()["status"] == nuevo

    # Todos los estados nuevos son válidos y dejan fecha de candidatura.
    for estado in ("Enviada", "Contactado", "Entrevista", "Rechazada"):
        res = client.post(
            "/applications",
            json={"company": f"Empresa {estado}", "position": "Backend", "status": estado},
        )
        assert res.status_code == 201, res.json()
        assert res.json()["status"] == estado
        assert res.json()["applied_date"] == date.today().isoformat()


def test_captura_retroactiva_ayer(client):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    res = client.post(
        "/applications",
        json={"company": "Acme", "position": "Data Analyst", "applied_date": ayer},
    )
    assert res.status_code == 201, res.json()
    data = res.json()
    assert data["applied_date"] == ayer
    assert data["found_date"] == ayer
    assert data["job_type"] == "Data Analyst"


def test_campos_antiguos_siguen_siendo_opcionales(client):
    res = client.post(
        "/applications",
        json={
            "company": "Acme",
            "position": "Backend",
            "source": "LinkedIn",
            "modality": "Híbrido",
            "location": "Madrid",
            "cv_version": "Backend",
            "url": "https://example.com/oferta",
            "notes": "Contacto por LinkedIn",
        },
    )
    assert res.status_code == 201, res.json()
    data = res.json()
    assert data["source"] == "LinkedIn"
    assert data["modality"] == "Híbrido"
    assert data["location"] == "Madrid"
    assert data["cv_version"] == "Backend"
    assert data["url"] == "https://example.com/oferta"
    assert data["notes"] == "Contacto por LinkedIn"


def test_estados_nuevos_se_pueden_fijar_a_mano(client):
    res = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend", "status": "Contactado"},
    )
    assert res.status_code == 201, res.json()
    assert res.json()["status"] == "Contactado"
    assert res.json()["max_stage_reached"] == 2


def test_cambiar_estado_actualiza_max_stage_reached_y_no_baja_al_rechazar(client):
    res = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend", "status": "Enviada"},
    )
    app_id = res.json()["id"]

    res = client.patch(f"/applications/{app_id}", json={"status": "Entrevista"})
    assert res.status_code == 200
    assert res.json()["max_stage_reached"] == 3

    res = client.patch(f"/applications/{app_id}", json={"status": "Rechazada"})
    assert res.status_code == 200
    assert res.json()["max_stage_reached"] == 3


def test_filtrar_por_estado(client):
    client.post(
        "/applications",
        json={"company": "A", "position": "Backend", "status": "Enviada"},
    )
    client.post(
        "/applications",
        json={"company": "B", "position": "Backend", "status": "Contactado"},
    )
    res = client.get("/applications", params={"status": "Contactado"})
    assert len(res.json()) == 1
    assert res.json()[0]["company"] == "B"


def test_sugerencias_de_empresas_y_puestos(client):
    client.post("/applications", json={"company": "Stripe", "position": "Backend Python"})
    client.post("/applications", json={"company": "Stripe", "position": "Data Analyst"})
    client.post("/applications", json={"company": "Cabify", "position": "Backend Java"})

    res = client.get("/applications/suggestions", params={"q": "str"})
    assert res.status_code == 200
    data = res.json()
    assert data["companies"] == ["Stripe"]
    assert data["positions"] == []

    res = client.get("/applications/suggestions", params={"q": "back"})
    assert "Backend Python" in res.json()["positions"]


def test_aviso_de_duplicado(client):
    ayer = (date.today() - timedelta(days=12)).isoformat()
    client.post(
        "/applications",
        json={"company": "Stripe", "position": "Backend", "applied_date": ayer},
    )
    res = client.get(
        "/applications/check",
        params={"company": "stripe", "position": "Backend"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["duplicate"] is True
    assert "12 días" in data["message"]
    assert data["matches"][0]["company"] == "Stripe"


def test_panel_requiere_atencion_y_acciones(client):
    viejo = (date.today() - timedelta(days=30)).isoformat()
    res = client.post(
        "/applications",
        json={"company": "Old Co", "position": "Backend", "applied_date": viejo},
    )
    app_id = res.json()["id"]

    atencion = client.get("/applications/attention").json()
    assert len(atencion) == 1
    assert atencion[0]["id"] == app_id
    assert atencion[0]["days_waiting"] >= 21

    # Hacer seguimiento reinicia el contador.
    res = client.patch(f"/applications/{app_id}", json={"follow_up_date": date.today().isoformat()})
    assert res.status_code == 200
    assert client.get("/applications/attention").json() == []

    # Y marcarla como rechazada también la saca de la lista.
    client.patch(f"/applications/{app_id}", json={"follow_up_date": None})
    assert len(client.get("/applications/attention").json()) == 1
    client.patch(f"/applications/{app_id}", json={"status": "Rechazada"})
    assert client.get("/applications/attention").json() == []


def test_deshacer_borrado_restaura_id_y_etapa(client):
    res = client.post(
        "/applications",
        json={"company": "Acme", "position": "Backend", "status": "Entrevista"},
    )
    original = res.json()
    assert original["max_stage_reached"] == 3

    borrada = client.delete(f"/applications/{original['id']}")
    assert borrada.status_code == 200
    payload = borrada.json()
    assert payload["id"] == original["id"]
    assert payload["max_stage_reached"] == 3

    restaurada = client.post("/applications/restore", json=payload)
    assert restaurada.status_code == 201, restaurada.json()
    assert restaurada.json()["id"] == original["id"]
    assert restaurada.json()["max_stage_reached"] == 3
    assert client.get(f"/applications/{original['id']}").status_code == 200


def test_cv_version_cv_general_y_legacy_data_engineer(client):
    res1 = client.post(
        "/applications",
        json={
            "company": "Empresa A",
            "position": "Analista",
            "cv_version": "CV General",
            "status": "Enviada",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["cv_version"] == "CV General"

    # Legado 'Data Engineer' se normaliza a 'CV General'
    res2 = client.post(
        "/applications",
        json={
            "company": "Empresa B",
            "position": "Analista",
            "cv_version": "Data Engineer",
            "status": "Enviada",
        },
    )
    assert res2.status_code == 201
    assert res2.json()["cv_version"] == "CV General"

    res_list = client.get("/applications", params={"cv_version": "CV General"})
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2


def test_cv_version_java_junior(client):
    res1 = client.post(
        "/applications",
        json={
            "company": "Empresa Java 1",
            "position": "Junior Java Developer",
            "cv_version": "Java Junior",
        },
    )
    assert res1.status_code == 201
    assert res1.json()["cv_version"] == "Java Junior"

    res2 = client.post(
        "/applications",
        json={
            "company": "Empresa Java 2",
            "position": "Java Jr",
            "cv_version": "java junior",
        },
    )
    assert res2.status_code == 201
    assert res2.json()["cv_version"] == "Java Junior"

    res_filter = client.get("/applications", params={"cv_version": "Java Junior"})
    assert res_filter.status_code == 200
    assert len(res_filter.json()) == 2


def test_inferencia_de_tipo_de_puesto(client):
    casos = {
        "Analista de Datos Junior / Python": "Data Analyst",
        "Ingeniero/a de datos Python-Pyspark": "Data Engineer",
        "Desarrollador/a Python": "Python",
        "Junior Java": "Backend",
        "Formativo": "Otro",
    }
    for puesto, esperado in casos.items():
        res = client.post("/applications", json={"company": "X", "position": puesto})
        assert res.status_code == 201, res.json()
        assert res.json()["job_type"] == esperado, puesto


def test_iconos_y_manifest_disponibles(client):
    assert client.get("/favicon.ico").status_code == 200
    assert client.get("/site.webmanifest").status_code == 200
    assert client.get("/static/icon.svg").status_code == 200


def test_sanitizacion_automatica_strings(client):
    res = client.post(
        "/applications",
        json={
            "company": "   Globant Spain   ",
            "position": "   Senior Python Engineer   ",
            "location": "  Madrid, Remoto  ",
            "url": "   ",
            "notes": "  ",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["company"] == "Globant Spain"
    assert data["position"] == "Senior Python Engineer"
    assert data["location"] == "Madrid, Remoto"
    assert data["url"] is None
    assert data["notes"] is None


def test_exportar_csv(client):
    client.post(
        "/applications",
        json={"company": "Empresa CSV", "position": "Data Analyst", "status": "Enviada"},
    )
    res = client.get("/applications/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "Empresa CSV" in res.text
    assert "Data Analyst" in res.text
    assert "Etapa máxima" in res.text
