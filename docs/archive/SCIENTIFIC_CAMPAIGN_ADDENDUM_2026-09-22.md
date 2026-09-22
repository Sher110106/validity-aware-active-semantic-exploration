# Scientific campaign addendum — block 00069/42 v6

The final fresh attempt was stopped safely at 19.5 m, after stages 0–6 completed and stage 7 began. It added $18.552664 of real settled spend; the shared scientific ledger then stood at $36.783435 settled, with zero unresolved or reserved requests and no increase in redundant settlement. The pinned checkout remained byte-identical against the fresh 616-file baseline.

The limiting factor was the allocation’s reservation accounting: 2,233 settled requests consumed $159.976812 of the $160 allocation’s reservation sum, although their actual settled cost was $36.783435. The pipeline then failed closed with `AccountingHalt("allocation exhausted")`; retries did not make new provider calls. Creating another allocation is not possible within the remaining $6.50 code-ceiling headroom, and the ledger semantics were not changed.

Zero-cost offline scoring was run with commit `5c178e2` under both `official_asp` and `validator_plus_unanimity_raw_tau_1_0` and is preserved on tyrone at:

`/workspace/runs/prospective_gemini/scientific_campaign_20260922/offline_scoring_20260922/block_00069_42_v6/summary.json`

Stages 0–6 have complete four-member tracks; stage 7 is retained as a partial artifact and is marked by missing completion files. The three earlier zero-spend startup attempts (`v3`, `v4`, `v5`) are also preserved.
