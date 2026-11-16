# ASOD Benchmark Dataset Card

**Project:** Assignment Similarity and Overlap Detector (ASOD)  
**Document version:** 0.1  
**Status:** Initial specification — benchmark construction in progress  
**Last updated:** 26 October 2026

## 1. Dataset Overview

The ASOD benchmark is being designed to evaluate two distinct tasks in academic writing analysis:

1. **Textual overlap and potential plagiarism analysis:** identify and characterize reused text between source and target documents.
2. **AI-text detection:** estimate whether text was human-written, AI-generated, AI-transformed, or produced through mixed authorship.

These tasks will be evaluated independently. Textual similarity alone does not establish plagiarism, and an AI-text detector's prediction does not establish authorship.

**Current implementation status:** The metadata contains one initial document record (`DOC_0001`). A temporary text fixture has been used to test character-offset validation. No substantial research dataset or validated benchmark has been established yet.

## 2. Intended Uses

The benchmark is intended for:

- Developing and evaluating text-overlap detection methods.
- Comparing lexical, structural, and semantic similarity approaches.
- Evaluating detection of exact copying, near-copying, and paraphrased reuse.
- Studying false positives caused by generic phrases and legitimate quotations.
- Separately evaluating AI-text detection across text origins and transformations.
- Measuring the reliability and limitations of explanations produced by ASOD.

The benchmark is not intended to automatically accuse students of plagiarism, establish misconduct, or prove that a document was written by AI.

## 3. Scope and Task Separation

### Track A — Textual Overlap

This track evaluates relationships between source and target documents.

Document-pair labels:

- `reuse_present`
- `no_reuse`
- `uncertain`

Passage-level annotations identify actual reused spans and characterize their relationship.

### Track B — AI-Text Analysis

This track evaluates the provenance of a document or text segment.

Potential labels include:

- `human_written`
- `ai_generated`
- `ai_paraphrased`
- `ai_polished_human`
- `human_edited_ai`
- `human_ai_mixed`
- `human_initiated_ai_continued`
- `unknown_or_unverified`

AI-text labels must not be used as substitutes for textual-overlap labels. A document may belong to either task's relevant categories independently.

## 4. Data Sources and Provenance

Potential external sources will be assessed before inclusion. Planned research candidates include PAN plagiarism-detection corpora and generative-plagiarism datasets for Track A, and AI-text evaluation resources such as RAID and suitable academic-writing datasets for Track B.

These are candidate sources, not confirmed acquisitions.

Before any external data is integrated, the project must document:

- Dataset name and version.
- Original source and download location.
- Applicable licence and permitted uses.
- Collection method and original task.
- Available ground-truth labels and annotation procedure.
- Known limitations, demographic or domain coverage where documented, and potential biases.
- Any transformations performed during preprocessing.

External records must retain their original identifiers or a documented mapping to ASOD identifiers. Source attribution and licence conditions must be preserved.

## 5. Document Metadata

Document-level metadata is stored as JSON Lines in `benchmark/metadata/documents.jsonl` and validated against `benchmark/schemas/document.schema.json`.

The current schema records document identity, source grouping, document type, origin, transformation type, language, word count, dataset split, provenance status, and licence status, alongside applicable optional fields.

Document text for the current custom-data workflow is stored separately under `benchmark/data/custom/documents/`, using the document ID as the filename, for example `DOC_0001.txt`.

The current one-record metadata file is a structural starting point, not evidence of a representative dataset.

## 6. Annotation Design

### Document-Pair Annotations

Pair labels are stored separately from passage annotations. A `no_reuse` label means that a pair was judged negative under the documented annotation procedure; it does not prove that no possible reuse exists.

### Passage-Level Overlap Annotations

Passage annotations use the following relationship labels:

- `exact_reuse`
- `near_copy`
- `paraphrased_reuse`
- `llm_paraphrased_reuse`
- `mixed_reuse`
- `undetermined`

Citation status is recorded independently, including whether material is cited or appears as a quotation with a citation.

Character offsets use zero-based indexing with an exclusive end. For a text of length _N_, a valid non-empty span must satisfy `0 <= start < end <= N`.

The annotation protocol is maintained in `benchmark/ANNOTATION_PROTOCOL.md`. It remains subject to pilot annotation, review, and refinement.

## 7. Data Splitting and Leakage Prevention

Training, validation, and test splits must be assigned at the source-group level whenever documents share an origin, parent, or transformation lineage.

Related versions of the same underlying text must not be distributed across splits in a way that inflates evaluation performance.

The project will run metadata validation, document-integrity checks, and split-leakage audits as the benchmark grows. Additional checks will be needed for duplicated or near-duplicated content across external datasets.

## 8. Evaluation Plan

### Track A — Textual Overlap

Depending on the task and available annotations, planned metrics include:

- Precision, recall, and F1 for document-pair classification.
- False-positive and false-negative rates.
- Passage-level span precision, recall, and F1.
- Retrieval Recall@K and nDCG@K for source retrieval, where relevance judgments are available.
- Results stratified by overlap type, text length, citation condition, and transformation type.

### Track B — AI-Text Analysis

Planned metrics include:

- Precision, recall, and F1.
- False-positive and false-negative rates.
- ROC-AUC where suitable scores and labels are available.
- Performance by text length, domain, generator, editing condition, and other supported evaluation groups.

Class imbalance, dataset provenance, and the distinction between in-domain and out-of-domain evaluation must be reported. No performance claim will be made until experiments have actually been run.

## 9. Quality Assurance

Before benchmark release or performance reporting:

1. Validate dataset records against their schemas.
2. Check identifier uniqueness and referential integrity.
3. Check document and passage boundaries.
4. Verify source-group split assignments.
5. Review provenance and licence documentation.
6. Conduct a pilot annotation exercise and resolve disagreements.
7. Report annotation agreement where multiple annotators are involved.
8. Keep synthetic test fixtures separate from research examples.
9. Document exclusions, preprocessing, and known data limitations.

Automated integrity checks establish structural consistency, not the correctness of research labels.

## 10. Known Limitations and Risks

- The current dataset is too small for meaningful performance evaluation.
- External benchmark availability, licences, and compatibility have not yet been verified.
- Human judgments of paraphrased reuse may be subjective.
- Citation presence does not by itself determine whether reuse is acceptable.
- AI-text detectors may fail to generalize across domains, models, languages, and editing styles.
- Synthetic examples may not reflect real academic misconduct or authentic student writing.
- Dataset contamination and overlap between public corpora may inflate results.
- A model score or highlighted passage is evidence for review, not a final misconduct determination.

## 11. Release and Versioning

Dataset releases should include a versioned metadata snapshot, dataset card, annotation protocol, source and licence manifest, validation results, split definitions, and a change log.

Restricted or third-party text must not be redistributed unless the applicable licence permits it. Where redistribution is prohibited, document the source, access procedure, and any lawful derived artifacts instead.

## 12. Current Status and Next Milestones

- [x] Define separate overlap and AI-text analysis tracks.
- [x] Establish initial metadata and annotation schemas.
- [x] Create an initial annotation protocol.
- [x] Implement and test basic document and overlap integrity checks using temporary fixtures.
- [ ] Verify candidate dataset availability, licences, and annotation compatibility.
- [ ] Define the first pilot dataset and its inclusion criteria.
- [ ] Collect or acquire permitted research documents.
- [ ] Pilot the annotation protocol and measure agreement where possible.
- [ ] Establish leakage-safe splits and a reproducible baseline evaluation.

**Status statement:** This card describes the intended benchmark design and current project state. It does not claim that the proposed datasets have been acquired, that annotations are complete, or that any model has achieved validated performance.
