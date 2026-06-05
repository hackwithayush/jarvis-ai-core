"""
Jarvis v15.0 — Dynamic Skills Registry & Schema Validator
Dynamically discovers, validates, and governs composite orchestration behaviors
loaded from the skills directory using robust standard JSON schema matches.
"""
import os
import sys
import json
import importlib.util
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("jarvis.skills_registry")

class SkillsRegistry:
    """Discovers, validates, and runs modular orchestration skills."""

    def __init__(self, skills_dir: str = None, schemas_dir: str = None):
        cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if not skills_dir:
            skills_dir = os.path.join(cwd, "skills")
        if not schemas_dir:
            schemas_dir = os.path.join(cwd, "data", "schemas")

        self.skills_dir = skills_dir
        self.schemas_dir = schemas_dir
        self.skills: Dict[str, Dict[str, Any]] = {} # skill_id -> {manifest, module, path}
        self._validation_hooks: Dict[str, Any] = {} # hook_name -> callable
        
        os.makedirs(self.skills_dir, exist_ok=True)
        self.skill_schema = self._load_schema("skill_definition_schema.json")

    def _load_schema(self, filename: str) -> Optional[dict]:
        """Loads a JSON validation schema from data/schemas."""
        schema_path = os.path.join(self.schemas_dir, filename)
        if os.path.exists(schema_path):
            try:
                with open(schema_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[SKILLS] Failed to read schema {filename}: {e}")
        return None

    def register_validation_hook(self, name: str, hook_fn):
        """Allows external validation plugins to register custom matching rules."""
        self._validation_hooks[name] = hook_fn
        logger.info(f"[SKILLS] Registered external validation hook: '{name}'")

    def validate_manifest(self, manifest: dict) -> bool:
        """
        Validates the skill's manifest dictionary against the JSON schema contract.
        Supports standard jsonschema library if present, else falls back to robust validation rules.
        """
        if not manifest or not isinstance(manifest, dict):
            return False

        # 1. Try using standard jsonschema library if installed
        try:
            import jsonschema
            if self.skill_schema:
                jsonschema.validate(instance=manifest, schema=self.skill_schema)
                # Run external hooks if present
                for hook_name, hook_fn in self._validation_hooks.items():
                    if not hook_fn(manifest):
                        logger.error(f"[SKILLS VALIDATION] External validation hook '{hook_name}' failed.")
                        return False
                return True
        except ImportError:
            pass  # Fallback to local robust schema matching rules
        except Exception as schema_err:
            logger.error(f"[SKILLS VALIDATION] jsonschema engine validation failed: {schema_err}")
            return False

        # 2. Local Fallback Schema Validation Rules
        required_fields = ["skill_id", "name", "description", "required_clearance", "required_capabilities"]
        for field in required_fields:
            if field not in manifest:
                logger.error(f"[SKILLS VALIDATION] Missing required manifest field: '{field}'")
                return False

        # Regex-like alphanumeric underscore check for skill_id
        skill_id = manifest.get("skill_id", "")
        if not skill_id or not all(c.isalnum() or c == '_' for c in skill_id):
            logger.error(f"[SKILLS VALIDATION] skill_id '{skill_id}' must be alphanumeric and underscores only.")
            return False

        if manifest.get("required_clearance") not in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            logger.error(f"[SKILLS VALIDATION] Invalid clearance level: {manifest.get('required_clearance')}")
            return False

        if not isinstance(manifest.get("required_capabilities"), list):
            logger.error("[SKILLS VALIDATION] 'required_capabilities' must be a list.")
            return False

        # Deep Parameters Validation matching schema parameters properties block
        parameters = manifest.get("parameters", {})
        if not isinstance(parameters, dict):
            logger.error("[SKILLS VALIDATION] 'parameters' must be an object dictionary.")
            return False

        for param_name, param_meta in parameters.items():
            if not isinstance(param_meta, dict):
                logger.error(f"[SKILLS VALIDATION] Parameter metadata for '{param_name}' must be a dictionary.")
                return False
            
            p_type = param_meta.get("type")
            p_desc = param_meta.get("description")
            
            if not p_type or p_type not in ["string", "number", "boolean", "object", "array"]:
                logger.error(f"[SKILLS VALIDATION] Parameter '{param_name}' has invalid type '{p_type}'.")
                return False
                
            if not p_desc or not isinstance(p_desc, str):
                logger.error(f"[SKILLS VALIDATION] Parameter '{param_name}' must present a valid string description.")
                return False

        # 3. Execute all registered pluggable custom validation hooks
        for hook_name, hook_fn in self._validation_hooks.items():
            try:
                if not hook_fn(manifest):
                    logger.error(f"[SKILLS VALIDATION] External validation hook '{hook_name}' failed.")
                    return False
            except Exception as hook_err:
                logger.error(f"[SKILLS VALIDATION] Exception executing hook '{hook_name}': {hook_err}")
                return False

        return True

    def discover_and_load_skills(self):
        """Scans the skills directory, dynamically imports Python skill modules, and registers them."""
        logger.info(f"[SKILLS] Discovering modular skills in: {self.skills_dir}")
        self.skills.clear()

        if not os.path.exists(self.skills_dir):
            return

        for filename in os.listdir(self.skills_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                skill_path = os.path.join(self.skills_dir, filename)
                module_name = f"skills.{filename[:-3]}"
                
                try:
                    # AST Security Scan Before Loading (Upgrade 4)
                    import ast
                    with open(skill_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    
                    is_safe = True
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                            if node.func.id in ["eval", "exec", "open"]:
                                logger.error(f"[SKILLS SECURITY] Blocked load of {filename}: Contains banned built-in '{node.func.id}'")
                                is_safe = False
                                break
                        # Also block subprocess imports for extra safety
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name in ["subprocess", "os", "sys", "pty", "socket"]:
                                    logger.error(f"[SKILLS SECURITY] Blocked load of {filename}: Contains banned import '{alias.name}'")
                                    is_safe = False
                                    break
                        if isinstance(node, ast.ImportFrom):
                            if node.module in ["subprocess", "os", "sys", "pty", "socket"]:
                                logger.error(f"[SKILLS SECURITY] Blocked load of {filename}: Contains banned import '{node.module}'")
                                is_safe = False
                                break
                    if not is_safe:
                        continue

                    # Dynamically load the module
                    spec = importlib.util.spec_from_file_location(module_name, skill_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)

                    # Extract manifest and action callback
                    if not hasattr(module, "MANIFEST"):
                        logger.warning(f"[SKILLS] Skill {filename} skipped: Missing MANIFEST dictionary.")
                        continue
                    if not hasattr(module, "execute"):
                        logger.warning(f"[SKILLS] Skill {filename} skipped: Missing execute() function.")
                        continue

                    manifest = getattr(module, "MANIFEST")
                    if self.validate_manifest(manifest):
                        skill_id = manifest["skill_id"]
                        self.skills[skill_id] = {
                            "manifest": manifest,
                            "module": module,
                            "path": skill_path
                        }
                        logger.info(f"[SKILLS] Registered valid skill '{skill_id}' from {filename}")
                    else:
                        logger.error(f"[SKILLS] Failed manifest validation for {filename}")

                except Exception as e:
                    logger.error(f"[SKILLS] Failed to load skill module {filename}: {e}")

    def get_skill(self, skill_id: str) -> Optional[dict]:
        """Retrieves a registered skill definition by its unique identifier."""
        return self.skills.get(skill_id)

    def execute_skill(self, skill_id: str, context: dict) -> dict:
        """
        Runs a skill behavior if governance clearance check passes.
        Context expects: {'clearance_level': 'HIGH', 'args': {...}}
        """
        skill_entry = self.get_skill(skill_id)
        if not skill_entry:
            return {"success": False, "error": f"Skill '{skill_id}' is not registered."}

        manifest = skill_entry["manifest"]
        clearance = context.get("clearance_level", "LOW")
        
        # Governance Gate Check using PolicyEngine
        from core.policy_engine import policy_engine
        
        # Verify clearance holds all required capabilities
        denied_caps = []
        for cap in manifest.get("required_capabilities", []):
            if not policy_engine.verify_capability(clearance, cap):
                denied_caps.append(cap)
                
        if denied_caps:
            err_msg = f"Access Denied: Clearance level '{clearance}' lacks required capabilities: {', '.join(denied_caps)}."
            logger.warning(f"[SKILLS GATING] Execution blocked for '{skill_id}': {err_msg}")
            return {
                "success": False,
                "error": err_msg,
                "required_capabilities": manifest.get("required_capabilities"),
                "missing_capabilities": denied_caps
            }

        # Issue execution clearance tokens behind the scenes for filesystem/process skills!
        tokens = {}
        for cap in manifest.get("required_capabilities", []):
            token = policy_engine.issue_execution_token(f"SkillExecutor_{skill_id}", cap, clearance)
            if token:
                tokens[cap] = token

        # Invoke the skill's composite execute function
        logger.info(f"[SKILLS RUN] Executing skill '{skill_id}' under clear-level '{clearance}'...")
        try:
            skill_args = context.get("args", {})
            # Pass verified tokens for secure operations!
            result = skill_entry["module"].execute(skill_args, tokens)
            return {
                "success": True,
                "skill_id": skill_id,
                "result": result
            }
        except Exception as e:
            logger.exception(f"Skill '{skill_id}' encountered exception during execute")
            return {
                "success": False,
                "error": f"Exception during skill execution: {e}"
            }

    def ingest_zip_skill_pack(self, zip_path: str, expected_checksum: Optional[str] = None) -> dict:
        """
        Cryptographically validates and securely ingests a dynamic zip skill pack.
        Enforces SHA-256 validation and Zip-Slip traversal defenses.
        """
        import hashlib
        import zipfile
        
        # 1. Compute SHA-256 checksum and validate if expected
        sha256_hash = hashlib.sha256()
        try:
            with open(zip_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            checksum = sha256_hash.hexdigest()
            logger.info(f"[SKILLS REGISTRY] Zip file '{zip_path}' SHA-256: {checksum}")
            
            if expected_checksum and checksum.lower() != expected_checksum.lower():
                return {
                    "success": False,
                    "error": f"Cryptographic mismatch: Expected checksum '{expected_checksum}', but calculated '{checksum}'."
                }
        except Exception as e:
            return {"success": False, "error": f"Failed to compute file checksum: {e}"}

        # 2. Inspect Zip archive securely (Zip-Slip defense)
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                # Resolve the base directory absolutely
                base_dir = os.path.abspath(self.skills_dir)
                
                # Check all entries
                for member in z.infolist():
                    target_path = os.path.abspath(os.path.join(base_dir, member.filename))
                    if not target_path.startswith(base_dir + os.sep) and target_path != base_dir:
                        logger.error(f"[SKILLS REGISTRY] Security Alert: Prevented Zip-Slip path traversal for entry '{member.filename}' trying to write to '{target_path}'.")
                        return {
                            "success": False,
                            "error": f"Security Alert: Directory traversal detected in zip file for entry '{member.filename}'."
                        }
                
                # Verify that there is at least one compliant python file that has a MANIFEST and execute function
                has_valid_module = False
                for member in z.infolist():
                    if member.filename.endswith(".py") and not member.filename.startswith("__"):
                        has_valid_module = True
                
                if not has_valid_module:
                    return {"success": False, "error": "Zip pack skipped: Missing a valid Python (.py) skill module."}
                
                # Perform secure extraction
                z.extractall(base_dir)
                logger.info(f"[SKILLS REGISTRY] Securely extracted zip pack '{zip_path}' to '{base_dir}'.")
        except Exception as e:
            logger.error(f"[SKILLS REGISTRY] Failed to extract zip: {e}")
            return {"success": False, "error": f"Extraction failure: {e}"}
            
        # 3. Reload discover_and_load_skills to load new skills dynamically
        self.discover_and_load_skills()
        return {"success": True, "checksum": checksum}

# Global singleton skills registry
skills_registry = SkillsRegistry()
