# StudyChat

Course PDF question answering with streaming answers and verified page citations.

Status: **T0–T3 complete**. Local foundation, PDF ingestion/document APIs, and internal citation verification work in offline fixture mode. Chat, live OpenAI integration, and the PDF viewer are planned for T4/T5.

Validation at T3: 81 backend tests passed against real PostgreSQL/pgvector; lint passed. T1 frontend production build and GitHub checks passed. Resume accuracy and answer-rate metrics have not yet been measured.

See [local setup and checks](docs/RUNBOOK.md).

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
