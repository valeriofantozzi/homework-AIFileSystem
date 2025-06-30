- [ ] **Phase 1 – File-system & Core Tools**

  - [ ] **Task 1 – Bootstrap `workspace_fs` package**

    - [x] 1.1 Create the package skeleton under `tools/workspace_fs` with Poetry and an initial `tests` folder.  
           _Goal: empty package imports without errors._
    - [x] 1.2 Define the public API surface (`Workspace`, `FileSystemTools`, custom exceptions) and add concise docstrings.  
           _Goal: any future module can import these names without touching internals._
    - [ ] 1.3 Configure local CI for the package (pytest + coverage, ruff, bandit).  
           _Goal: `poetry run pytest -q` and `ruff .` succeed._

  - [ ] **Task 2 – Implement the sandbox**

    - [ ] 2.1 Implement the `Workspace` class: resolve the root directory, create it if missing, and add `safe_join()` that blocks traversal and symlinks.  
           _Guarantee: all resolved paths stay inside the workspace._
    - [ ] 2.2 Create custom exceptions (`PathTraversalError`, `SymlinkError`, `SizeLimitExceeded`, `InvalidMode`).  
           _Goal: call-sites can catch fine-grained errors rather than generic `ValueError`._

  - [ ] **Task 3 – Implement file operations**

    - [ ] 3.1 Add `FileSystemTools` constructor with max-read, max-write and rate-limit parameters.  
           _Goal: centralise all runtime limits in one place._
    - [ ] 3.2 Implement `list_files()` returning filenames sorted by modification time.  
           _Scope: ignore directories and hidden files._
    - [ ] 3.3 Implement `read_file(filename)` with size check and UTF-8 fallback decoding.  
           _Guarantee: never reads more than `max_read` bytes._
    - [ ] 3.4 Implement `write_file(filename, content, mode)` with mode validation (`w` / `a`) and file-locking.  
           _Guarantee: respect `max_write` and prevent concurrent corruption._
    - [ ] 3.5 Implement `delete_file(filename)` that removes a file after symlink and scope checks.  
           _Goal: return `"deleted"` on success or raise `FileNotFoundError`._
    - [ ] 3.6 Add an internal rate-limit guard that raises `RateLimitError` when calls/second exceed the threshold.  
           _Prevents infinite tool loops._

  - [ ] **Task 4 – Test suite for `workspace_fs`**

    - [ ] 4.1 Create fixture `tmp_ws` providing a temporary workspace with low limits.  
           _Reusable by all tests in this phase._
    - [ ] 4.2 Write traversal and symlink rejection tests.  
           _Expect specific custom exceptions._
    - [ ] 4.3 Write size-limit and rate-limit enforcement tests.  
           _Ensure limits trigger reliably._
    - [ ] 4.4 Write happy-path CRUD tests, including delete flow and list refresh.  
           _Goal: validate normal operation under limits._
    - [ ] 4.5 Reach ≥ 95 % coverage for the `workspace_fs` package.  
           _Coverage gate in CI._

  - [ ] **Task 5 – Build `crud_tools` package**

    - [ ] 5.1 Generate package skeleton at `tools/crud_tools`.  
           _Independent Poetry project._
    - [ ] 5.2 Implement factory wrappers that expose `list_files`, `read_file`, `write_file`, `delete_file` as Pydantic-AI tools.  
           _Return functions already decorated for the agent._
    - [ ] 5.3 Implement `answer_question_about_files(query)` tool:  
           _Reads a capped sample of files, streams content to a lightweight LLM, returns a synthesized answer._
    - [ ] 5.4 Add unit tests using a `FakeChatModel` to validate tool wiring and multi-file summarisation logic.  
           _Goal: deterministic results without live LLM calls._

  - [ ] **Task 6 – Package documentation**

    - [ ] 6.1 Write a README for each package with usage examples and the public API.  
           _Audience: other developers who may reuse the library._
    - [ ] 6.2 Add an initial CHANGELOG (`v0.1.0 – first stable release`).  
           _Sets precedent for semantic versioning._

  - [ ] **Task 7 – Repository wiring**
    - [ ] 7.1 Declare editable path dependencies for both packages in the root `pyproject.toml` (or `requirements.txt`).  
           _Enables one-shot installation of the entire repo._
    - [ ] 7.2 Update `agent/__init__.py` to import and register the five tools for later phases.  
           _Ensures the agent sees them without extra glue code later._
    - [ ] 7.3 Create `scripts/smoke_fs.py`: writes, reads, deletes a file and prints results.  
           _Quick manual sanity check for reviewers._
