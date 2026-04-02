import pytest


class TestCreateWorkflow:
    def test_create_workflow_success(self, client, sample_workflow_yaml):
        """测试成功创建工作流"""
        response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Workflow"
        assert data["description"] == "A test workflow"
        assert data["yaml"] == sample_workflow_yaml
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_workflow_invalid_yaml(self, client):
        """测试创建工作流时使用无效的 YAML"""
        response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "yaml": "invalid yaml: :",
            },
        )
        assert response.status_code == 400

    def test_create_workflow_missing_fields(self, client):
        """测试创建工作流时缺少必填字段"""
        response = client.post(
            "/v2/workflows",
            json={
                "description": "A test workflow",
            },
        )
        assert response.status_code == 422


class TestGetWorkflow:
    def test_get_workflow_success(self, client, sample_workflow_yaml):
        """测试成功获取工作流"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        get_response = client.get(f"/v2/workflows/{workflow_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == workflow_id
        assert data["name"] == "Test Workflow"

    def test_get_workflow_not_found(self, client):
        """测试获取不存在的工作流"""
        response = client.get("/v2/workflows/nonexistent-id")
        assert response.status_code == 404


class TestUpdateWorkflow:
    def test_update_workflow_success(self, client, sample_workflow_yaml):
        """测试成功更新工作流"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        updated_yaml = sample_workflow_yaml.replace("Test Workflow", "Updated Workflow")
        update_response = client.put(
            f"/v2/workflows/{workflow_id}",
            json={
                "name": "Updated Workflow",
                "description": "An updated test workflow",
                "yaml": updated_yaml,
            },
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["id"] == workflow_id
        assert data["name"] == "Updated Workflow"
        assert data["description"] == "An updated test workflow"

    def test_update_workflow_not_found(self, client):
        """测试更新不存在的工作流"""
        response = client.put(
            "/v2/workflows/nonexistent-id",
            json={
                "name": "Updated Workflow",
            },
        )
        assert response.status_code == 404

    def test_update_workflow_partial(self, client, sample_workflow_yaml):
        """测试部分更新工作流"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        update_response = client.put(
            f"/v2/workflows/{workflow_id}",
            json={
                "name": "Partially Updated",
            },
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["name"] == "Partially Updated"
        assert data["description"] == "A test workflow"


class TestDeleteWorkflow:
    def test_delete_workflow_success(self, client, sample_workflow_yaml):
        """测试成功删除工作流"""
        create_response = client.post(
            "/v2/workflows",
            json={
                "name": "Test Workflow",
                "description": "A test workflow",
                "yaml": sample_workflow_yaml,
            },
        )
        workflow_id = create_response.json()["id"]

        delete_response = client.delete(f"/v2/workflows/{workflow_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        get_response = client.get(f"/v2/workflows/{workflow_id}")
        assert get_response.status_code == 404

    def test_delete_workflow_not_found(self, client):
        """测试删除不存在的工作流"""
        response = client.delete("/v2/workflows/nonexistent-id")
        assert response.status_code == 404


class TestListWorkflows:
    def test_list_workflows_empty(self, client):
        """测试空列表"""
        response = client.get("/v2/workflows")
        assert response.status_code == 200
        data = response.json()
        assert data["workflows"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_workflows_with_items(self, client, sample_workflow_yaml):
        """测试列出工作流"""
        for i in range(3):
            client.post(
                "/v2/workflows",
                json={
                    "name": f"Workflow {i}",
                    "description": f"Description {i}",
                    "yaml": sample_workflow_yaml,
                },
            )

        response = client.get("/v2/workflows")
        assert response.status_code == 200
        data = response.json()
        assert len(data["workflows"]) == 3
        assert data["total"] == 3

    def test_list_workflows_pagination(self, client, sample_workflow_yaml):
        """测试分页"""
        for i in range(25):
            client.post(
                "/v2/workflows",
                json={
                    "name": f"Workflow {i}",
                    "yaml": sample_workflow_yaml,
                },
            )

        response = client.get("/v2/workflows?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["workflows"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 10

        response = client.get("/v2/workflows?page=3&page_size=10")
        assert len(response.json()["workflows"]) == 5

    def test_list_workflows_search(self, client, sample_workflow_yaml):
        """测试搜索"""
        client.post(
            "/v2/workflows",
            json={
                "name": "Special Workflow",
                "description": "This is special",
                "yaml": sample_workflow_yaml,
            },
        )
        client.post(
            "/v2/workflows",
            json={
                "name": "Regular Workflow",
                "description": "This is regular",
                "yaml": sample_workflow_yaml,
            },
        )

        response = client.get("/v2/workflows?search=Special")
        assert response.status_code == 200
        data = response.json()
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["name"] == "Special Workflow"
