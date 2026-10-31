from tests.conftest import needs_sample_video, register

CAM = {"name": "Main Entrance", "location": "Lobby", "source_type": "file", "source": "sample.mp4"}


def test_camera_crud(client, auth_headers):
    # create
    res = client.post("/cameras", json=CAM, headers=auth_headers)
    assert res.status_code == 201
    cam = res.json()
    assert cam["status"] == "idle"
    assert cam["line"] == {"x1": 0.0, "y1": 0.5, "x2": 1.0, "y2": 0.5}
    cam_id = cam["id"]

    # list + get
    assert len(client.get("/cameras", headers=auth_headers).json()) == 1
    assert client.get(f"/cameras/{cam_id}", headers=auth_headers).json()["name"] == "Main Entrance"

    # update (partial) + deactivate
    res = client.put(f"/cameras/{cam_id}", json={"location": "Front door", "is_active": False}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["location"] == "Front door"
    assert res.json()["is_active"] is False
    assert res.json()["name"] == "Main Entrance"

    # delete
    assert client.delete(f"/cameras/{cam_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/cameras/{cam_id}", headers=auth_headers).status_code == 404


def test_camera_requires_auth(client):
    assert client.get("/cameras").status_code == 401


def test_camera_not_found_and_bad_id(client, auth_headers):
    assert client.get("/cameras/000000000000000000000000", headers=auth_headers).status_code == 404
    assert client.get("/cameras/not-an-id", headers=auth_headers).status_code == 404


def test_duplicate_camera_name(client, auth_headers):
    client.post("/cameras", json=CAM, headers=auth_headers)
    assert client.post("/cameras", json=CAM, headers=auth_headers).status_code == 409


def test_source_validation(client, auth_headers):
    bad_webcam = {**CAM, "source_type": "webcam", "source": "abc"}
    assert client.post("/cameras", json=bad_webcam, headers=auth_headers).status_code == 422
    bad_rtsp = {**CAM, "source_type": "rtsp", "source": "http://x"}
    assert client.post("/cameras", json=bad_rtsp, headers=auth_headers).status_code == 422
    ok_rtsp = {**CAM, "source_type": "rtsp", "source": "rtsp://10.0.0.5:554/stream1"}
    assert client.post("/cameras", json=ok_rtsp, headers=auth_headers).status_code == 201

    # update that switches type without fixing source is rejected
    cam_id = client.get("/cameras", headers=auth_headers).json()[0]["id"]
    res = client.put(f"/cameras/{cam_id}", json={"source_type": "webcam"}, headers=auth_headers)
    assert res.status_code == 422


def test_users_cannot_see_each_others_cameras(client, auth_headers):
    cam_id = client.post("/cameras", json=CAM, headers=auth_headers).json()["id"]
    bob_token = register(client, email="bob@example.com").json()["access_token"]
    bob = {"Authorization": f"Bearer {bob_token}"}
    assert client.get("/cameras", headers=bob).json() == []
    assert client.get(f"/cameras/{cam_id}", headers=bob).status_code == 404
    assert client.delete(f"/cameras/{cam_id}", headers=bob).status_code == 404


def test_start_rejects_missing_file_and_inactive_camera(client, auth_headers):
    cam = client.post("/cameras", json={**CAM, "source": "does-not-exist.mp4"}, headers=auth_headers).json()
    res = client.post(f"/cameras/{cam['id']}/start", headers=auth_headers)
    assert res.status_code == 422
    assert "not found" in res.json()["detail"]

    client.put(f"/cameras/{cam['id']}", json={"is_active": False}, headers=auth_headers)
    assert client.post(f"/cameras/{cam['id']}/start", headers=auth_headers).status_code == 422


def test_live_and_stream_when_not_running(client, auth_headers):
    cam_id = client.post("/cameras", json=CAM, headers=auth_headers).json()["id"]
    assert client.get(f"/cameras/{cam_id}/live", headers=auth_headers).status_code == 409
    token = auth_headers["Authorization"].split()[1]
    assert client.get(f"/cameras/{cam_id}/stream?token={token}").status_code == 409
    assert client.get(f"/cameras/{cam_id}/stream?token=bad").status_code == 401
    # stopping a camera that isn't running is a harmless no-op
    assert client.post(f"/cameras/{cam_id}/stop", headers=auth_headers).status_code == 204


def test_presence_tracking_events_empty(client, auth_headers):
    assert client.get("/presence/current", headers=auth_headers).json()["running_cameras"] == 0
    assert client.get("/tracking", headers=auth_headers).json() == {"items": [], "total": 0, "skip": 0, "limit": 50}
    assert client.get("/events?type=entry", headers=auth_headers).json()["total"] == 0
    assert client.get("/detections", headers=auth_headers).json() == []


def test_file_source_cannot_escape_video_dir(client, auth_headers):
    for bad in ["/etc/passwd", "../app/main.py", "a/../../x.mp4"]:
        res = client.post("/cameras", json={**CAM, "name": bad, "source": bad}, headers=auth_headers)
        assert res.status_code == 422, bad


@needs_sample_video
def test_snapshot_of_file_camera(client, auth_headers):
    cam_id = client.post("/cameras", json={**CAM, "source": "people-detection.mp4"}, headers=auth_headers).json()["id"]
    token = auth_headers["Authorization"].split()[1]
    res = client.get(f"/cameras/{cam_id}/snapshot?token={token}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    assert res.content[:2] == b"\xff\xd8"
