# ASOD Annotation Protocol

**Project:** Assignment Similarity and Overlap Detector (ASOD)  
**Document type:** Research and benchmark specification  
**Version:** 0.2 — Revised annotation protocol  
**Status:** Proposed protocol; pending pilot annotation and review

## 1. Purpose

This protocol defines how ASOD document pairs and reused passages will be labeled for research, development, and evaluation.

Its primary objectives are to:

- Establish consistent definitions for different forms of textual reuse.
- Separate document-level reuse judgments from passage-level annotations.
- Record citation and quotation context without assuming that textual similarity automatically constitutes plagiarism.
- Support reproducible evaluation of lexical and semantic similarity methods.
- Preserve uncertainty and annotator disagreement rather than forcing unsupported conclusions.

ASOD identifies evidence of textual overlap and reuse. It does not independently determine academic misconduct or prove authorship.

## 2. Annotation units

ASOD uses two annotation units.

### 2.1 Document-pair annotation

A document-pair annotation describes the overall relationship between a source document and a target document.

Allowed labels:

- `reuse_present`: At least one qualifying instance of textual reuse has been identified.
- `no_reuse`: No qualifying reuse was identified under the defined annotation procedure.
- `uncertain`: Available evidence is insufficient to make a reliable decision.

A `no_reuse` label is a benchmark judgment, not proof that no source of reuse exists anywhere.

Each pair must reference two distinct document IDs. Source and target roles must remain consistent within an experiment.

### 2.2 Passage-level annotation

A passage-level annotation identifies a specific span in the source and its corresponding span in the target.

Allowed labels:

- `exact_reuse`
- `near_copy`
- `paraphrased_reuse`
- `llm_paraphrased_reuse`
- `mixed_reuse`
- `undetermined`

The existing `overlap.schema.json` remains the schema authority for these labels and their required fields.

A document-pair negative label is not represented as a passage with zero-length offsets. Negative pairs belong in the document-pair annotation file.

## 3. Operational definitions

### 3.1 Exact reuse

Text has been copied verbatim or with no substantive textual changes.

Punctuation or formatting differences may occur, but the wording remains effectively identical.

### 3.2 Near-copy reuse

The target retains substantial wording or sentence structure from the source, with limited changes such as substitutions, deletions, insertions, or reordering.

The judgment must consider the passage in context rather than relying exclusively on a numerical similarity threshold.

### 3.3 Paraphrased reuse

The target expresses substantially the same source-specific meaning or information using materially different wording or sentence structure.

Shared subject matter alone is insufficient. The annotator should identify a meaningful correspondence to the source.

### 3.4 LLM-paraphrased reuse

A passage corresponds to source material and has been transformed using a large language model, with that transformation supported by reliable provenance or controlled experiment records.

Text must not receive this label merely because it sounds machine-generated or is semantically similar to another passage.

### 3.5 Mixed reuse

A passage contains multiple forms of reuse, such as verbatim copying combined with paraphrasing, or source-derived material combined with independently written text.

Annotators should identify the relevant span boundaries as precisely as practical. Where distinct spans can be labeled independently, separate annotations are preferable to an unnecessarily broad mixed span.

### 3.6 Undetermined

The evidence is insufficient to classify the suspected correspondence reliably.

This label must not be used as a substitute for careful annotation when a defensible decision is possible.

## 4. Citation and quotation context

Citation status is recorded separately from the reuse type.

The existing schema supports:

- `cited`
- `uncited`
- `quotation_with_citation`
- `not_applicable`
- `unknown`

Apply these labels as follows:

- `cited`: Relevant source attribution is present, but the passage is not clearly a quotation with citation.
- `uncited`: No relevant attribution is identified after examining the available context.
- `quotation_with_citation`: The passage is presented as a quotation and includes relevant citation or attribution.
- `not_applicable`: Citation status is not meaningful for the annotation or the evaluation condition.
- `unknown`: Available evidence does not permit a reliable judgment.

The presence of a citation does not eliminate textual overlap. Conversely, the absence of a citation does not by itself establish misconduct.

Citation judgments should account for the available bibliography, in-text citations, quotation markers, and relevant surrounding context.

### 4.1 Ambiguous, partial, and mismatched citations

Annotators must assess citation status using the available passage, surrounding text, in-text citations, quotation markers, and bibliography.

- **Partial attribution:** When a citation is present but it is unclear whether it attributes the specific reused passage, record `unknown` unless the available context supports a more definite label.
- **Mismatched citation:** When a citation is present but the cited source cannot be reliably connected to the relevant passage, record `unknown` unless sufficient evidence establishes that no relevant attribution is present.
- **Indirect attribution:** When a passage attributes information to an intermediate source rather than directly to the apparent original source, record the observable citation status and document the attribution issue in the annotation notes where relevant. Do not assume that the original source was consulted.
- **Unclear quotation boundaries:** When quotation markers or formatting make it unclear which words are quoted, record `unknown` if the uncertainty prevents a reliable citation judgment.
- **Unavailable references:** When the bibliography or cited source cannot be accessed, do not automatically classify the passage as `uncited`. Use the available evidence and record the limitation.

These cases concern citation status, not the existence of textual reuse. Annotators must assess reuse type independently and must not change a reuse label solely because citation status is uncertain.

## 5. Passage boundaries and character offsets

ASOD uses zero-based character offsets with an exclusive end position.

For a passage represented as `[start, end)`:

- `start` identifies the first included character.
- `end` identifies the position immediately after the final included character.
- A valid non-empty span satisfies `0 <= start < end <= len(text)`.

Example:

For the text `This is an example.`, the span `[0, 4)` identifies `This`.

Offsets must be calculated against the exact stored text version, including its line endings and Unicode representation.

Annotators and preprocessing scripts must not silently normalize, rewrite, or trim the text after offsets have been recorded. If text normalization is introduced, the project must preserve a reliable mapping between normalized and original character positions.

Source and target spans must be recorded independently. Their lengths do not need to be equal.

## 6. Annotation procedure

For each candidate document pair:

1. Confirm that both document IDs exist and refer to distinct documents.
2. Verify the text provenance and the relationship between the documents, where known.
3. Examine the relevant source and target passages in context.
4. Identify qualifying reuse and assign passage-level labels where applicable.
5. Record source and target offsets using the defined convention.
6. Record citation status independently from reuse type.
7. Assign the document-pair label based on the complete evidence examined.
8. Record the annotation method, review status, and relevant notes.
9. Mark unresolved cases as uncertain or undetermined at the appropriate annotation level.

### 6.1 Evidence-search scope

Before assigning `no_reuse`, annotators must complete the search procedure defined for the relevant benchmark split and annotation task.

The procedure must specify:

- **Search corpus:** The documents or source collection available to the annotator.
- **Search method:** The manual inspection, lexical retrieval, semantic retrieval, or other search methods permitted by the task.
- **Search coverage:** Whether the full document or only specified passages are examined.
- **Search limitations:** Sources that are unavailable, inaccessible, or outside the benchmark's scope.

A `no_reuse` label means that no qualifying reuse was identified within the defined and completed search scope. It must not be interpreted as proof that no source of reuse exists elsewhere.

If the required search cannot be completed, or the available evidence is insufficient to support a reliable judgment, annotators must use `uncertain` rather than treating an incomplete search as evidence of no reuse.

The search scope and permitted methods must be documented before annotation begins and applied consistently across comparable examples. Automated retrieval results may guide inspection, but the absence of a retrieval match does not independently establish `no_reuse`.

Candidate passages discovered by automated retrieval must be reviewed against the underlying text. An algorithmic similarity score alone is not a ground-truth annotation.

## 7. Provenance and transformation evidence

Each document should retain its available provenance and transformation information in the document metadata.

Examples include:

- Original human-authored material.
- Original model-generated material.
- Human paraphrases.
- LLM-generated paraphrases.
- AI-polished or human-edited AI text.
- Mixed or unknown transformations.

Labels describing the transformation must be supported by documented collection procedures, source-dataset annotations, or other appropriate evidence.

When the origin or transformation cannot be verified, record the uncertainty. Do not infer human or AI authorship from writing style alone.

## 8. Review, disagreement, and adjudication

The initial protocol is a proposal and must be tested through a pilot annotation exercise.

For the pilot:

1. Select a manageable, varied sample of document pairs.
2. Have two annotators independently label the same subset where feasible.
3. Compare document-pair labels, passage labels, citation judgments, and span boundaries.
4. Record disagreements and identify ambiguous definitions.
5. Revise the protocol before the main annotation effort.
6. Resolve evaluation-set disagreements through documented adjudication.

The project should report inter-annotator agreement when sufficient independent annotations are available. Suitable statistics may include Cohen's kappa for two annotators assigning categorical labels, with appropriate alternatives for other annotation designs.

Passage-boundary agreement should be assessed separately from categorical agreement. Exact boundary matching and a predeclared span-overlap measure may be reported.

### 8.1 Span matching and boundary agreement

ASOD will use character-span Intersection over Union (IoU) as a primary measure of passage-boundary overlap.

For a predicted span \(P\) and a reference span \(G\), IoU is defined as:

\[
\operatorname{IoU}(P,G)=\frac{|P\cap G|}{|P\cup G|}
\]

The spans must be represented using the zero-based, exclusive-end character offsets defined in Section 5. The intersection and union are calculated over character positions.

Before evaluating the system, the project must declare the IoU threshold used to count a predicted span as a match. The threshold must be selected before inspecting final test-set results and must be reported with the evaluation.

A predicted span and a reference span may count as a match only when their document pair and relevant annotation category satisfy the evaluation's matching criteria and their IoU meets the declared threshold.

Where multiple predicted spans and reference spans overlap, the evaluation must use a documented one-to-one matching policy so that a single reference span is not counted as correctly detected multiple times. Unmatched predictions count as false positives, and unmatched reference spans count as false negatives.

Report passage detection and localization separately where appropriate. Exact boundary agreement may be reported as a stricter supplementary measure. The project must document its matching policy and threshold before reporting final test results.

### 8.2 Independent annotations and adjudication records

When multiple annotators evaluate the same document pair or passage, each annotator's original decision must be retained separately before adjudication.

The annotation record should preserve, where applicable:

- Annotator identifier.
- Original document-pair label.
- Original passage-level labels and spans.
- Original citation-status judgment.
- Annotation notes or uncertainty.
- Annotation timestamp or version information when available.

Adjudication produces a separate final decision and must not overwrite the independent annotations used to measure disagreement or inter-annotator agreement.

When annotators disagree, the adjudication record should identify the issue that was resolved, the evidence considered, and the resulting decision. If the disagreement cannot be resolved reliably, the case should remain `uncertain` or `undetermined` rather than being forced into a definitive category.

The final benchmark label used for evaluation must therefore be distinguishable from the original annotator judgments and from the adjudication record.

Do not claim inter-annotator reliability until independent annotations have actually been collected and analyzed.

## 9. Dataset splitting and leakage prevention

Documents derived from the same original source or transformation family must not be distributed across training, validation, and test splits.

The `source_group_id` field should identify the source family used for grouping. All related copies, paraphrases, and transformed descendants must remain within the same split.

The test set should be reserved for final evaluation. Model or threshold selection should use training and validation data rather than repeatedly tuning against test results.

Any exceptions must be documented and justified.

## 10. Quality-control requirements

Before an annotation is accepted into the benchmark, verify:

- Referenced document IDs exist.
- Source and target document IDs differ.
- Annotation IDs are unique.
- Required labels belong to the schema-defined enumerations.
- Offsets are integers and define non-empty spans.
- Passage boundaries do not exceed the stored text lengths.
- The annotation method is recorded accurately.
- Uncertainty and review status are represented honestly.
- Source-group relationships do not introduce split leakage.
- Provenance and licensing restrictions are respected.

Automated validation checks structural consistency. It does not establish that a human annotation is semantically correct.

## 11. Evaluation principles

ASOD must evaluate detection performance independently of annotation creation.

For document-pair classification, report suitable metrics such as precision, recall, F1, and false-positive rate. Include class counts and explain the decision threshold.

For passage detection, evaluate both whether reuse was detected and how accurately the relevant span was localized.

Report performance separately for relevant reuse categories, including exact copying and paraphrased reuse, where the dataset contains sufficient examples.

For citation-sensitive evaluation, distinguish correctly attributed quotations from uncited reuse rather than treating all textual overlap as equivalent.

AI-text detection must be evaluated as a separate task with separate labels, metrics, and error analysis. Similarity labels must not be used as substitutes for AI-authorship labels.

## 12. Limitations and research integrity

The benchmark's conclusions depend on its source coverage, annotation quality, provenance reliability, and evaluation design.

Synthetic examples may be useful for controlled tests but must be identified as synthetic and must not be presented as real-world evidence.

The project must distinguish verified source-dataset labels, human judgments, synthetic labels, and algorithmic predictions.

No annotation or model score alone establishes plagiarism, intent, misconduct, or AI authorship.

## 13. Version history

| Version | Status        | Changes                                                                                                                                                |
| ------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --- |
| 0.1     | Initial draft | Defines annotation units, reuse categories, citation context, offset conventions, review, leakage controls, and evaluation principles.                 |
| 0.2     | Revised       | Adds evidence-search scope, citation ambiguity rules, span IoU and matching requirements, and independent annotation/adjudication record requirements. |     |

**Next review:** After the first pilot annotation and disagreement analysis.
