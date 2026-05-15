import json
import os
import re
from datetime import datetime
from typing import Optional

from src.data_models import OperationSequence
from src.logger import log_info, log_error


class TemplateManager:
    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir is None:
            templates_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "templates"
            )
        self._templates_dir = templates_dir
        os.makedirs(self._templates_dir, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        return re.sub(r'[\\/:*?"<>|]', "_", name)

    def _template_path(self, name: str) -> str:
        return os.path.join(self._templates_dir, self._sanitize_name(name) + ".json")

    def create_template(self, name: str, sequence: OperationSequence) -> bool:
        try:
            data = {
                "name": name,
                "created_at": datetime.now().isoformat(),
                "operations": [op.to_dict() for op in sequence.operations],
            }
            path = self._template_path(name)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            log_info(f"模板已保存: {name}", "TemplateManager")
            return True
        except Exception as e:
            log_error(f"保存模板失败: {e}", "TemplateManager")
            return False

    def delete_template(self, name: str) -> bool:
        path = self._template_path(name)
        try:
            if os.path.exists(path):
                os.remove(path)
                log_info(f"模板已删除: {name}", "TemplateManager")
                return True
            return False
        except Exception as e:
            log_error(f"删除模板失败: {e}", "TemplateManager")
            return False

    def list_templates(self) -> list[dict]:
        templates = []
        if not os.path.exists(self._templates_dir):
            return templates
        for filename in os.listdir(self._templates_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(self._templates_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                templates.append({
                    "name": data.get("name", filename[:-5]),
                    "created_at": data.get("created_at", ""),
                    "operation_count": len(data.get("operations", [])),
                })
            except Exception:
                continue
        return templates

    def get_template(self, name: str) -> Optional[OperationSequence]:
        path = self._template_path(name)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return OperationSequence.from_dict(data)
        except Exception as e:
            log_error(f"加载模板失败: {e}", "TemplateManager")
            return None

    def template_exists(self, name: str) -> bool:
        return os.path.exists(self._template_path(name))
