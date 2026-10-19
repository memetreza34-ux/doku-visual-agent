"""Evidence-bound script drafts, validated without external requests."""
import json
from pathlib import Path
import tempfile
import unittest

from doku_visual_agent.scriptwriter import validate_sources, generate_script, save_draft


SOURCES = [{"id":"SRC-A","title":"Überprüfte offizielle Mitteilung",
            "url":"https://example.org/source", "editor_checked":True,
            "facts":["Das Unternehmen veröffentlichte den geprüften Originalbericht."]}]
RESPONSE = {
    "title":"Ein überprüfter Hintergrund",
    "hook":"Warum lohnt es sich, diesen Bericht genau zu lesen?",
    "scenes":[{"text":"Die vorliegende Mitteilung liefert hierfür eine dokumentierte Ausgangslage.",
               "source_ids":["SRC-A"]}],
    "outro":"Die Dokumente helfen, die offenen Fragen präzise zu formulieren.",
    "outro_source_ids":["SRC-A"],
}


class Model:
    def __init__(self, result): self.result=result
    def generate(self, prompt):
        self.prompt=prompt
        return self.result


class ScriptTests(unittest.TestCase):
    def test_valid_draft_has_citations_and_not_verified(self):
        m=Model(RESPONSE)
        d=generate_script("Wir erklären die offizielle Veröffentlichung.", SOURCES, m)
        self.assertTrue(d["editorial_review_required"])
        self.assertFalse(d["source_claims_semantically_verified"])
        self.assertEqual(d["scenes"][0]["source_ids"],["SRC-A"])
        self.assertIn("SRC-A",m.prompt)
        with tempfile.TemporaryDirectory() as tmp:
            save_draft(d,Path(tmp))
            script=(Path(tmp)/"draft_script.txt").read_text()
            evidence=json.loads((Path(tmp)/"draft_evidence.json").read_text())
            self.assertIn("Warum lohnt es sich",script)
            self.assertTrue(evidence["editorial_review_required"])

    def test_only_editor_reviewed_sources(self):
        with self.assertRaisesRegex(ValueError,"Vorprüfung"):
            validate_sources([{**SOURCES[0],"editor_checked":False}])

    def test_invalid_source_links(self):
        with self.assertRaisesRegex(ValueError,"Vorprüfung"):
            validate_sources([{**SOURCES[0],"url":"http://localhost/internal"}])

    def test_unknown_source_id_rejected(self):
        r={**RESPONSE,"scenes":[{**RESPONSE["scenes"][0],"source_ids":["SRC-UNKNOWN"]}]}
        with self.assertRaisesRegex(ValueError,"nachgewiesene"):
            generate_script("Wir erklären die offizielle Veröffentlichung.",SOURCES,Model(r))

    def test_no_unattributed_scenes(self):
        r={**RESPONSE,"scenes":[{**RESPONSE["scenes"][0],"source_ids":[]}]}
        with self.assertRaisesRegex(ValueError,"Quellen"):
            generate_script("Wir erklären die offizielle Veröffentlichung.",SOURCES,Model(r))

    def test_source_dedup_and_brief_limits(self):
        with self.assertRaisesRegex(ValueError,"Doppelte"):
            validate_sources(SOURCES+SOURCES)
        with self.assertRaisesRegex(ValueError,"10–800"):
            generate_script("kurz", SOURCES, Model(RESPONSE))


if __name__=="__main__": unittest.main()
