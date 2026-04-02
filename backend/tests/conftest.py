import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database_manager import database_manager
from app.main import app
from app.runtime.models import RunSpec, WorkflowSpec


@pytest.fixture(scope="function")
def test_db():
    """创建测试数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        engine = create_engine(f"sqlite:///{temp_db_path}")
        from app.runtime.models import Base

        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine
        )

        original_get_db = database_manager.get_db

        def override_get_db():
            try:
                db = TestingSessionLocal()
                yield db
            finally:
                db.close()

        database_manager.get_db = override_get_db

        yield TestingSessionLocal

        database_manager.get_db = original_get_db
        Base.metadata.drop_all(bind=engine)
    finally:
        os.unlink(temp_db_path)


@pytest.fixture(scope="function")
def client(test_db):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_workflow_yaml():
    """返回示例工作流 YAML"""
    return """version: "2.0"
name: "Test Workflow"
description: "A test workflow"

inputs:
  input1:
    type: string
    default: "hello"

nodes:
  start:
    type: start
    name: Start
    outputs:
      - id: input1
        name: Input 1
        type: string

  end:
    type: end
    name: End
    inputs:
      - id: result
        name: Result
        type: string

edges:
  - source: start.input1
    target: end.result
"""
