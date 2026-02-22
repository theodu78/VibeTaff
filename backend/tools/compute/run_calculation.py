import json
import logging
import math
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from tools._base import tool

logger = logging.getLogger(__name__)

_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool,
    "dict": dict, "enumerate": enumerate, "filter": filter,
    "float": float, "format": format, "frozenset": frozenset,
    "int": int, "isinstance": isinstance, "len": len,
    "list": list, "map": map, "max": max, "min": min,
    "pow": pow, "print": print, "range": range, "repr": repr,
    "reversed": reversed, "round": round, "set": set,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
    "type": type, "zip": zip,
    "True": True, "False": False, "None": None,
}

_SAFE_MODULES = {
    "math": math,
    "statistics": statistics,
    "json": json,
    "re": re,
}

CALC_TIMEOUT_SECONDS = 10


def _run_restricted(code: str) -> str:
    """Niveau 1 : RestrictedPython in-process (mode personal)."""
    from RestrictedPython import compile_restricted, safe_globals, PrintCollector
    from RestrictedPython.Eval import default_guarded_getiter
    from RestrictedPython.Guards import guarded_unpack_sequence, safer_getattr

    compiled = compile_restricted(code, "<sandbox>", "exec")
    if compiled is None:
        return "Erreur : Le code contient des instructions non autorisées."

    restricted_globals = safe_globals.copy()
    restricted_globals["__builtins__"] = _SAFE_BUILTINS.copy()
    restricted_globals["_print_"] = PrintCollector
    restricted_globals["_getiter_"] = default_guarded_getiter
    restricted_globals["_getattr_"] = safer_getattr
    restricted_globals["_unpack_sequence_"] = guarded_unpack_sequence
    restricted_globals["_iter_unpack_sequence_"] = guarded_unpack_sequence
    restricted_globals["_write_"] = lambda obj: obj
    restricted_globals["_inplacevar_"] = lambda op, x, y: op(x, y)

    for mod_name, mod in _SAFE_MODULES.items():
        restricted_globals[mod_name] = mod

    restricted_locals: dict = {}

    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("Le calcul a dépassé le timeout de 10 secondes.")

    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(CALC_TIMEOUT_SECONDS)

    try:
        exec(compiled, restricted_globals, restricted_locals)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    printed = restricted_locals.get("_print")
    result = printed() if printed else ""
    result = result.strip() if isinstance(result, str) else str(result).strip()
    return result


def _run_subprocess(code: str) -> str:
    """Niveau 2 : processus isolé avec environnement minimal."""
    wrapper = (
        "import math, statistics, json, re\n"
        "import sys\n"
        "# Block dangerous modules\n"
        "BLOCKED = {'os','subprocess','shutil','socket','http','urllib',\n"
        "           'requests','pathlib','importlib','ctypes','signal',\n"
        "           'multiprocessing','threading','webbrowser','ftplib',\n"
        "           'smtplib','telnetlib','pickle','shelve','dbm'}\n"
        "class _BlockedFinder:\n"
        "    def find_module(self, name, path=None):\n"
        "        if name.split('.')[0] in BLOCKED:\n"
        "            raise ImportError(f'Module interdit: {name}')\n"
        "        return None\n"
        "sys.meta_path.insert(0, _BlockedFinder())\n"
        "del sys.modules.get, __builtins__.__dict__.get('__import__', None)\n"
        "# --- user code ---\n"
    )
    full_code = wrapper + code

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(full_code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [sys.executable, "-u", "-S", tmp_path],
            capture_output=True,
            text=True,
            timeout=CALC_TIMEOUT_SECONDS,
            env={"PATH": "/usr/bin:/usr/local/bin"},
            cwd=tempfile.gettempdir(),
        )
        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            if "Module interdit" in stderr:
                return f"Erreur : {stderr.splitlines()[-1]}"
            return f"Erreur d'exécution : {stderr[-500:]}" if stderr else "Erreur inconnue."
        return proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Erreur : Le calcul a dépassé le timeout de 10 secondes."
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


@tool(
    name="run_local_calculation",
    description=(
        "Exécute du code Python dans un bac à sable sécurisé pour des calculs complexes. "
        "Modules disponibles : math, statistics, json, re. PAS d'accès fichiers ni réseau. "
        "QUAND l'utiliser : pour des calculs mathématiques, des conversions, du parsing de données, "
        "des pourcentages, des moyennes — tout ce qui nécessite de la logique de calcul. "
        "QUAND NE PAS l'utiliser : pour des calculs simples que tu peux faire de tête (2+2, TVA à 20%). "
        "Le résultat est la dernière valeur imprimée via print()."
    ),
    category="compute",
    parameters={
        "type": "object",
        "properties": {
            "python_code": {
                "type": "string",
                "description": "Le code Python à exécuter. Utilise print() pour renvoyer le résultat.",
            },
        },
        "required": ["python_code"],
    },
)
def run_local_calculation(args: dict, project_id: str, project_dir: Path) -> str:
    import config

    if not config.get("security.allow_code_execution", True):
        return "Erreur : L'exécution de code est désactivée par la politique de sécurité."

    code = args.get("python_code", "").strip()
    if not code:
        return "Erreur : Aucun code Python fourni."

    if len(code) > 10_000:
        return "Erreur : Le code est trop long (max 10 000 caractères)."

    sandbox_mode = config.get("security.sandbox_mode", "restricted")

    try:
        if sandbox_mode == "subprocess":
            logger.info("Sandbox: subprocess mode")
            result = _run_subprocess(code)
        else:
            logger.info("Sandbox: RestrictedPython mode")
            result = _run_restricted(code)

        if not result:
            return json.dumps({
                "status": "ok",
                "result": None,
                "stdout": "",
                "error": "Le code s'est exécuté sans erreur mais n'a rien affiché. Utilise print() pour renvoyer un résultat.",
            })

        if result.startswith("Erreur"):
            return json.dumps({
                "status": "error",
                "result": None,
                "stdout": "",
                "error": result,
            })

        return json.dumps({
            "status": "ok",
            "result": result,
            "stdout": result,
            "error": None,
        })

    except TimeoutError as e:
        return json.dumps({"status": "error", "result": None, "stdout": "", "error": str(e)})
    except SyntaxError as e:
        return json.dumps({"status": "error", "result": None, "stdout": "", "error": f"Syntaxe: {e}"})
    except Exception as e:
        return json.dumps({"status": "error", "result": None, "stdout": "", "error": f"{type(e).__name__}: {e}"})
