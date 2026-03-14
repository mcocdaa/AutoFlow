import json
from app.main import app
from fastapi.testclient import TestClient

flow_yaml = """
version: "1"
name: "foreach_test"
vars:
  items:
    - "a"
    - "b"
    - "c"
steps:
  - id: "loop"
    action:
      type: "dummy.echo"
      params:
        message: "{{vars.item}}"
    for_each: "{{vars.items}}"
    for_item_var: "item"
""".lstrip()

client = TestClient(app)
resp = client.post('/api/v1/runs/execute', json={'flow_yaml': flow_yaml})
print('Status:', resp.status_code)
print('Response:', resp.text)