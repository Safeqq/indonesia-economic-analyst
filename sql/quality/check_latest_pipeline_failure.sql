WITH ranked_runs AS (
    SELECT
        run_id,
        source_code,
        started_at,
        completed_at,
        status,
        rows_loaded,
        error_message,
        ROW_NUMBER() OVER (
            PARTITION BY source_code
            ORDER BY started_at DESC, run_id DESC
        ) AS recency_rank
    FROM fact_pipeline_run
)
SELECT
    run_id,
    source_code,
    started_at,
    completed_at,
    status,
    rows_loaded,
    error_message
FROM ranked_runs
WHERE recency_rank = 1
  AND status = 'failed';
