# ForgeMind Rail Explainability

ForgeMind Rail is an evidence-grounded AI decision-support system for predictive rail infrastructure maintenance.

The system is designed so that engineers can understand what information influenced an AI-assisted result, what evidence supports it, where uncertainty exists, and which decisions remain under human authority.

## Decision and Reasoning

ForgeMind Rail makes advisory maintenance decisions by connecting available engineering evidence rather than relying on an unsupported model prediction.

Its reasoning can incorporate asset context, inspection findings, usage history, failure records, maintenance history, work orders, engineering documents, procedures, and compliance information. Relevant evidence is retrieved and connected to the asset or engineering question being investigated.

The system is designed around the principle:

**Predict earlier → Explain why → Show the evidence → Let engineers decide.**

AI-generated reasoning is advisory. It does not itself authorize maintenance activity or change the operational state of railway infrastructure.

Where the available evidence does not adequately support an answer, ForgeMind Rail should abstain or communicate insufficient evidence instead of manufacturing certainty.

## Inputs and Data Sources

The data used by ForgeMind Rail can include railway asset records, inspection records, asset usage history, failure history, maintenance records, work orders, engineering documents, procedures, regulations, and compliance evidence.

The current public prototype uses a synthetic railway demonstration dataset. This dataset does not represent operational information from a real railway, metro operator, infrastructure owner, or safety authority.

Evidence can be associated with source lineage and citations where supported by the application workflow. This allows an engineer to inspect the information supporting an AI-assisted response rather than receiving an unexplained recommendation.

The demonstration environment also contains seeded asset, failure, inspection, work-order, and usage records so that evidence-grounded workflows can be reproduced consistently.

## Decision Evidence and Traceability

ForgeMind Rail is designed to connect analytical or generated outputs to supporting evidence whenever that evidence is available.

A ForgeMind citation represents a traceable reference from an analytical or generated output to supporting ingested evidence. Citations and evidence references are intended to help reviewers inspect why information was surfaced.

Evidence retrieval is therefore distinct from AI reasoning. Retrieved evidence provides supporting context, while AI-assisted components help interpret and organize that context for engineering review.

An AI-generated statement should not be interpreted as equivalent to verified engineering evidence merely because it appears in an AI response.

## Confidence and Evidence Sufficiency

ForgeMind Rail treats evidence sufficiency as an important part of its decision process.

When supporting evidence exists, the system can return evidence-grounded information together with the relevant context or citation. When evidence is missing or insufficient, the intended behavior is to communicate uncertainty, provide a low-confidence or unsupported result, or abstain.

The system must not fabricate an asset, inspection result, maintenance record, citation, engineering requirement, or operational condition merely to answer a request.

This behavior is demonstrated by unsupported-query scenarios in which the expected outcome is abstention rather than invented evidence.

## Human Decision and Authority

ForgeMind Rail provides engineering decision support. Qualified human engineers retain final authority over maintenance and operational decisions.

AI-generated recommendations do not constitute permission to perform railway maintenance or safety-critical actions. Human review remains required before information from the system could inform a real engineering decision.

The system does not autonomously approve maintenance, control trains, operate signalling equipment, actuate railway equipment, repair infrastructure, isolate systems, or modify safety-critical configuration.

**Operational action is not executed by the AI.**

## Limits, Limitations, Constraints, and Known Issues

ForgeMind Rail is currently a research and engineering prototype rather than a certified railway safety system or production railway deployment.

A major limitation is that the current rail demonstration dataset is synthetic. Results obtained from this dataset do not establish real-world predictive-maintenance performance, railway safety performance, or operational effectiveness.

The existing retrieval evaluation is a development smoke test rather than a held-out railway predictive-maintenance benchmark. Retrieval metrics and evidence counts must not be interpreted as predictive-maintenance accuracy.

The current public prototype runs on Google Cloud Run and uses ephemeral SQLite storage. Runtime-created data may therefore be lost when a container instance is replaced, and durable production persistence is not claimed.

Additional constraints for a real railway deployment would include representative field data, held-out validation, durable persistence, enterprise identity, cybersecurity controls, monitoring, operator-system integration, railway-domain validation, safety engineering, and applicable regulatory or certification processes.

## Safety Constraints and Non-Execution Boundary

ForgeMind Rail operates within an explicit advisory boundary.

The AI can retrieve relevant evidence, connect records, explain evidence context, identify patterns, surface maintenance concerns, assist investigation, and prepare decision-support information.

The AI cannot control trains, operate signalling equipment, actuate railway equipment, start or stop machinery, repair infrastructure, approve maintenance, override access controls, modify safety-critical configuration, or execute production actions.

These constraints ensure that evidence-grounded AI assistance remains separated from operational authority.

## Known Issue Handling and Abstention

When ForgeMind Rail cannot find sufficient supporting evidence for a requested conclusion, the intended response is abstention or an explicit indication that the evidence is insufficient.

For example, a query concerning an asset that does not exist in the available evidence should not cause the system to invent an asset, inspection frequency, citation, or maintenance history.

This behavior is intentional. In an engineering decision-support environment, acknowledging insufficient evidence is preferable to producing an unsupported answer.

## Explainability Summary

ForgeMind Rail separates evidence, AI-assisted reasoning, recommendations, and human authority.

Its explainability model can be summarized as:

**Rail Evidence → Evidence Retrieval → AI-Assisted Reasoning → Supporting Evidence and Citations → Maintenance Intelligence → Human Engineering Review**

The objective is not simply to tell an engineer what the AI recommends. The objective is to make it possible to understand what evidence was used, why a concern was surfaced, what limitations apply, and where human judgment remains required.

**Models explain. Evidence supports. Backend gates. Humans authorize.**
