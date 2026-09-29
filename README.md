# StudyChat

A personal learning project for course PDF question answering with streaming answers and verified page citations.

Status: **Implemented, tested and evaluated.** Upload PDFs, select sources, ask questions, and open checked citations in the PDF viewer. Live answers use GPT-5.4 mini; fixture mode works offline.

Validation: 118 backend tests, 11 frontend unit tests, seven browser tests, and the production build pass. The latest frozen synthetic evaluation measured **19/20 passing page checks (95%) and 20/20 cited answers (100%)**. The original separate 16-question evaluation remains recorded at 13/16. These are small AI-authored page-label benchmarks, not independently measured semantic answer accuracy. See [results and limitations](docs/EVALUATION_RESULTS.md).

See [final handoff](docs/HANDOFF.md), [local setup and checks](docs/RUNBOOK.md), and [interview preparation](docs/INTERVIEW_GUIDE.md).

Repository: https://github.com/alladikarthik02/StudyChat-Course-Q-A-with-Verified-Page-Citations
The remote was empty at initial inspection. Completed task checkpoints are committed and pushed separately.

- [Technical specification](docs/TECH_SPEC.md)
- [Implementation tasks and checkpoints](docs/TASKS.md)
- [Safety requirements](docs/SAFETY.md)
- [Architecture review and challenges](docs/CHALLENGES.md)
- [project evidence](docs/PROJECT_EVIDENCE.md)
- [User research notes](docs/user_notes.md)
- [Working preferences and handoff](docs/WORKING_AGREEMENT.md)

Only project 1 is in scope. The streaming renderer package, prompt injection research project, and shared key gateway are separate projects and are not part of this build.
