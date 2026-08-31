.PHONY: validate baseline evaluate demo shadow-transfer external-validate external-bundle external-live v2-status v2-sut-freeze v2-sut-verify v2-author-packet v2-validate v2-freeze v2-verify v2-predict v2-predict-resume v2-predict-resume-status v2-qwen-validate v2-qwen-probe v2-qwen-predict-resume v2-qwen-predict-resume-status v2-score v2-evidence-manifest test run

validate:
	python3 -m superturiya.hackathon validate

baseline:
	python3 -m superturiya.hackathon baseline --mode frozen

evaluate:
	python3 -m superturiya.hackathon evaluate --mode frozen

demo:
	python3 -m superturiya.hackathon demo --case eval-006 --mode frozen

shadow-transfer:
	python3 -m superturiya.hackathon shadow-transfer

external-validate:
	python3 -m superturiya.external_validity validate
	python3 -m superturiya.external_validity isolation

external-bundle:
	python3 -m superturiya.external_validity bundle

external-live:
	python3 -m superturiya.external_validity live --trials 3

v2-status:
	python3 -m superturiya.external_v2 status

v2-sut-freeze:
	python3 -m superturiya.external_v2 sut-freeze --model "$${SUPERTURIYA_LLM_MODEL:-openai/gpt-oss-120b}" --trials 3

v2-sut-verify:
	python3 -m superturiya.external_v2 sut-verify

v2-author-packet:
	python3 -m superturiya.external_v2 author-packet --output output/external_v2_author_packet.zip

v2-validate:
	python3 -m superturiya.external_v2 validate

v2-freeze:
	@test -n "$(AUTHOR_ID)" || (echo "AUTHOR_ID is required" && exit 2)
	@test -n "$(REVIEWER_ID)" || (echo "REVIEWER_ID is required" && exit 2)
	python3 -m superturiya.external_v2 freeze --author-id "$(AUTHOR_ID)" --reviewer-id "$(REVIEWER_ID)"

v2-verify:
	python3 -m superturiya.external_v2 verify

v2-predict:
	@test -n "$(OUTPUT)" || (echo "OUTPUT is required" && exit 2)
	python3 -m superturiya.external_v2 predict --mode live --experiment comparison --trials 3 --output "$(OUTPUT)"

v2-predict-resume:
	@test -n "$(OUTPUT)" || (echo "OUTPUT is required" && exit 2)
	python3 -m superturiya.external_v2_resumable run --output "$(OUTPUT)" $(if $(CHECKPOINT_DIR),--checkpoint-dir "$(CHECKPOINT_DIR)",)

v2-predict-resume-status:
	@test -n "$(OUTPUT)" || (echo "OUTPUT is required" && exit 2)
	python3 -m superturiya.external_v2_resumable status --output "$(OUTPUT)" $(if $(CHECKPOINT_DIR),--checkpoint-dir "$(CHECKPOINT_DIR)",)

v2-qwen-validate:
	python3 -m superturiya.external_v2_qwen_fallback validate

v2-qwen-probe:
	python3 -m superturiya.external_v2_qwen_fallback probe

v2-qwen-predict-resume:
	@test -n "$(OUTPUT)" || (echo "OUTPUT is required" && exit 2)
	python3 -m superturiya.external_v2_qwen_fallback run --output "$(OUTPUT)" $(if $(CHECKPOINT_DIR),--checkpoint-dir "$(CHECKPOINT_DIR)",)

v2-qwen-predict-resume-status:
	@test -n "$(OUTPUT)" || (echo "OUTPUT is required" && exit 2)
	python3 -m superturiya.external_v2_qwen_fallback status --output "$(OUTPUT)" $(if $(CHECKPOINT_DIR),--checkpoint-dir "$(CHECKPOINT_DIR)",)

v2-score:
	@test -n "$(RAW)" || (echo "RAW is required" && exit 2)
	@test -n "$(OUTPUT)" || (echo "OUTPUT is required" && exit 2)
	python3 -m superturiya.external_v2 score --raw "$(RAW)" --output "$(OUTPUT)"

v2-evidence-manifest:
	@test -n "$(EVIDENCE_ROOT)" || (echo "EVIDENCE_ROOT is required" && exit 2)
	python3 -m superturiya.external_v2 evidence-manifest --evidence-root "$(EVIDENCE_ROOT)" --output "$(EVIDENCE_ROOT)/manifest.json"

test:
	python3 -m unittest discover -s tests -v

run:
	python3 -m superturiya --seed --port 8765
