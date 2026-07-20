demo:
	@echo "=== 1. The pipeline's tests all pass ==="
	cd fixture/dbt_project && uv run dbt test --profiles-dir .
	@echo ""
	@echo "=== 2. But Chaos Monkey finds what they miss ==="
	uv run chaos-monkey report
