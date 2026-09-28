# StudyChat

Course PDF question answering with streaming answers and verified page citations.

Status: **Implementation and synthetic evaluation complete (T0–T8), with final handoff (T9).** Upload PDFs, select sources, ask questions, and open checked citations in the PDF viewer. Live answers use GPT-5.4 mini; fixture mode works offline.

Validation: 110 backend tests, 11 frontend unit tests, seven browser tests, and production build pass. A frozen 16-question synthetic live evaluation measured **81.25% labeled-page accuracy and 100% cited-answer rate**. The 90% accuracy target remains unmet; no independent human study or 74%→90% improvement is claimed. See [results and limitations](docs/EVALUATION_RESULTS.md).

See [final handoff](docs/HANDOFF.md), [local setup and checks](docs/RUNBOOK.md), and [interview preparation](docs/INTERVIEW_GUIDE.md).

Repository identified from the resume: https://github.com/alladikarthik02/StudyChat-Course-Q-A-with-Verified-Page-Citations
The remote was empty at initial inspection. Completed task checkpoints are committed and pushed separately.

- [Technical specification](docs/TECH_SPEC.md)
- [Implementation tasks and checkpoints](docs/TASKS.md)
- [Safety requirements](docs/SAFETY.md)
- [Architecture review and challenges](docs/CHALLENGES.md)
- [Resume evidence](docs/RESUME_EVIDENCE.md)
- [User research notes](docs/user_notes.md)
- [Working preferences and handoff](docs/WORKING_AGREEMENT.md)

Only project 1 is in scope. The streaming renderer package, prompt injection research project, and shared key gateway are separate projects and are not part of this build.
