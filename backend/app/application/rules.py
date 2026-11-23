"""读取独立维护的任务规则，并以内容摘要记录每次分析采用的版本。"""

import hashlib
from pathlib import Path

RULE_DIR = Path(__file__).resolve().parents[2] / "rules"
ANALYSIS_RULE = (RULE_DIR / "analysis.md").read_text(encoding="utf-8")
INTAKE_RULE = (RULE_DIR / "intake.md").read_text(encoding="utf-8")
INTAKE_VERSION = "intake-v1-" + hashlib.sha256(INTAKE_RULE.encode()).hexdigest()[:10]
RULE_VERSION = "analysis-v1-" + hashlib.sha256(ANALYSIS_RULE.encode()).hexdigest()[:10]
FEEDBACK_RULE = (RULE_DIR / "feedback.md").read_text(encoding="utf-8")
FEEDBACK_VERSION = "feedback-v1-" + hashlib.sha256(FEEDBACK_RULE.encode()).hexdigest()[:10]
