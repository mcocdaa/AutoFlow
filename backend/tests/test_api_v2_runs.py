import pytest


class TestTriggerRun:
    def test_trigger_run_success(self, client, sample_workflow_yaml):
        """测试成功触发执行"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        trigger_response = client.post(
            f"/v2/workflows/{workflow_id}/runs",
            json={"inputs": {"param1": "value1"}},
        )
        assert trigger_response.status_code == 200
        data = trigger_response.json()
        assert "run_id" in data
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "running"
        assert "started_at" in data

    def test_trigger_run_workflow_not_found(self, client):
        """测试触发不存在的工作流执行"""
        response = client.post(
            "/v2/workflows/nonexistent-id/runs",
            json={"inputs": {}},
        )
        assert response.status_code == 404


class TestGetRun:
    def test_get_run_success(self, client, sample_workflow_yaml):
        """测试成功获取执行状态"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        trigger_response = client.post(
            f"/v2/workflows/{workflow_id}/runs",
            json={"inputs": {}},
        )
        run_id = trigger_response.json()["run_id"]

        get_response = client.get(f"/v2/runs/{run_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["run_id"] == run_id
        assert data["workflow_id"] == workflow_id
        assert data["status"] == "running"

    def test_get_run_not_found(self, client):
        """测试获取不存在的执行"""
        response = client.get("/v2/runs/nonexistent-id")
        assert response.status_code == 404


class TestCancelRun:
    def test_cancel_run_success(self, client, sample_workflow_yaml):
        """测试成功取消执行"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        trigger_response = client.post(
            f"/v2/workflows/{workflow_id}/runs",
            json={"inputs": {}},
        )
        run_id = trigger_response.json()["run_id"]

        cancel_response = client.post(f"/v2/runs/{run_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["success"] is True

    def test_cancel_run_not_found(self, client):
        """测试取消不存在的执行"""
        response = client.post("/v2/runs/nonexistent-id/cancel")
        assert response.status_code == 404


class TestPauseRun:
    def test_pause_run_success(self, client, sample_workflow_yaml):
        """测试成功暂停执行"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        trigger_response = client.post(
            f"/v2/workflows/{workflow_id}/runs",
            json={"inputs": {}},
        )
        run_id = trigger_response.json()["run_id"]

        pause_response = client.post(f"/v2/runs/{run_id}/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["success"] is True

    def test_pause_run_not_found(self, client):
        """测试暂停不存在的执行"""
        response = client.post("/v2/runs/nonexistent-id/pause")
        assert response.status_code == 404


class TestResumeRun:
    def test_resume_run_success(self, client, sample_workflow_yaml):
        """测试成功继续执行"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        trigger_response = client.post(
            f"/v2/workflows/{workflow_id}/runs",
            json={"inputs": {}},
        )
        run_id = trigger_response.json()["run_id"]

        resume_response = client.post(f"/v2/runs/{run_id}/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["success"] is True

    def test_resume_run_not_found(self, client):
        """测试继续不存在的执行"""
        response = client.post("/v2/runs/nonexistent-id/resume")
        assert response.status_code == 404


class TestListRuns:
    def test_list_runs_empty(self, client, sample_workflow_yaml):
        """测试空执行历史"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        response = client.get(f"/v2/workflows/{workflow_id}/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["runs"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_runs_with_items(self, client, sample_workflow_yaml):
        """测试列出执行历史"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        for _ in range(3):
            client.post(
                f"/v2/workflows/{workflow_id}/runs",
                json={"inputs": {}},
            )

        response = client.get(f"/v2/workflows/{workflow_id}/runs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 3
        assert data["total"] == 3

    def test_list_runs_pagination(self, client, sample_workflow_yaml):
        """测试执行历史分页"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        for _ in range(25):
            client.post(
                f"/v2/workflows/{workflow_id}/runs",
                json={"inputs": {}},
            )

        response = client.get(f"/v2/workflows/{workflow_id}/runs?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["runs"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 10

        response = client.get(f"/v2/workflows/{workflow_id}/runs?page=3&page_size=10")
        assert len(response.json()["runs"]) == 5

    def test_list_runs_workflow_not_found(self, client):
        """测试列出不存在工作流的执行历史"""
        response = client.get("/v2/workflows/nonexistent-id/runs")
        assert response.status_code == 404
