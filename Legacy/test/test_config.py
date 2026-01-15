import tempfile
import os
import yaml
from stupify_phi.config import load_config

def test_load_yaml_config():
    config_data = {"ai_fields": ["doctor_notes", "comments"]}

    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        yaml.dump(config_data, tmp)
        tmp_path = tmp.name

    config = load_config(tmp_path)
    assert "ai_fields" in config
    assert config["ai_fields"] == ["doctor_notes", "comments"]
    os.unlink(tmp_path)
