"""Local Bug Database lookup engine enforcing 'Similarity is evidence, not truth'."""

import json
import re
from pathlib import Path
from typing import List, Dict, Any
from core.schemas import BugRecord


def _tokenize(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-zA-Z0-9_]+", text.lower())
        if len(tok) > 2
        and tok not in {"the", "and", "when", "with", "from", "that", "this", "for", "are"}
    }


class LocalBugDatabase:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def lookup(
        self,
        issue_text: str,
        candidate_functions: List[str],
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        if max_results <= 0 or not self.db_path.exists():
            return []

        raw_records = json.loads(self.db_path.read_text(encoding="utf-8"))
        issue_tokens = _tokenize(issue_text)
        fn_set = {f.lower() for f in candidate_functions}

        scored: List[BugRecord] = []
        for item in raw_records:
            corpus = " ".join(
                [
                    item.get("issue_pattern", ""),
                    item.get("repository_pattern", ""),
                    " ".join(item.get("symptoms", [])),
                ]
            )
            record_tokens = _tokenize(corpus)
            lexical_overlap = len(issue_tokens & record_tokens) / max(
                1, len(issue_tokens | record_tokens)
            )
            rec_fns = {f.lower() for f in item.get("relevant_functions", [])}
            fn_overlap = len(fn_set & rec_fns) / max(1, len(rec_fns)) if rec_fns else 0.0

            score = round(0.65 * lexical_overlap + 0.35 * fn_overlap, 3)
            if score > 0.05:
                scored.append(
                    BugRecord(
                        bug_id=item.get("bug_id", "BUG-UNKNOWN"),
                        issue_pattern=item.get("issue_pattern", ""),
                        repository_pattern=item.get("repository_pattern", ""),
                        symptoms=item.get("symptoms", []),
                        relevant_functions=item.get("relevant_functions", []),
                        fix_pattern=item.get("fix_pattern", ""),
                        patch=item.get("patch", ""),
                        outcome=item.get("outcome", "passed"),
                        similarity_score=score,
                        epistemic_status="SIMILARITY_IS_EVIDENCE_NOT_TRUTH",
                    )
                )

        scored.sort(key=lambda r: r.similarity_score, reverse=True)
        return [r.to_dict() for r in scored[:max_results]]
