# ASOD Dataset Acquisition Register

**Project:** Assignment Similarity and Overlap Detector (ASOD)  
**Register version:** 0.1  
**Prepared:** 2026-10-28  
**Status:** Candidate review only — no external dataset has been downloaded, acquired, or incorporated into the benchmark.

## Purpose

Track candidate external datasets before acquisition. Record access and use conditions, likely annotation compatibility, storage needs, conversion work, and limitations. Keep original source files separate from normalized ASOD records and never overwrite source data.

## Candidate register

### DSET-001 — PAN Plagiarism Corpus 2011 (PAN-PC-11)

- **Primary task:** Traditional plagiarism / passage-overlap detection.
- **Official record:** https://zenodo.org/records/3250095
- **DOI:** https://doi.org/10.5281/zenodo.3250095
- **Access status:** Public download listed on Zenodo.
- **Use conditions:** Zenodo states the corpus may be used free of charge for research. The record's license field is not clearly populated in the visible metadata; do not assume unrestricted redistribution or commercial use. Re-check the record and accompanying documentation before use.
- **Published size:** Approximately 1.7 GB compressed across two RAR parts. Extracted size is not yet verified.
- **Published content/annotation:** Includes automatically inserted and manually produced plagiarism. Exact file layout, encoding, and annotation files must be inspected after acquisition.
- **Expected schema mapping:** Likely useful for `document` metadata, `document_pair` reuse labels, and `overlap` passage spans. Mapping is provisional until the actual corpus structure and offsets are inspected.
- **Suitability:** Useful traditional baseline; older corpus and not designed for contemporary LLM paraphrasing.
- **Expected conversion work:** Inventory archive; verify checksums if available; inspect text/annotation structure; parse source–target links and offsets; verify whether offsets are zero-based and exclusive-end; validate spans against decoded text; map labels without changing original annotations; document any conversion loss.
- **Storage estimate:** At least 1.7 GB for the compressed parts, plus additional space for extraction and normalized copies. Reserve several GB before downloading.
- **Current decision:** Keep as a primary candidate, pending license/terms review and storage check.
- **Source:** Zenodo record and Webis dataset page: https://webis.de/data/pan-pc-11.html

### DSET-002 — PAN 2025 Generative Plagiarism Detection

- **Primary task:** LLM-paraphrased reuse and passage localization.
- **Official task page:** https://pan.webis.de/clef25/pan25-web/generated-plagiarism-detection.html
- **Official data record:** https://zenodo.org/records/14969012
- **DOI:** https://doi.org/10.5281/zenodo.14969012
- **Access status:** Restricted. The task page says to register with TIRA; Zenodo access must be requested.
- **Use conditions:** The task page states the data contains copyrighted material, is for research purposes only, and must not be redistributed. Do not download or share it unless access is granted and conditions are accepted.
- **Published size:** Zenodo displays a data volume of approximately 891.3 GB in its statistics. This may reflect aggregate transfer statistics, not the size of one downloadable archive; actual downloadable size is not verified. Do not use this number as a storage estimate.
- **Published content/annotation:** Training/validation pairs; source and suspicious text; XML `_truths` annotations with passage offsets and source references. The `plagiarism` feature identifies reused spans, while `altered` can identify genuine LLM-paraphrased text that is not reused.
- **Expected schema mapping:** Strong candidate for `document_pair` and `overlap` annotations, including source/target spans. Citation status and provenance labels required by ASOD may not be supplied and must not be inferred.
- **Suitability:** High relevance to modern LLM-obfuscated reuse and the crucial distinction between paraphrased reuse and genuine LLM paraphrasing.
- **Expected conversion work:** After access approval, inspect the exact train/validation package; parse pair lists and XML; preserve source identifiers and raw XML; confirm offset conventions; validate all spans against exact decoded files; map only supported labels; keep original train/validation split and avoid leakage.
- **Storage estimate:** Unknown until the accessible package size is confirmed. Check available disk space before download.
- **Current decision:** Request access only if needed for the project and after mentor/research-use conditions are understood. Do not make project progress dependent on approval.
- **Sources:** Official task page and Zenodo record above.

### DSET-003 — RAID: Robust AI Detection benchmark

- **Primary task:** AI-generated text detection and robustness evaluation.
- **Paper:** https://aclanthology.org/2024.acl-long.674/
- **Official repository:** https://github.com/liamdugan/raid
- **Dataset site:** https://raid-bench.xyz/
- **Access status:** Public repository and documented dataset-loading options.
- **Use conditions:** The GitHub repository displays an MIT license for the repository/software. This does **not by itself establish the license or redistribution rights of every underlying text in the dataset**. Inspect the dataset documentation and source-specific terms before redistribution or publication of text samples.
- **Published scale:** The paper reports 6M+ generations; the current repository describes over 10 million documents. Treat counts as version-dependent and record the exact release/snapshot used.
- **Published content/annotation:** Multiple language models, domains/genres, decoding strategies, and adversarial text transformations. Repository documents train/test/extra partitions and provides a loader. The exact subset schema and fields must be inspected in the selected release.
- **Expected schema mapping:** Likely useful for `document` and `ai_annotation` records. Preserve generator/model, domain, split, attack/transformation, and label fields where present. Do not invent human-editing provenance where the dataset does not provide it.
- **Suitability:** Strong candidate for robustness and out-of-domain evaluation. Too large to ingest wholesale for an initial pilot; select a documented, reproducible subset.
- **Expected conversion work:** Pin the package/version or commit; inspect schema and labels; select a subset by a predeclared rule; preserve original split; check duplicates and overlap between sources; map labels to ASOD's AI-origin taxonomy; keep raw source records and conversion script.
- **Storage estimate:** Version and subset dependent. The repository reports large CSV partitions (including adversarial variants), so do not load the entire dataset until subset size and disk requirements are measured.
- **Current decision:** Primary AI-detection candidate, pending license review for underlying data and subset specification.
- **Sources:** ACL Anthology paper and official GitHub repository above.

## Acquisition workflow

Do these steps for each candidate, in order:

1. **Terms check:** Record the dataset's own license/terms separately from the software repository license. Record whether redistribution, public demo use, and publication of examples are permitted.
2. **Access check:** Mark public, access-request required, or unavailable. Do not treat a public landing page as proof that data files are accessible.
3. **Size check:** Record compressed and extracted size where known; confirm free disk space before downloading.
4. **Version pinning:** Record version/release, access date, DOI or commit, and file checksums where available.
5. **Raw preservation:** Store acquired data in a dedicated raw-data location. Do not edit raw source files.
6. **Structure inspection:** Inventory files, formats, encoding, identifiers, split definitions, labels, offsets, and provenance fields.
7. **Compatibility audit:** Map only source-supported information to ASOD schemas. Preserve unknown or unavailable values as unknown; do not fabricate labels.
8. **Conversion and validation:** Write a reproducible conversion script; validate documents, pairs, spans, and split leakage.
9. **Decision record:** Document accepted subset, excluded items, rationale, limitations, and any unresolved rights questions before using it in experiments.

## Proposed storage convention

Do not place external corpus contents directly into `benchmark/data/custom/documents/`.

After acquisition and terms review, use a structure like:

```text
benchmark/
  data/
    external/
      pan_pc_11/
        raw/
        extracted/
        README_SOURCE.md
      pan_2025_generative_plagiarism/
        raw/
        extracted/
        README_SOURCE.md
      raid/
        raw/
        selected_subset/
        README_SOURCE.md
  metadata/
    documents.jsonl
    document_pairs.jsonl
    overlap_annotations.jsonl
```

This is a proposed convention, not a claim that these directories or datasets already exist. If a dataset's terms prohibit storing or redistributing its text in the repository, keep it outside version control and document the required local path and acquisition instructions instead.

## Decision log

| Date | Dataset | Decision/status | Reason / next action |
|---|---|---|---|
| 2026-10-28 | PAN-PC-11 | Candidate | Verify terms and inspect file/annotation structure before download. |
| 2026-10-28 | PAN 2025 Generative Plagiarism | Access restricted | Review research-use/no-redistribution conditions; request access if appropriate; measure actual package size after approval. |
| 2026-10-28 | RAID | Candidate | Verify underlying dataset terms; define a small, reproducible subset and inspect schema before download. |

## Research-integrity rules

- No dataset is marked **acquired** until the files have actually been downloaded and verified.
- No source label is treated as ground truth beyond the source's documented annotation procedure and scope.
- Do not silently convert absent citation/provenance information into `uncited`, `human`, or `no_reuse`.
- Keep source labels, normalized ASOD labels, and any adjudicated labels distinguishable.
- Preserve source splits where possible and audit related-document/source-group leakage before experiments.
- Do not publish restricted/copyrighted text or redistribute data unless the relevant terms explicitly allow it.
- `DOC_0001` remains a temporary test fixture and is not benchmark evidence.
